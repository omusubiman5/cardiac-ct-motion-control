import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gesture_fsm import Shape  # noqa: E402
from op_controller import OperationController  # noqa: E402
from tests.test_gesture_fsm import make_landmarks  # noqa: E402


def test_disconnected_stale_armed_state_cannot_keep_menu_armed():
    client = FakeClient()
    client.last_state['armed'] = True
    ops = OperationController(client, panel_menu=True)
    ops.panel_menu.show('edit')
    ops.menu_open = True
    client.connected = False
    assert not ops.armed
    ops.update(Shape.FIST, None)
    assert not ops.menu_open and not ops.panel_menu.opened
    assert client.sent == []


def test_menu_gesture_activity_refreshes_idle_clock_but_hold_does_not():
    clock = Clock()
    client = FakeClient()
    client.last_state['armed'] = True
    ops = OperationController(client, panel_menu=True, now=clock, gesture_hold_s=.2)
    ops.panel_menu.show('edit')
    ops.update(Shape.THUMB_DOWN, None)
    clock.t += .3
    ops.update(Shape.THUMB_DOWN, None)
    assert ops.panel_menu.index == 1
    assert ops.last_accepted_at == clock.t
    accepted = ops.last_accepted_at
    clock.t += 20
    ops.update(Shape.THUMB_DOWN, None)
    assert ops.last_accepted_at == accepted


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class FakeClient:
    """In-memory stand-in for SlicerSessionClient that emulates the
    server-side state transitions."""

    def __init__(self):
        self.connected = True
        self.session = "fake"
        self.last_state = {
            "armed": False, "mode": "view",
            "layer": "PERFORMED", "draft": False,
        }
        self.sent = []
        self.menu_index = 0

    def send(self, cmd, params=None):
        params = params or {}
        self.sent.append((cmd, params))
        st = self.last_state
        if cmd == "arm":
            st["armed"] = True
        elif cmd == "disarm":
            st["armed"] = False
        elif cmd == "select_mode":
            st["mode"] = params["mode"]
        elif cmd == "stamp":
            st["draft"] = True
        elif cmd in ("commit", "cancel"):
            st["draft"] = False
        resp = {"ok": True, "state": dict(st)}
        if cmd == "menu_open":
            resp["menu"] = {"open": True, "index": 0,
                            "items": ["mode_view", "disarm"]}
        elif cmd == "menu_next":
            self.menu_index = 1
            resp["menu"] = {"open": True, "index": 1,
                            "items": ["mode_view", "disarm"]}
        elif cmd in ("menu_close", "menu_confirm"):
            resp["menu"] = {"open": False, "index": 0,
                            "items": ["mode_view", "disarm"]}
        return resp


@pytest.fixture
def rig():
    clock = Clock()
    client = FakeClient()
    ops = OperationController(
        client, gesture_hold_s=0.2, arm_hold_s=0.5, now=clock,
    )
    return clock, client, ops


def feed(ops, clock, shape, seconds=0.0, landmarks=None):
    """Feed one frame then advance time."""
    out = ops.update(shape, landmarks)
    clock.t += seconds
    return out


def hold(ops, clock, shape, seconds, landmarks=None, step=0.05):
    """Feed frames for ``seconds`` to satisfy hold times."""
    out = []
    t = 0.0
    while t < seconds:
        out += ops.update(shape, landmarks)
        clock.t += step
        t += step
    return out


def test_iloveyou_hold_arms_once(rig):
    clock, client, ops = rig
    assert client.last_state["armed"] is False
    hold(ops, clock, Shape.ILOVEYOU, 0.6)
    assert [c for c, _ in client.sent] == ["arm"]
    assert ops.armed
    # a continued hold returns home once: the main menu opens and a
    # prolonged hold never re-arms or re-fires
    hold(ops, clock, Shape.ILOVEYOU, 1.0)
    assert client.sent == [("arm", {}), ("menu_open", {})]


def test_no_commands_while_disarmed_except_arm(rig):
    clock, client, ops = rig
    hold(ops, clock, Shape.FIST, 0.5)
    hold(ops, clock, Shape.TWO, 0.5)
    assert client.sent == []


