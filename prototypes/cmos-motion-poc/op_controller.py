"""Gesture -> typed command mapping for the non-contact path.

One OperationController instance turns per-frame shape+landmarks into
commands for the Slicer command protocol. The server owns the state;
this controller only reflects the last response (armed/mode/layer/
draft/menu) and never bypasses the armed/mode/draft gates.

Discrete bindings (single-meaning gesture assignment, docs/57):

    ILOVEYOU    -> home: arm (stopped) / show main menu (armed, from anywhere)
                   | frozen draft: resume editing (draft is never discarded)
    THUMB       -> up: menu previous | closed menu: invoke C (aim/move mode)
    THUMB_DOWN  -> down: menu next (last item = back/close) | draft: cancel
    FIST        -> decide: menu select | aim: stamp | draft: open commit confirm
    THREE       -> reset: draft direction | view (no draft)
    TWO         -> inert (no meaning)

Continuous bindings while armed and the menu is closed:

    OPEN_PALM -> view_rotate (always camera only, every mode)
    POINT     -> view_pan (view) | aim (aim) | move_draft (draft, move)
                 | review marker (review)
    PINCH     -> zoom dy (no draft) | draft: rotate_opening dx

While armed the controller keeps the last stable aim point: the stamp
fires at the point that was still, so switching from POINT to FIST can
never shift the placement. Disarming happens through the menu or the
input timeout; an open palm held still can never disarm by accident.
"""

from __future__ import annotations

import time
from typing import Callable, Mapping

from gesture_fsm import GestureLatch, HoldDetector, Shape
from motion_engine import Point, palm_center
from session_client import SlicerSessionClient
from hand_menu import HandMenu
from zoom_engine import SmoothZoom

# aim positions within this normalized radius count as "still" — the
# point the operator actually decided on, immune to shape-change wobble
AIM_EPS = 0.01


