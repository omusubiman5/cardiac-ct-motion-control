"""Typed command protocol between the motion PoC and the C-stamp module.

Envelope (one JSON object per line over loopback TCP)::

    {"v": 1, "session": "<id>", "seq": 3, "req": "<request id>",
     "cmd": "stamp", "ts": 1760000000.0, "params": {...}}

Handshake: the client first sends ``{"cmd": "hello", "v": 1}`` and the
server replies with a freshly allocated ``session`` id. Every following
line must carry that session, a strictly increasing ``seq``, a unique
``req`` id, and a timestamp within ``session_ttl_ms`` of server time.

Rejected input is inert: wrong version/session, non-increasing seq,
reused req (replays return the stored response instead of executing
again), stale timestamps, unknown commands, and commands not allowed in
the current state all produce ``{"ok": false, ...}`` and change nothing.
No keyboard input, shell, arbitrary Python, or arbitrary node edits are
reachable through this protocol.
"""

from __future__ import annotations

import json
import math
import time
import uuid
from typing import Callable, Mapping


PROTOCOL_VERSION = 1
DEFAULT_TTL_MS = 2000.0
MAX_LINE_BYTES = 4096

MODES = {"view", "aim", "move", "rotate", "tilt", "review"}
LAYERS = {"PLANNED", "PERFORMED"}

# commands that never require the armed state
PRE_ARM_COMMANDS = {"hello", "status", "arm", "size_settings", "disarm", "query_result", "recognition_lost", "claim_input", "diagnose"}

# command -> required operation mode (None = any mode)
# view_rotate / view_pan / zoom change only the camera, so they stay
# available in every mode — including while a draft is open (FR-021).
MODE_REQUIRED = {
    "aim": {"aim", "move"},
    "stamp": "aim",
    "move_draft": "move",
    "rotate_opening": "rotate",
    "tilt": "tilt",
    "select_event": "review",
    "show_c": "review",
    "begin_correction": "review",
}

DRAFT_REQUIRED = {
    "move_draft", "rotate_opening", "tilt", "reverse", "reset_dir",
    "commit", "cancel",
}

NO_DRAFT_REQUIRED = {"stamp", "begin_correction", "load_session", "create_plan", "load_plan", "select_plan",
                     "begin_plan_revision", "edit_plan_item", "add_plan_item", "delete_plan_item",
                     "move_plan_item", "save_plan_revision", "cancel_plan_revision", "skip_plan", "reorder_plan"}

KNOWN_COMMANDS = PRE_ARM_COMMANDS | set(MODE_REQUIRED) | {
    "view_rotate", "view_pan", "zoom", "reset_view",
    "disarm", "resume_draft", "select_mode", "select_layer",
    "reverse", "reset_dir", "commit", "cancel",
    "load_plan", "select_plan_item", "skip_plan", "reorder_plan",
    "create_plan", "begin_plan_revision", "edit_plan_item",
    "delete_plan_item", "add_plan_item", "move_plan_item",
    "save_plan_revision", "cancel_plan_revision",
    "select_reason", "set_out_of_plan", "revoke_event",
    "confirm_audit",
    "menu_open", "menu_next", "menu_prev", "menu_confirm", "menu_close",
    "save_session", "load_session", "query_result",
    "select_plan", "select_plan_version", "select_creator", "select_storage",
}

# commands that only read state or move the menu cursor — they must
# stay reachable even when the target window lost the foreground so an
# operator can always query or shut down. Everything else (view
# changes, draft edits, plan edits, commits) is blocked while the
# target window is not foreground (docs/23 unit 2/3, SR-006).
FOREGROUND_EXEMPT = PRE_ARM_COMMANDS | {
    "status", "query_result", "disarm",
    "menu_open", "menu_next", "menu_prev", "menu_close", "menu_confirm",
    "select_mode", "select_layer", "select_reason",
}


def _reject(reason: str, state: Mapping | None = None) -> dict:
    return {"ok": False, "reason": reason, "state": dict(state or {})}