def test_fist_stamps_in_aim_mode_at_stable_point(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    client.last_state["mode"] = "aim"
    hold(ops, clock, Shape.FIST, 0.3)
    assert [c for c, _ in client.sent] == ["stamp"]
    # holding still does not stamp twice (OP-003)
    hold(ops, clock, Shape.FIST, 0.5)
    assert [c for c, _ in client.sent] == ["stamp"]
    # release then re-hold stamps again only if server cleared draft
    client.last_state["draft"] = False
    feed(ops, clock, Shape.NONE, seconds=0.25)
    hold(ops, clock, Shape.FIST, 0.3)
    assert [c for c, _ in client.sent] == ["stamp", "stamp"]


def test_two_fingers_is_inert(rig):
    clock, client, ops = rig
    client.last_state.update(armed=True, mode="aim")
    hold(ops, clock, Shape.TWO, 0.5)
    assert client.sent == []
    client.last_state["draft"] = True
    feed(ops, clock, Shape.NONE, seconds=0.25)
    hold(ops, clock, Shape.TWO, 0.5)
    assert client.sent == []


def test_three_fingers_resets_view_or_draft_direction(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    hold(ops, clock, Shape.THREE, 0.3)
    assert client.sent == [("reset_view", {})]
    client.last_state["draft"] = True
    feed(ops, clock, Shape.NONE, seconds=0.25)
    hold(ops, clock, Shape.THREE, 0.3)
    assert client.sent[-1] == ("reset_dir", {})


def test_thumb_down_cancels_draft_and_returns_to_view(rig):
    clock, client, ops = rig
    client.last_state.update(armed=True, mode="move")
    hold(ops, clock, Shape.THUMB_DOWN, 0.3)
    assert client.sent == []
    client.last_state["draft"] = True
    feed(ops, clock, Shape.NONE, seconds=0.25)
    hold(ops, clock, Shape.THUMB_DOWN, 0.3)
    assert [c for c, _ in client.sent] == ["cancel", "select_mode"]


def test_thumb_invokes_c_branch(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    hold(ops, clock, Shape.THUMB, 0.3)
    assert client.sent == [("select_mode", {"mode": "aim"})]
    # with a live draft the C call returns to the edit context
    client.last_state["draft"] = True
    client.last_state["mode"] = "view"
    feed(ops, clock, Shape.NONE, seconds=0.25)
    hold(ops, clock, Shape.THUMB, 0.3)
    assert client.sent[-1] == ("select_mode", {"mode": "move"})


def test_iloveyou_menu_flow(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    hold(ops, clock, Shape.ILOVEYOU, 0.3)
    assert client.sent[-1][0] == "menu_open"
    assert ops.menu_open
    feed(ops, clock, Shape.NONE)
    hold(ops, clock, Shape.THUMB_DOWN, 0.3)
    assert client.sent[-1][0] == "menu_next"
    feed(ops, clock, Shape.NONE)
    hold(ops, clock, Shape.FIST, 0.3)
    assert client.sent[-1][0] == "menu_confirm"
    assert not ops.menu_open


def test_menu_open_blocks_continuous(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    hold(ops, clock, Shape.ILOVEYOU, 0.3)
    feed(ops, clock, Shape.NONE)
    # moving open palm must not emit view_rotate while menu is open
    lm = make_landmarks(index=True, middle=True, ring=True, pinky=True)
    out = feed(ops, clock, Shape.OPEN_PALM, landmarks=lm)
    out += feed(ops, clock, Shape.OPEN_PALM, landmarks=lm)
    assert all(cmd != "view_rotate" for cmd, _ in client.sent)


def test_close_without_menu_payload_allows_reopen(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    original_send = client.send

    def legacy_send(cmd, params=None):
        response = original_send(cmd, params)
        if cmd == "menu_close":
            response.pop("menu", None)
        return response

    client.send = legacy_send
    hold(ops, clock, Shape.ILOVEYOU, 0.3)
    feed(ops, clock, Shape.NONE, seconds=0.25)
    # remote menu has two items: down past the last entry closes it
    hold(ops, clock, Shape.THUMB_DOWN, 0.3)
    assert client.sent[-1][0] == "menu_next"
    feed(ops, clock, Shape.NONE, seconds=0.25)
    hold(ops, clock, Shape.THUMB_DOWN, 0.3)
    assert client.sent[-1][0] == "menu_close"
    assert not ops.menu_open
    feed(ops, clock, Shape.NONE)
    hold(ops, clock, Shape.ILOVEYOU, 0.3)
    assert client.sent[-1][0] == "menu_open"
    assert ops.menu_open


def test_closed_menu_rejection_resynchronizes_without_retry(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    ops.menu_open = True
    ops.menu_lines = ["mode_view", "disarm"]
    ops.menu_index = 0
    client.send = lambda cmd, params=None: {"ok": False, "reason": "menu is closed"}
    responses = hold(ops, clock, Shape.THUMB_DOWN, 0.3)
    assert not ops.menu_open
    assert not ops.menu_lines
    assert ops.last_command == "menu_next"
    assert not ops.last_response["ok"]


def test_rejected_close_keeps_menu_state(rig):
    _, client, ops = rig
    ops.menu_open = True
    client.send = lambda cmd, params=None: {"ok": False, "reason": "transport timeout"}
    ops._send("menu_close")
    assert ops.menu_open


def test_repeated_iloveyou_returns_home_without_closing(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    hold(ops, clock, Shape.ILOVEYOU, 0.3)
    feed(ops, clock, Shape.NONE, seconds=0.25)
    hold(ops, clock, Shape.ILOVEYOU, 0.3)
    assert ops.menu_open
    assert [cmd for cmd, _ in client.sent] == ["menu_open", "menu_open"]
    feed(ops, clock, Shape.NONE)
    hold(ops, clock, Shape.THUMB_DOWN, 0.3)
    assert ops.menu_index == 1
    feed(ops, clock, Shape.NONE)
    hold(ops, clock, Shape.FIST, 0.3)
    assert client.sent[-1][0] == "menu_confirm"


def test_open_palm_continuous_rotate(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    lm1 = make_landmarks(index=True, middle=True, ring=True,
                         pinky=True)
    lm2 = dict(lm1)
    for k in (0, 5, 9, 13, 17):
        lm2[k] = type(lm1[k])(lm1[k].x + 0.05, lm1[k].y)
    feed(ops, clock, Shape.OPEN_PALM, seconds=0.25, landmarks=lm1)  # settle
    feed(ops, clock, Shape.OPEN_PALM, landmarks=lm2)
    rotates = [p for c, p in client.sent if c == "view_rotate"]
    assert len(rotates) == 1
    assert rotates[0]["dx"] == pytest.approx(0.05 * 220.0)
    assert rotates[0]["dy"] == 0.0


def test_pinch_sends_continuous_zoom_ratio(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    lm = make_landmarks(index=True, pinch=True)
    feed(ops, clock, Shape.PINCH, seconds=0.25, landmarks=lm)
    lm2 = dict(lm)
    lm2[8] = type(lm[8])(lm[8].x, lm[8].y + 0.02)
    feed(ops, clock, Shape.PINCH, landmarks=lm2)
    zooms = [p for c, p in client.sent if c == "zoom"]
    assert len(zooms) == 1
    assert zooms[0]["ratio"] < 1.0


def test_aim_mode_sends_normalized_fingertip(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    client.last_state["mode"] = "aim"
    lm = make_landmarks(index=True)
    lm[8] = type(lm[8])(0.25, 0.40)
    feed(ops, clock, Shape.POINT, seconds=0.25, landmarks=lm)
    feed(ops, clock, Shape.POINT, landmarks=lm)
    aims = [p for c, p in client.sent if c == "aim"]
    assert aims and aims[-1] == {"nx": 0.25, "ny": 0.40}


def test_move_mode_sends_move_draft(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    client.last_state["mode"] = "move"
    client.last_state["draft"] = True
    lm = make_landmarks(index=True)
    lm[8] = type(lm[8])(0.3, 0.5)
    feed(ops, clock, Shape.POINT, seconds=0.25, landmarks=lm)
    feed(ops, clock, Shape.POINT, landmarks=lm)
    moves = [p for c, p in client.sent if c == "move_draft"]
    assert moves and moves[-1] == {"nx": 0.3, "ny": 0.5}


def test_pinch_sends_opening_delta_while_draft(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    client.last_state["mode"] = "rotate"
    client.last_state["draft"] = True
    lm = make_landmarks(index=True, pinch=True)
    feed(ops, clock, Shape.PINCH, seconds=0.25, landmarks=lm)
    lm2 = dict(lm)
    lm2[8] = type(lm[8])(lm[8].x + 0.01, lm[8].y)
    feed(ops, clock, Shape.PINCH, landmarks=lm2)
    rots = [p for c, p in client.sent if c == "rotate_opening"]
    assert rots and rots[-1]["delta_deg"] == pytest.approx(0.01 * 400.0)


def test_palm_rotates_camera_even_in_draft_edit_mode(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    client.last_state["mode"] = "rotate"
    client.last_state["draft"] = True
    lm = make_landmarks(index=True, middle=True, ring=True, pinky=True)
    feed(ops, clock, Shape.OPEN_PALM, seconds=0.25, landmarks=lm)
    lm2 = dict(lm)
    for k in (0, 5, 9, 13, 17):
        lm2[k] = type(lm[k])(lm[k].x + 0.01, lm[k].y)
    feed(ops, clock, Shape.OPEN_PALM, landmarks=lm2)
    rotates = [p for c, p in client.sent if c == "view_rotate"]
    assert rotates and rotates[-1]["dx"] == pytest.approx(0.01 * 220.0)
    assert all(cmd != "rotate_opening" for cmd, _ in client.sent)


def test_disconnect_clears_state(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    hold(ops, clock, Shape.ILOVEYOU, 0.3)
    assert ops.menu_open
    client.connected = False
    ops.update(Shape.NONE, None)
    assert not ops.menu_open
    assert ops.menu_lines == []


def test_zoom_step_converts_wheel_ticks_to_ratio(rig):
    """FR-022: discrete wheel input becomes a continuous-ratio zoom
    command on the same wire path as pinch."""
    clock, client, ops = rig
    client.last_state["armed"] = True
    ops.zoom_step(2)
    zooms = [p for c, p in client.sent if c == "zoom"]
    assert zooms and 1.0 < zooms[0]["ratio"] <= 1.0 + ops._zoom.config.max_velocity * .08
    ops.zoom_step(-3)
    assert 0.8 < client.sent[-1][1]["ratio"] < 1.0


def test_zoom_step_requires_armed(rig):
    clock, client, ops = rig
    assert ops.zoom_step(1) is None
    assert client.sent == []


@pytest.mark.parametrize('mode', ['view', 'aim', 'review'])
def test_pinch_zoom_is_common_camera_action_and_preserves_edit_mode(rig, mode):
    """Without a draft, pinch keeps zooming the camera in every mode."""
    clock, client, ops = rig
    client.last_state.update(armed=True, mode=mode, draft=False)
    lm = make_landmarks(index=True)
    for i in range(12):
        moved = dict(lm)
        moved[8] = type(lm[8])(lm[8].x, lm[8].y-i*.01)
        feed(ops, clock, Shape.PINCH, seconds=0.05, landmarks=moved)
    zooms = [params for cmd, params in client.sent if cmd == 'zoom']
    assert zooms and all(params['ratio'] > 1 for params in zooms)
    assert all(cmd == 'zoom' for cmd, _ in client.sent)
    assert client.last_state['mode'] == mode


@pytest.mark.parametrize('mode', ['move', 'rotate', 'tilt'])
def test_pinch_adjusts_opening_while_draft(rig, mode):
    """While a provisional C exists pinch turns the opening direction
    instead of zooming; the draft itself is preserved."""
    clock, client, ops = rig
    client.last_state.update(armed=True, mode=mode, draft=True)
    lm = make_landmarks(index=True)
    for i in range(12):
        moved = dict(lm)
        moved[8] = type(lm[8])(lm[8].x+i*.01, lm[8].y)
        feed(ops, clock, Shape.PINCH, seconds=0.05, landmarks=moved)
    rots = [params for cmd, params in client.sent if cmd == 'rotate_opening']
    assert rots and all(params['delta_deg'] > 0 for params in rots)
    assert all(cmd in {'select_mode', 'rotate_opening'} for cmd, _ in client.sent)
    assert client.last_state['mode'] == 'rotate'
    assert client.last_state['draft'] is True


def test_zoom_step_clamped(rig):
    clock, client, ops = rig
    client.last_state["armed"] = True
    ops.zoom_step(100)
    assert 1.0 < client.sent[-1][1]["ratio"] <= 1.0 + ops._zoom.config.max_velocity * .08


def test_commit_binds_last_seen_revision(rig):
    """ONI-001: the commit carries the displayed binding the operator
    last saw (draft_id/rev/hash); the server rejects a stale snapshot."""
    clock, client, _ = rig
    ops = OperationController(client, gesture_hold_s=0.2, arm_hold_s=0.5,
                              now=clock, panel_menu=True)
    client.last_state["armed"] = True
    client.last_state["draft"] = True
    binding = {"draft_id": "d1", "rev": 3, "hash": "h1"}

    def with_result(cmd, params=None):
        resp = FakeClient.send(client, cmd, params)
        if cmd == "status":
            resp["result"] = {"rev": 3, "displayed": dict(binding)}
        else:
            resp.setdefault("result", {})["rev"] = 3
        return resp
    client.send = with_result

    # drive an edit response through _send so _last_draft_rev picks up 3
    ops._send("rotate_opening", {"delta_deg": 5})
    feed(ops, clock, Shape.NONE)
    hold(ops, clock, Shape.FIST, 0.3)   # fist opens the confirm page
    assert ops.panel_menu.opened and ops.panel_menu.page == "confirm"
    # release the fist, then fist again to execute the displayed entry
    hold(ops, clock, Shape.NONE, 0.3)
    hold(ops, clock, Shape.FIST, 0.3)
    commits = [p for c, p in client.sent if c == "commit"]
    assert commits and commits[0] == binding
