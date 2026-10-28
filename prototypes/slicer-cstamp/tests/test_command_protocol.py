import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from command_protocol import CommandDispatcher  # noqa: E402


@pytest.mark.parametrize('error',[ValueError('duplicate event identity'),OSError('ledger unavailable')])
def test_bad_persisted_history_returns_rejection_instead_of_transport_timeout(error):
    import json,time
    ops=FakeOps();dispatcher=CommandDispatcher(ops)
    session=dispatcher.handle_line(json.dumps({'cmd':'hello','v':1}))['session']
    ops.draft=True;dispatcher.armed=True
    def fail(request_id):raise error
    ops.query_persisted_result=fail
    response=dispatcher.handle_line(json.dumps({'v':1,'cmd':'commit','session':session,
        'seq':1,'req':'bad-ledger','ts':time.time(),'params':{}}))
    assert not response['ok'] and response['req']=='bad-ledger'
    assert str(error) in response['reason']
    assert ops.draft and dispatcher.session==session
    assert response['server_timing']['accepted_ns'] is None


def test_rejected_operation_is_not_reported_as_accepted():
    import json,time
    dispatcher=CommandDispatcher(FakeOps())
    session=dispatcher.handle_line(json.dumps({'cmd':'hello','v':1}))['session']
    response=dispatcher.handle_line(json.dumps({'v':1,'cmd':'stamp','session':session,
        'seq':1,'req':'stopped-stamp','ts':time.time(),'params':{}}))
    assert not response['ok']
    assert response['server_timing']['accepted_ns'] is None
    assert response['server_timing']['envelope_validated_ns'] is not None


def test_target_validator_runs_before_mutating_handler():
    ops=FakeOps();dispatcher=CommandDispatcher(ops);dispatcher.armed=True;dispatcher.mode='aim'
    def rejected(cmd,params):
        if cmd=='stamp':raise RuntimeError('target changed')
    ops.verify_action_target=rejected
    response=dispatcher.dispatch_local('stamp')
    assert not response['ok'] and not ops.draft


def test_runtime_change_invalidates_old_session_even_after_configuration_is_restored():
    import json,time
    ops=FakeOps();changed=[False]
    ops.verify_runtime_hello=lambda actual:'a'*64
    def verify(requested,accepted):
        if changed[0] or requested!=accepted:raise ValueError('configuration changed')
    ops.verify_runtime_request=verify
    dispatcher=CommandDispatcher(ops)
    session=dispatcher.handle_line(json.dumps({'cmd':'hello','v':1}))['session']
    def request(seq):
        return dispatcher.handle_line(json.dumps({'v':1,'cmd':'arm','session':session,'seq':seq,'req':str(seq),
                                                   'ts':time.time(),'params':{},'runtime_hash':'a'*64}))
    assert request(1)['ok']
    changed[0]=True;assert not request(2)['ok']
    assert dispatcher.session is None and not dispatcher.armed
    changed[0]=False;assert not request(3)['ok']


def test_trace_cannot_smuggle_camera_or_arbitrary_payload_into_saved_receipts():
    import json,time
    dispatcher=CommandDispatcher(FakeOps())
    session=dispatcher.handle_line(json.dumps({'v':1,'cmd':'hello'}))['session']
    response=dispatcher.handle_line(json.dumps({'v':1,'session':session,'seq':1,'req':'bad-trace','ts':time.time(),
                                                 'cmd':'arm','params':{},'trace':{'camera_image':'not allowed'}}))
    assert not response['ok'] and 'metadata trace' in response['reason']
    assert not dispatcher.armed


class FakeOps:
    """Minimal operations stub: tracks calls and a draft flag."""

    def __init__(self):
        self.draft = False
        self.calls = []

    def has_draft(self):
        return self.draft

    def on_session_reset(self):
        self.calls.append("session_reset")

    def on_disconnect(self):
        self.draft = False
        self.calls.append("disconnect")

    def op_arm(self, params):
        return {"ok": True}

    def op_disarm(self, params):
        return {"ok": True}

    def op_stamp(self, params):
        self.draft = True
        return {"ok": True, "draft_id": "draft-0001"}

    def op_commit(self, params):
        self.draft = False
        return {"ok": True, "event_id": "evt-1"}

    def op_cancel(self, params):
        self.draft = False
        return {"ok": True}

    def op_view_rotate(self, params):
        self.calls.append(("rotate", params))
        return {"ok": True}

    def op_aim(self, params):
        return {"ok": True}

    def __getattr__(self, name):
        # generic handler for commands without specific test assertions
        if name.startswith("op_"):
            return lambda params: {"ok": True}
        raise AttributeError(name)


def make_dispatcher(now_value=1000.0):
    ops = FakeOps()
    disp = CommandDispatcher(ops, ttl_ms=2000.0,
                             now=lambda: now_value)
    return ops, disp


def hello(disp):
    response = disp.handle_line('{"cmd":"hello","v":1}')
    assert response["ok"]
    return response["session"]


def cmd(disp, session, seq, name, params=None, ts=1000.0, req=None):
    import json
    line = json.dumps({
        "v": 1, "session": session, "seq": seq, "req": req or f"r{seq}",
        "cmd": name, "ts": ts, "params": params or {},
    })
    return disp.handle_line(line)


def arm(disp, session):
    return cmd(disp, session, 1, "arm")


def test_hello_allocates_session_and_resets():
    ops, disp = make_dispatcher()
    session = hello(disp)
    assert session
    assert ops.calls == ["disconnect", "session_reset"]
    assert disp.armed is False


def test_command_without_session_rejected():
    ops, disp = make_dispatcher()
    response = cmd(disp, "x", 1, "arm")
    assert not response["ok"]
    assert "no session" in response["reason"]