class CommandDispatcher:
    """Validates envelopes and dispatches to the operations object.

    ``ops`` must implement methods named after commands (``arm``,
    ``stamp`` ...). Each method receives the params dict and returns a
    dict merged into the response. The dispatcher owns session state,
    mode, armed flag and dedup — ops only performs the action.
    """

    def __init__(
        self,
        ops,
        ttl_ms: float = DEFAULT_TTL_MS,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.ops = ops
        self.ttl_ms = ttl_ms
        self._now = now
        self.session: str | None = None
        self._last_seq = 0
        self._seen: dict[str, dict] = {}
        self.armed = False
        self.mode = "view"
        self.layer = "PERFORMED"
        self.input_owner = 'hand'
        self._local_input = None
        self.runtime_hash = None

    # --- transport ---------------------------------------------------

    def handle_line(self, raw: bytes | str) -> dict:
        received = time.perf_counter_ns()
        response = self._handle_line(raw)
        response['server_timing'] = {'received_ns':received, 'response_ready_ns':time.perf_counter_ns(),
                                     'clock':'server-perf-counter'}
        contract = getattr(self.ops, 'display_contract', None)
        response['server_timing']['render_ack_ns'] = getattr(contract, 'acknowledged_ns', None)
        response['server_timing']['last_save'] = getattr(self.ops, '_last_save_timing', None)
        response['server_timing']['last_render'] = getattr(self.ops, '_last_render_timing', None)
        context = getattr(self.ops, '_request_context', {})
        same_request = context.get('req') is not None and context.get('req') == response.get('req')
        response['server_timing']['envelope_validated_ns'] = context.get('envelope_validated_ns') if same_request else None
        response['server_timing']['accepted_ns'] = context.get('accepted_ns') if same_request and response.get('ok') is True else None
        return response

    def _handle_line(self, raw: bytes | str) -> dict:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if len(raw) > MAX_LINE_BYTES:
                return _reject("line too long")
            data = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _reject("not json")
        if not isinstance(data, dict):
            return _reject("not an object")

        if data.get("cmd") == "hello":
            if data.get('v') != PROTOCOL_VERSION:
                return _reject('protocol version mismatch',self._state())
            verifier = getattr(self.ops, 'verify_runtime_hello', None)
            if verifier:
                try:
                    self.runtime_hash = verifier(data.get('runtime_manifest'))
                except (ValueError, OSError) as error:
                    self.on_disconnect()
                    self.session = None
                    self.runtime_hash = None
                    return _reject(str(error), self._state())
            response = self._hello()
            response['runtime_hash'] = self.runtime_hash
            return response

        cmd = data.get("cmd")
        if not isinstance(cmd, str) or cmd not in KNOWN_COMMANDS:
            return _reject("unknown command", self._state())

        response = self._check_envelope(data)
        if response is not None:
            return response

        finder = getattr(self.ops,'query_persisted_result',None)
        if cmd == 'commit' and finder:
            try:
                saved = finder(data['req'])
            except (ValueError, OSError) as error:
                # Invalid/unreadable history is a refusal, never a silent Qt callback failure.
                return {**_reject(f'保存履歴を検証できません: {error}', self._state()), 'req': data['req']}
            if saved:
                if saved.get('binding') != (data.get('params') or {}):
                    return _reject('saved request binding mismatch',self._state())
                return {**saved, 'state':self._state(), 'deduplicated':True}
        self._seen[data["req"]] = None  # placeholder until executed
        self.ops._request_context = {'req': data['req'], 'cmd': cmd,
                                     'input_method': 'hand', 'session': self.session,
                                     'params':data.get('params') or {},
                                     'runtime_hash':self.runtime_hash, 'trace':data.get('trace'),
                                     'envelope_validated_ns':time.perf_counter_ns(), 'accepted_ns':None}
        result = self._execute(cmd, data.get("params") or {})
        response = {
            "ok": result.get("ok", True),
            "req": data["req"],
            "state": self._state(),
        }
        if "reason" in result:
            response["reason"] = result["reason"]
        for key in ("result", "draft_id", "event_id", "menu"):
            if key in result:
                response[key] = result[key]
        self._seen[data["req"]] = response
        return response

    def _hello(self) -> dict:
        if self.input_owner == 'hand':
            self.ops.on_disconnect()
        self.session = uuid.uuid4().hex
        self._last_seq = 0
        self._seen.clear()
        # reconnect never inherits armed state or a live draft's control
        if self.input_owner == 'hand':
            self.armed = False
            self.ops.on_session_reset()
        return {
            "ok": True,
            "session": self.session,
            "state": self._state(),
        }

    def _check_envelope(self, data: Mapping) -> dict | None:
        trace = data.get('trace')
        if trace is not None and (not isinstance(trace, dict) or set(trace)-{'frame_id','acquired_ns','recognized_ns','gate_ns'}
                                  or any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in trace.values())):
            return _reject('invalid metadata trace', self._state())
        verifier = getattr(self.ops, 'verify_runtime_request', None)
        if verifier and data.get('cmd') not in {'status', 'disarm', 'query_result', 'recognition_lost', 'diagnose'}:
            try:
                verifier(data.get('runtime_hash'), self.runtime_hash)
            except (ValueError, OSError) as error:
                self.on_disconnect()
                self.session = None
                self.runtime_hash = None
                return _reject(str(error), self._state())
        if data.get("v") != PROTOCOL_VERSION:
            return _reject("protocol version mismatch", self._state())
        if self.session is None:
            return _reject("no session; send hello first")
        if data.get("session") != self.session:
            return _reject("wrong session", self._state())
        seq = data.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq <= self._last_seq:
            return _reject("seq must increase", self._state())
        req = data.get("req")
        if not isinstance(req, str) or not req:
            return _reject("missing request id", self._state())
        if req in self._seen:
            cached = dict(self._seen[req] or _reject("in flight"))
            cached["deduplicated"] = True
            return cached
        ts = data.get("ts")
        if not isinstance(ts, (int, float)) or isinstance(ts, bool) \
                or not math.isfinite(ts):
            return _reject("missing timestamp", self._state())
        if abs(self._now() - ts) * 1000.0 > self.ttl_ms:
            return _reject("stale command", self._state())
        self._last_seq = seq
        return None

    def _execute(self, cmd: str, params: dict) -> dict:
        if not isinstance(params, dict):
            return _reject("params must be an object", self._state())
        local_verifier = getattr(self.ops, 'verify_runtime_local', None)
        if self._local_input == 'mouse' and local_verifier and cmd not in {'status','disarm','query_result','claim_input','size_settings','diagnose'}:
            try:
                local_verifier()
            except (OSError, ValueError) as error:
                self.on_disconnect()
                return _reject(str(error), self._state())
        if cmd == 'claim_input':
            owner = params.get('owner')
            if owner not in {'hand', 'mouse'} or (self.input_owner != owner and self._local_input != 'mouse'):
                return _reject('input owner requires explicit local mouse handover', self._state())
            foreground = getattr(self.ops, 'foreground_ok', None)
            if foreground is not None and not foreground():
                return _reject('target window is not foreground', self._state())
            self.input_owner = owner
            self.armed = False
            self.ops.on_disconnect()
            if owner == 'mouse':
                self.session = None; self._seen.clear()
            return {'ok': True, 'result': {'input_owner': owner}}
        if cmd == 'recognition_lost':
            if self.input_owner != 'hand':
                return _reject('input owned by '+self.input_owner, self._state())
            self.ops.on_disconnect()
            return {'ok': True, 'result': {'frozen': bool(self.ops.has_draft())}}
        if self.input_owner != (self._local_input or 'hand') and cmd not in {'status','query_result','disarm','diagnose'}:
            return _reject('input owned by '+self.input_owner, self._state())

        if not self.armed and cmd not in PRE_ARM_COMMANDS:
            return _reject("not armed", self._state())

        draft_active = bool(self.ops.has_draft())
        required = MODE_REQUIRED.get(cmd)
        if required is not None:
            allowed = required if isinstance(required, set) else {required}
            if self.mode not in allowed:
                return _reject(
                    f"command requires mode {sorted(allowed)}",
                    self._state(),
                )
        if cmd in DRAFT_REQUIRED and not draft_active:
            return _reject("no active draft", self._state())
        if cmd in NO_DRAFT_REQUIRED and draft_active:
            return _reject("draft already exists", self._state())
        if cmd == "select_layer" and draft_active:
            return _reject("layer change forbidden during draft",
                           self._state())
        if cmd == "select_mode":
            mode = params.get("mode")
            if mode not in MODES:
                return _reject("unknown mode", self._state())
            if draft_active and mode in {"aim", "review"}:
                return _reject("mode not allowed during draft",
                               self._state())
            if not draft_active and mode in {"move", "rotate", "tilt"}:
                return _reject("mode requires an active draft",
                               self._state())
        if cmd == "select_layer":
            if params.get("layer") not in LAYERS:
                return _reject("unknown layer", self._state())
        if cmd == "query_result":
            # read-only lookup of a previously issued request's stored
            # response; never re-executes the command (plan §共通契約)
            req = params.get("req")
            stored = self._seen.get(req) if isinstance(req, str) else None
            if stored is None and isinstance(req, str):
                finder = getattr(self.ops, 'query_persisted_result', None)
                stored = finder(req) if finder else None
            if stored is None:
                return _reject("unknown request id", self._state())
            return {"ok": True, "result": {"response": stored}}

        # foreground gate: edits and view changes require the target
        # window to be active. Ops without a foreground_ok method are
        # headless/test doubles and exempt.
        if cmd not in FOREGROUND_EXEMPT:
            foreground_ok = getattr(self.ops, "foreground_ok", None)
            if foreground_ok is not None and not foreground_ok():
                return _reject("target window is not foreground",
                               self._state())

        handler = getattr(self.ops, f"op_{cmd}", None)
        if handler is None:
            return _reject("command not implemented", self._state())
        try:
            target_validator = getattr(self.ops, 'verify_action_target', None)
            if target_validator:
                target_validator(cmd, params)
            context=getattr(self.ops,'_request_context',None)
            if isinstance(context,dict):
                context['accepted_ns']=time.perf_counter_ns()
            result = handler(params)
        except Exception as error:  # noqa: BLE001
            return _reject(f"rejected: {error}", self._state())

        if result.get("ok", True):
            if cmd == "arm":
                self.armed = True
            elif cmd == "disarm":
                self.armed = False
            elif cmd == "select_mode":
                self.mode = params["mode"]
            elif cmd == "select_layer":
                self.layer = params["layer"]
        return result

    def dispatch_local(self, cmd: str, params: dict | None = None, input_method=None) -> dict:
        """Execute a command on behalf of a locally trusted caller (e.g.
        a menu_confirm inside the module). Runs the same armed/mode/
        draft gates as wire commands but requires no envelope fields."""
        if cmd not in KNOWN_COMMANDS:
            return _reject("unknown command", self._state())
        previous = self._local_input
        self._local_input = input_method
        self.ops._request_context = {'req': uuid.uuid4().hex, 'cmd': cmd,
                                     'input_method': input_method or 'hand', 'params':params or {}}
        try:
            result = self._execute(cmd, params or {})
        finally:
            self._local_input = previous
        response = {
            "ok": result.get("ok", True),
            "state": self._state(),
        }
        if "reason" in result:
            response["reason"] = result["reason"]
        for key in ("result", "draft_id", "event_id", "menu"):
            if key in result:
                response[key] = result[key]
        return response

    # --- mode / layer bookkeeping (driven by ops results) ------------

    def _state(self) -> dict:
        return {
            "armed": self.armed,
            "mode": self.mode,
            "layer": self.layer,
            "draft": bool(self.ops.has_draft()),
            'input_owner': self.input_owner,
        }

    def on_disconnect(self) -> None:
        """Connection loss: disarm and freeze any draft (never cancel).
        Reconnection alone must not resume control."""
        self.armed = False
        self.session = None
        self._last_seq = 0
        self._seen.clear()
        self.ops.on_disconnect()