class OperationController:
    def __init__(
        self,
        client: SlicerSessionClient,
        gesture_hold_s: float = 0.35,
        arm_hold_s: float = 1.5,
        rotate_deg_per_norm: float = 220.0,
        rotate_deadzone: float = 0.002,
        pan_px_per_norm: float = 900.0,
        zoom_ratio_per_norm: float = 1.6,
        wheel_zoom_ratio: float = 1.15,
        aim_rate_hz: float = 25.0,
        opening_deg_per_norm: float = 400.0,
        tilt_deg_per_norm: float = 400.0,
        zoom_config=None,
        now: Callable[[], float] = time.monotonic,
        panel_menu: bool = False,
        loss_grace_s: float = 1.5,
    ) -> None:
        self.client = client
        self._now = now
        self.rotate_deg_per_norm = rotate_deg_per_norm
        self.rotate_deadzone = rotate_deadzone
        self.pan_px_per_norm = pan_px_per_norm
        self.zoom_ratio_per_norm = zoom_ratio_per_norm
        self.wheel_zoom_ratio = wheel_zoom_ratio
        # revision of the draft the operator last saw (server reports
        # it in each edit response); sent back on commit so a stale
        # snapshot can never be committed (ONI-001)
        self._last_draft_rev: int | None = None
        self.aim_period = 1.0 / max(1.0, aim_rate_hz)
        self.opening_deg_per_norm = opening_deg_per_norm
        self.tilt_deg_per_norm = tilt_deg_per_norm
        self._latch = GestureLatch(hold_s=gesture_hold_s, now=now)
        self._arm_hold = HoldDetector(Shape.ILOVEYOU, arm_hold_s, now=now)
        self._last_palm: Point | None = None
        self._last_finger: Point | None = None
        self._last_pinch_y: float | None = None
        self._shape_since = 0.0
        self._last_aim_sent = 0.0
        self._shape = Shape.NONE
        self.last_response: dict = {}
        self.last_command = ""
        self.last_accepted_at = None
        self.status_details = {}
        self.last_commit_request = None
        self._zoom = SmoothZoom(zoom_config)
        self._zoom_at = None
        self._loss_notified = False
        self._loss_since: float | None = None
        self.loss_grace_s = loss_grace_s
        self.menu_open = False
        self.menu_lines: list[str] = []
        self.menu_index = 0
        self.aim_valid: bool | None = None
        self.panel_menu = HandMenu() if panel_menu else None
        self.notice = ""
        self.draft_frozen = False
        # The last aim position that stayed within a small radius for the
        # gesture hold time. Discrete placement acts on this point so the
        # wobble of a shape change can never move the target.
        self._stable_aim = None
        self._aim_candidate = None
        self._aim_since = None
        self._last_aim_cmd = None
        self._last_pinch_x = None

    # --- state helpers -------------------------------------------------

    @property
    def _state(self) -> dict:
        return self.client.last_state

    @property
    def armed(self) -> bool:
        return self.client.connected and bool(self._state.get("armed")) and self._state.get("input_owner","hand") == "hand"

    @property
    def mode(self) -> str:
        return str(self._state.get("mode", "view"))

    @property
    def draft(self) -> bool:
        return bool(self._state.get("draft"))

    def _send(self, cmd: str, params: dict | None = None) -> dict:
        response = self.client.send(cmd, params)
        self.last_response = response
        self.last_command = cmd
        if not self.client.connected:
            self.on_transport_lost()
        result = response.get("result")
        if response.get('ok') and cmd not in {'status', 'query_result'}:
            self.last_accepted_at = self._now()
        if cmd == 'commit':
            self.last_commit_request = getattr(self.client, 'last_request', None)
        if cmd == 'status' and response.get('ok') and isinstance(result, dict):
            self.status_details = result
            if self.panel_menu:
                self.panel_menu.choices = result.get('choices', {})
        if cmd == 'resume_draft' and response.get('ok'):
            self._loss_notified = False
        if cmd == "arm" and response.get("ok"):
            self._latch.reset()
            self._reset_continuous()
            self._stable_aim = None
            self._aim_candidate = None
            self._last_aim_cmd = None
        if cmd in {"disarm", "select_mode", "resume_draft"} and response.get("ok"):
            self._reset_continuous()
            self.notice = ""
        if cmd == "resume_draft" and response.get("ok"):
            self.draft_frozen = False
        if cmd == "status" and response.get("ok") and isinstance(result, dict):
            self.draft_frozen = bool(result.get("frozen"))
        if cmd == "aim":
            self.aim_valid = result.get("valid") if response.get("ok") and isinstance(result, dict) else None
        if isinstance(result, dict) and "rev" in result:
            self._last_draft_rev = result["rev"]
        if cmd == "stamp" and response.get("ok") and response.get("draft_id"):
            # A new draft starts at revision 0 (state_machine.Draft).
            self._last_draft_rev = 0
        menu = response.get("menu")
        if menu is not None:
            self.menu_open = bool(menu.get("open"))
            self.menu_lines = list(menu.get("items", []))
            self.menu_index = int(menu.get("index", 0))
        elif (cmd == "menu_close" and response.get("ok")) or response.get("reason") == "menu is closed":
            # Older running servers acknowledge close without a menu payload.
            # A closed-menu rejection is also authoritative, never a new action.
            self.menu_open = False
            self.menu_lines = []
            self.menu_index = 0
        if cmd not in {"view_rotate", "view_pan", "zoom", "aim", "move_draft", "rotate_opening", "tilt"}:
            print(f"slicer_command cmd={cmd} ok={response.get('ok')} "
                  f"menu={self.menu_open} index={self.menu_index} "
                  f"mode={self._state.get('mode')} reason={response.get('reason', '')!r}", flush=True)
        if not self.draft:
            self._last_draft_rev = None
        return response

    def zoom_step(self, ticks: float) -> dict | None:
        """Discrete input (e.g. a mouse wheel tick) converted into the
        same continuous-ratio ``zoom`` command a pinch produces
        (FR-022): one smooth ratio step per tick, clamped."""
        if ticks == 0 or not self.armed:
            return None
        before = self._zoom.ratio
        # A wheel step uses the same acceleration, velocity and total-ratio caps.
        state = self._zoom.update(max(-1.,min(1.,ticks)), .08)
        ratio = state.ratio/before
        self._zoom.velocity = 0.0
        return self._send("zoom", {"ratio": ratio})

    def _reset_continuous(self) -> None:
        self._last_palm = None
        self._last_finger = None
        self._last_pinch_x = None
        self._last_pinch_y = None
        self._zoom.velocity = 0.0
        self._zoom_at = None

    def recognition_lost(self, reason):
        if not (self.draft and self.mode in {"move", "rotate", "tilt"}
                and not self.menu_open and not self._loss_notified):
            return None
        # Freeze only on a SUSTAINED loss: gesture transitions and brief
        # tracking dropouts must not freeze the draft — nothing moves
        # while the hand is unseen anyway, so grace costs no safety.
        now = self._now()
        if self._loss_since is None:
            self._loss_since = now
            return None
        if now - self._loss_since < self.loss_grace_s:
            return None
        self._loss_notified = True
        self._loss_since = None
        self._reset_continuous()
        return self._send("recognition_lost", {"reason": reason})

    # --- per-frame update -------------------------------------------------

    def update(
        self, shape: Shape, landmarks: Mapping[int, Point] | None
    ) -> list[dict]:
        """Process one frame; returns the list of command responses."""
        responses: list[dict] = []
        if landmarks is not None:
            # A valid observation clears any pending loss grace window.
            self._loss_since = None
        if shape != self._shape:
            # The shape transition wobbles the hand. Re-anchor the target
            # on the last stable point before the new shape takes over.
            if (
                self._shape is Shape.POINT and self._stable_aim is not None
                and self._last_aim_cmd is not None
                and self.client.connected and self.armed
                and not (self.panel_menu and self.panel_menu.opened)
                and (abs(self._last_aim_cmd[0] - self._stable_aim[0]) > AIM_EPS
                     or abs(self._last_aim_cmd[1] - self._stable_aim[1]) > AIM_EPS)
            ):
                sx, sy = self._stable_aim
                if self.draft and self.mode == "move":
                    responses.append(self._send("move_draft", {"nx": sx, "ny": sy}))
                elif not self.draft and self.mode == "aim":
                    responses.append(self._send("aim", {"nx": sx, "ny": sy}))
            self._reset_continuous()
            self._shape = shape
            self._shape_since = self._now()
            self.notice = ""

        if not self.client.connected:
            self.on_transport_lost()
            return responses

        # dedicated arm path: works while disarmed, fires once
        if not self.armed:
            if self.panel_menu:
                self.panel_menu.close()
                self.menu_open = False
            if self._arm_hold.update(shape, armed=False):
                responses.append(self._send("arm"))
            return responses
        self._arm_hold.reset()

        edge = self._latch.update(shape)

        # ILOVEYOU = return to the start: disarmed it arms, armed it always
        # shows the main menu. A live draft is never discarded by this.
        # A frozen draft (recognition loss) is resumed by the same gesture
        # — the operator never leaves the sterile field for a mouse click.
        if edge is Shape.ILOVEYOU:
            if self.draft_frozen:
                # Resume the frozen draft straight back into editing — no
                # menu detour (an open menu would eat the next FIST as a
                # menu selection instead of opening commit confirmation).
                responses.append(self._send("resume_draft"))
                if self.panel_menu and self.panel_menu.opened:
                    self.panel_menu.close()
                    self.menu_open = False
                self.last_accepted_at = self._now()
                self._reset_continuous()
                return responses
            if self.panel_menu:
                self.panel_menu.show("main")
                self.menu_open = True
            else:
                responses.append(self._send("menu_open"))
            self.last_accepted_at = self._now()
            self._reset_continuous()
            return responses
        if shape is Shape.ILOVEYOU:
            return responses

        if self.panel_menu and self.panel_menu.opened:
            if edge is Shape.THUMB:
                self.panel_menu.previous()
                self.last_accepted_at = self._now()
            elif edge is Shape.THUMB_DOWN:
                # next item; past the last entry backs out one level
                if self.panel_menu.index >= len(self.panel_menu.entries) - 1:
                    self.panel_menu.back()
                else:
                    self.panel_menu.next()
                self.last_accepted_at = self._now()
            elif edge is Shape.FIST:
                responses.extend(self._panel_select())
            elif edge is Shape.THREE:
                responses.append(self._send("reset_dir" if self.draft else "reset_view"))
            # navigation edges keep their menu meaning; every other shape
            # keeps its single meaning (view work, draft edit) even while
            # the menu is open — the tree has no mode-lockout
            self.menu_open = self.panel_menu.opened
            responses.extend(self._continuous(shape, landmarks))
            return responses
        if self.menu_open:
            if edge is Shape.THUMB:
                responses.append(self._send("menu_prev"))
            elif edge is Shape.THUMB_DOWN:
                if self.menu_index >= len(self.menu_lines) - 1:
                    responses.append(self._send("menu_close"))
                else:
                    responses.append(self._send("menu_next"))
            elif edge is Shape.FIST:
                responses.append(self._send("menu_confirm"))
            elif edge is Shape.THREE:
                responses.append(self._send("reset_dir" if self.draft else "reset_view"))
            responses.extend(self._continuous(shape, landmarks))
            return responses

        # THUMB = invoke the C branch: aim mode to place, move mode to
        # edit a live draft.
        if edge is Shape.THUMB:
            responses.append(self._send("select_mode",
                                      {"mode": "move" if self.draft else "aim"}))
            return responses
        if edge is Shape.THUMB_DOWN:
            # down/back: cancel the provisional C and return to view work
            if self.draft:
                response = self._send("cancel")
                responses.append(response)
                if response.get("ok"):
                    responses.append(self._send("select_mode", {"mode": "view"}))
        elif edge is Shape.FIST:
            if self.draft:
                # decide: proceed to the independent confirmation page.
                # A commit without the displayed-binding confirmation is
                # always rejected server-side, so there is no fallback.
                if self.panel_menu:
                    self._open_confirmation()
                return responses
            elif self.mode == "aim":
                # decide: place the provisional C at the stable point
                if self._stable_aim is not None:
                    responses.append(self._send(
                        "aim", {"nx": self._stable_aim[0], "ny": self._stable_aim[1]}))
                responses.append(self._send("stamp"))
        elif edge is Shape.THREE:
            # reset to the initial value: draft direction or the view
            responses.append(self._send("reset_dir" if self.draft else "reset_view"))
        responses.extend(self._continuous(shape, landmarks))
        return responses

    def _open_confirmation(self):
        menu = self.panel_menu
        # Mouse size edits also increment the draft revision. Query the same
        # guarded connection before binding the confirmation snapshot.
        response = self._send("status")
        menu.show("confirm")
        menu.confirm_revision = self._last_draft_rev if response.get("ok") else None
        menu.confirm_snapshot = self.status_details.get("displayed") if response.get("ok") else None
        self.menu_open = True
        self._reset_continuous()

    def _panel_select(self):
        menu = self.panel_menu
        key = menu.entries[menu.index].key
        if self.draft and key == "review":
            menu.notice = "仮Cの編集を完了してから既存Cを選択してください"
            return []
        if key in {'plans', 'plan_versions', 'creators', 'storages', 'plan_items'}:
            self._send('status')
            menu.choice_revision = self.status_details.get('plan_revision')
            menu.show(key)
            return []
        if key in {"main", "edit", "records", "reasons"}:
            if key == "records" and self.draft:
                menu.notice = "仮Cの編集を完了してから計画・記録を開いてください"
            else:
                menu.show(key)
            return []
        if key == "c" and self.draft:
            menu.show("edit")
            return []
        if key == "confirm":
            self._open_confirmation()
            return []
        bound = key in {'begin_plan_revision','save_plan_revision','cancel_plan_revision','edit_plan_item','delete_plan_item','add_plan_item','move_plan_item','reorder_plan','skip_plan','confirm_audit'}
        if bound:
            self._send('status')
        params = {'plan_revision':self.status_details.get('plan_revision')} if bound else {}
        if key.startswith('choose:'):
            _, category, index = key.split(':')
            choices = menu.choice_snapshot.get(category, [])
            if int(index) >= len(choices):
                menu.notice = '選択対象が変わりました。選び直してください'
                return []
            value = choices[int(index)]
            cmd, field = {'plans':('select_plan','plan_id'), 'creators':('select_creator','creator'),
                          'storages':('select_storage','storage'), 'plan_items':('select_plan_item','item_id'),
                          'plan_versions':('select_plan_version','version')}[category]
            params[field] = value
            if category in {'plan_items','plan_versions'}:
                params['plan_revision'] = menu.choice_revision
        elif key in {"view", "c", "review", "move", "rotate", "tilt"}:
            cmd, params = "select_mode", {"mode": "aim" if key == "c" else key}
        elif key == "stop":
            cmd = "disarm"
        elif key == "layer":
            cmd, params = "select_layer", {"layer": "PLANNED" if self._state.get("layer") == "PERFORMED" else "PERFORMED"}
        elif key == "out_of_plan":
            cmd = "set_out_of_plan"
        elif key == "skip_plan":
            cmd = key
        elif key.startswith("reason:"):
            cmd, params = "select_reason", {"reason": key[7:]}
        elif key == "commit":
            if not self.draft or menu.confirm_revision is None:
                menu.notice = "仮Cの版を確認できません。編集に戻って調整してください"
                return []
            if menu.confirm_revision != self._last_draft_rev:
                menu.notice = "仮Cが変わりました。編集に戻って確認し直してください"
                return []
            if not menu.confirm_snapshot:
                menu.notice = '描画完了を確認できません。編集に戻ってください'
                return []
            cmd, params = key, {k:menu.confirm_snapshot[k] for k in ('draft_id','rev','hash')}
        elif key == 'query_result':
            if not self.last_commit_request:
                menu.notice = '照会する確定要求がありません'
                return []
            cmd, params = key, {'req':self.last_commit_request}
        elif key == 'confirm_audit':
            cmd, params = key, {'audit':self.status_details.get('pending_audit')}
        elif key in {'edit_plan_item','delete_plan_item'}:
            current = self.status_details.get('selected_plan_item')
            if not current:
                menu.notice = '先に予定項目を選んでください'
                return []
            cmd = key
            params['item_id'] = current
        elif key in {'move_plan_item','reorder_plan'}:
            cmd = key
            params.update(self.status_details.get('reorder_selection') or {})
        else:
            cmd = key
        response = self._send(cmd, params)
        if response.get("ok"):
            if cmd == 'select_plan_version':
                self._send('status')
            if cmd in {'commit', 'cancel'}:
                self._send("select_mode", {"mode": "view"})
            menu.close()
            self._reset_continuous()
        else:
            menu.notice = "拒否：" + str(response.get("reason", "不明"))
        return [response]

    # --- continuous control ------------------------------------------------

    def _finger_nx(self, landmarks) -> float:
        return float(landmarks[8].x) if landmarks and 8 in landmarks else 0.5

    def _finger_ny(self, landmarks) -> float:
        return float(landmarks[8].y) if landmarks and 8 in landmarks else 0.5

    def _continuous(
        self, shape: Shape, landmarks: Mapping[int, Point] | None
    ) -> list[dict]:
        if landmarks is None:
            return []
        if shape in {Shape.NONE, Shape.UNKNOWN}:
            self._reset_continuous()
            return []
        mode = self.mode
        out: list[dict] = []

        # settle window: right after a shape change the hand is still
        # moving; seed every baseline so the transition wobble can never
        # become a camera jump or a draft move
        if self._now() - self._shape_since < self._latch.hold_s:
            self._last_palm = palm_center(landmarks)
            self._last_pinch_x = landmarks[8].x
            self._last_pinch_y = landmarks[8].y
            self._last_aim_sent = self._now()
            return out

        # PINCH: zoom while no provisional C exists; while a draft is
        # open it adjusts the opening direction (hand zoom pauses, the
        # mouse wheel keeps working).
        if shape is Shape.PINCH:
            if self.draft:
                if mode != "rotate":
                    out.append(self._send("select_mode", {"mode": "rotate"}))
                x = landmarks[8].x
                if self._last_pinch_x is None:
                    self._last_pinch_x = x
                    return out
                dx = x - self._last_pinch_x
                # Sub-deadzone motion must accumulate: advancing the
                # reference on every frame silently swallows slow drags.
                if abs(dx) <= self.rotate_deadzone:
                    return out
                self._last_pinch_x = x
                out.append(self._send("rotate_opening", {
                    "delta_deg": dx * self.opening_deg_per_norm,
                }))
                return out
            y = landmarks[8].y
            if self._last_pinch_y is None:
                self._last_pinch_y = y
                return out
            dy = y - self._last_pinch_y
            if abs(dy) > 1e-4:
                now = self._now()
                dt = min(0.1, max(0.001, now-(self._zoom_at or now-0.04)))
                self._zoom_at = now
                before = self._zoom.ratio
                zoom = self._zoom.update(-dy*self.zoom_ratio_per_norm/dt, dt)
                ratio = zoom.ratio/before
                if ratio != 1.0:
                    out.append(self._send('zoom', {'ratio': ratio}))
            self._last_pinch_y = y
            return out

        if shape is Shape.POINT:
            nx = self._finger_nx(landmarks)
            ny = self._finger_ny(landmarks)
            now = self._now()
            # track the point that stays still: it becomes the decided
            # point that shape changes cannot wobble away from
            if (self._aim_candidate is None
                    or abs(nx - self._aim_candidate[0]) > AIM_EPS
                    or abs(ny - self._aim_candidate[1]) > AIM_EPS):
                self._aim_candidate = (nx, ny)
                self._aim_since = now
            elif self._aim_since is not None \
                    and now - self._aim_since >= self._latch.hold_s:
                self._stable_aim = self._aim_candidate
            if self.draft:
                if mode != "move":
                    out.append(self._send("select_mode", {"mode": "move"}))
                    return out
                if now - self._last_aim_sent < self.aim_period:
                    return out
                self._last_aim_sent = now
                self._last_aim_cmd = (nx, ny)
                out.append(self._send("move_draft", {"nx": nx, "ny": ny}))
                return out
            if mode in ("aim", "review"):
                # fingertip drives the surface aim / review marker
                if now - self._last_aim_sent < self.aim_period:
                    return out
                self._last_aim_sent = now
                self._last_aim_cmd = (nx, ny)
                out.append(self._send("aim", {"nx": nx, "ny": ny}))
                return out

        center = palm_center(landmarks)
        if center is None:
            return out
        if self._last_palm is None:
            self._last_palm = center
            return out

        if shape is Shape.OPEN_PALM:
            # open palm always rotates the camera — even while a draft
            # is open the C itself is never moved by it
            dx = center.x - self._last_palm.x
            dy = center.y - self._last_palm.y
            # Sub-deadzone motion must accumulate: advancing the
            # reference on every frame silently swallows slow drags.
            if abs(dx) < self.rotate_deadzone and abs(dy) < self.rotate_deadzone:
                return out
            out.append(self._send("view_rotate", {
                "dx": dx * self.rotate_deg_per_norm,
                "dy": dy * self.rotate_deg_per_norm,
            }))
            self._last_palm = center
            return out
        elif shape is Shape.POINT and mode == "view" and not self.draft:
            dx = center.x - self._last_palm.x
            dy = center.y - self._last_palm.y
            if dx or dy:
                out.append(self._send("view_pan", {
                    "dx": dx * self.pan_px_per_norm,
                    "dy": dy * self.pan_px_per_norm,
                }))
                self._last_palm = center
                return out

        self._last_palm = center
        return out

    def on_transport_lost(self) -> None:
        """The client dropped: clear local mirrors so nothing acts on
        stale state."""
        self._loss_since = None
        self.menu_open = False
        self.menu_lines = []
        self.menu_index = 0
        self.aim_valid = None
        if self.panel_menu:
            self.panel_menu.close()
        self._stable_aim = None
        self._aim_candidate = None
        self._last_aim_cmd = None
        self._reset_continuous()
        self._latch.reset()
        self._arm_hold.reset()