def test_not_armed_rejects_commands():
    ops, disp = make_dispatcher()
    session = hello(disp)
    response = cmd(disp, session, 1, "view_rotate",
                   {"dx": 5, "dy": 0})
    assert not response["ok"]
    assert "not armed" in response["reason"]


def test_arm_then_view_command():
    ops, disp = make_dispatcher()
    session = hello(disp)
    assert arm(disp, session)["ok"]
    response = cmd(disp, session, 2, "view_rotate", {"dx": 5, "dy": 0})
    assert response["ok"]
    assert ops.calls[-1] == ("rotate", {"dx": 5, "dy": 0})


def test_wrong_session_rejected():
    ops, disp = make_dispatcher()
    hello(disp)
    response = cmd(disp, "other", 1, "arm")
    assert not response["ok"]
    assert "wrong session" in response["reason"]


def test_non_increasing_seq_rejected():
    ops, disp = make_dispatcher()
    session = hello(disp)
    assert arm(disp, session)["ok"]
    assert not cmd(disp, session, 1, "disarm")["ok"]


def test_duplicate_req_returns_cached_response():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    first = cmd(disp, session, 2, "status", req="dup")
    second = cmd(disp, session, 3, "status", req="dup")
    assert first["ok"] and second["ok"]
    assert second["deduplicated"] is True


def test_stale_timestamp_rejected():
    ops, disp = make_dispatcher(now_value=2000.0)
    session = hello(disp)
    response = cmd(disp, session, 1, "arm", ts=1000.0)
    assert not response["ok"]
    assert "stale" in response["reason"]


def test_view_commands_allowed_in_any_mode():
    # FR-021: zoom (and camera moves generally) must stay available in
    # every mode, including while a draft is open — they only move the
    # camera and never touch draft or ledger data.
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    assert cmd(disp, session, 2, "select_mode",
               {"mode": "aim"})["ok"]
    assert cmd(disp, session, 3, "view_rotate",
               {"dx": 1, "dy": 0})["ok"]
    assert cmd(disp, session, 4, "zoom", {"ratio": 1.05})["ok"]
    assert cmd(disp, session, 5, "stamp")["ok"]
    # draft now exists in aim mode: zoom still allowed, draft untouched
    assert cmd(disp, session, 6, "zoom", {"ratio": 0.95})["ok"]
    assert cmd(disp, session, 7, "view_pan",
               {"dx": 0, "dy": 1})["ok"]
    assert ops.has_draft()


def test_stamp_then_mode_restrictions():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    cmd(disp, session, 2, "select_mode", {"mode": "aim"})
    assert cmd(disp, session, 3, "stamp")["ok"]
    # draft now exists: select_layer forbidden, aim mode forbidden
    assert not cmd(disp, session, 4, "select_layer",
                   {"layer": "PLANNED"})["ok"]
    assert not cmd(disp, session, 5, "select_mode",
                   {"mode": "aim"})["ok"]
    assert cmd(disp, session, 6, "select_mode",
               {"mode": "rotate"})["ok"]


def test_edit_modes_require_draft():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    response = cmd(disp, session, 2, "select_mode", {"mode": "move"})
    assert not response["ok"]


def test_commit_requires_draft():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    assert not cmd(disp, session, 2, "commit")["ok"]


def test_disconnect_disarms_and_freezes():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    cmd(disp, session, 2, "select_mode", {"mode": "aim"})
    cmd(disp, session, 3, "stamp")
    disp.on_disconnect()
    assert disp.armed is False
    assert ops.draft is False or "disconnect" in ops.calls
    # new session does not inherit armed
    session2 = hello(disp)
    assert not cmd(disp, session2, 1, "commit")["ok"]


def test_unknown_and_malformed_are_inert():
    ops, disp = make_dispatcher()
    hello(disp)
    assert not disp.handle_line("not json")["ok"]
    assert not disp.handle_line("[1,2]")["ok"]
    assert not disp.handle_line('{"cmd":"shell","v":1}')["ok"]


def test_select_layer_param_validated():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    assert not cmd(disp, session, 2, "select_layer",
                   {"layer": "BOGUS"})["ok"]
    assert cmd(disp, session, 3, "select_layer",
               {"layer": "PLANNED"})["ok"]
    assert disp.layer == "PLANNED"


def test_diagnose_runs_while_disarmed_and_does_not_mutate():
    ops, disp = make_dispatcher()
    response = disp.dispatch_local('diagnose', input_method='mouse')
    assert response['ok']
    state = response['state']
    assert state['armed'] is False and state['draft'] is False
    assert not disp.armed and not ops.draft


def test_diagnose_is_not_blocked_by_foreign_input_owner():
    ops, disp = make_dispatcher()
    disp.input_owner = 'mouse'
    response = disp.dispatch_local('diagnose')
    assert response['ok']
    assert disp.input_owner == 'mouse'
    assert not disp.armed


def test_diagnose_survives_runtime_mismatch_on_local_and_wire():
    import json, time
    ops, disp = make_dispatcher()
    ops.verify_runtime_local = lambda: (_ for _ in ()).throw(ValueError('runtime mismatch'))
    ops.verify_runtime_hello = lambda actual: 'a' * 64
    def fail_request(requested, accepted):
        raise ValueError('runtime mismatch')
    ops.verify_runtime_request = fail_request
    assert disp.dispatch_local('diagnose', input_method='mouse')['ok']
    assert disp.session is None
    session = hello(disp)
    response = cmd(disp, session, 1, 'diagnose')
    assert response['ok'] and disp.session == session


def test_diagnose_is_foreground_exempt_on_wire():
    ops, disp = make_dispatcher()
    ops.foreground_ok = lambda: False
    session = hello(disp)
    assert cmd(disp, session, 1, 'diagnose')['ok']
