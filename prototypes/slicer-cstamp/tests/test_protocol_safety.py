"""Dispatcher-level safety tests added for docs/23 second edition:
foreground gating (SR-006), new command allowlist, mouse/hand
equivalence at the dispatch layer (X-02), injection inertness (X-03),
and a dispatcher latency measurement (X-06, measurement only — no
agreed threshold exists, so nothing is asserted as a pass/fail gate).
"""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from command_protocol import (  # noqa: E402
    CommandDispatcher,
    KNOWN_COMMANDS,
)
from test_command_protocol import FakeOps, arm, cmd, hello  # noqa: E402


# --- foreground gate (SR-006) ---------------------------------------


class ForegroundOps(FakeOps):
    def __init__(self):
        super().__init__()
        self.foreground = True

    def foreground_ok(self):
        return self.foreground


def make_foreground_dispatcher(now_value=1000.0):
    ops = ForegroundOps()
    disp = CommandDispatcher(ops, ttl_ms=2000.0, now=lambda: now_value)
    return ops, disp


def test_foreground_loss_blocks_edit_commands():
    ops, disp = make_foreground_dispatcher()
    session = hello(disp)
    arm(disp, session)
    ops.foreground = False
    r = cmd(disp, session, 2, "view_rotate", {"dx": 1, "dy": 0})
    assert not r["ok"]
    assert "foreground" in r["reason"]
    assert ("rotate", {"dx": 1, "dy": 0}) not in ops.calls


def test_foreground_loss_blocks_stamp_and_commit():
    ops, disp = make_foreground_dispatcher()
    session = hello(disp)
    arm(disp, session)
    cmd(disp, session, 2, "select_mode", {"mode": "aim"})
    ops.foreground = False
    assert not cmd(disp, session, 3, "stamp")["ok"]
    assert not ops.draft


def test_foreground_loss_still_allows_status_and_disarm():
    ops, disp = make_foreground_dispatcher()
    session = hello(disp)
    arm(disp, session)
    ops.foreground = False
    assert cmd(disp, session, 2, "status")["ok"]
    assert cmd(disp, session, 3, "menu_open")["ok"]
    assert cmd(disp, session, 4, "disarm")["ok"]


def test_foreground_restored_allows_commands():
    ops, disp = make_foreground_dispatcher()
    session = hello(disp)
    arm(disp, session)
    ops.foreground = False
    assert not cmd(disp, session, 2, "view_rotate",
                   {"dx": 1, "dy": 0})["ok"]
    ops.foreground = True
    assert cmd(disp, session, 3, "view_rotate", {"dx": 1, "dy": 0})["ok"]


# --- new command allowlist -------------------------------------------


@pytest.mark.parametrize("command", [
    "create_plan", "begin_plan_revision", "edit_plan_item",
    "delete_plan_item", "add_plan_item", "move_plan_item",
    "save_plan_revision", "cancel_plan_revision",
    "select_reason", "set_out_of_plan", "revoke_event",
    "confirm_audit", "reset_view",
])
def test_new_commands_reach_ops_when_armed(command):
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    response = cmd(disp, session, 2, command, {"x": 1})
    assert response["ok"], response


@pytest.mark.parametrize("command", [
    "create_plan", "edit_plan_item", "save_plan_revision",
    "revoke_event", "reset_view",
])
def test_new_commands_rejected_when_not_armed(command):
    ops, disp = make_dispatcher()
    session = hello(disp)
    response = cmd(disp, session, 1, command, {"x": 1})
    assert not response["ok"]
    assert "not armed" in response["reason"]


def test_unknown_command_still_inert():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    response = cmd(disp, session, 2, "eval", {"code": "print(1)"})
    assert not response["ok"]
    assert "unknown" in response["reason"]


# --- X-02: dispatch-layer equivalence (wire vs local menu path) ------


def test_wire_and_local_dispatch_reach_identical_gates():
    """The same command list must hit the same ops through the wire
    envelope path and the local (menu/mouse) dispatch path."""
    sequence = [
        ("view_rotate", {"dx": 2, "dy": 0}),
        ("select_mode", {"mode": "aim"}),
        ("stamp", {}),
        ("select_mode", {"mode": "rotate"}),
        ("rotate_opening", {"delta_deg": 10}),
        ("commit", {}),
    ]

    wire_ops, wire_disp = make_dispatcher()
    session = hello(wire_disp)
    arm(wire_disp, session)
    for i, (name, params) in enumerate(sequence, start=2):
        wire_disp.handle_line(json.dumps({
            "v": 1, "session": session, "seq": i,
            "req": f"w{i}", "cmd": name, "ts": 1000.0,
            "params": params,
        }))

    local_ops, local_disp = make_dispatcher()
    hello(local_disp)
    local_disp.dispatch_local("arm")
    for name, params in sequence:
        local_disp.dispatch_local(name, params)

    # both paths arrived at identical op invocations
    wire_only = [c for c in wire_ops.calls if c != "session_reset"]
    local_only = [c for c in local_ops.calls if c != "session_reset"]
    assert wire_only == local_only
    # and identical terminal state
    assert wire_disp._state() == local_disp._state()


# --- X-03: injection battery stays inert ------------------------------


def test_injection_battery_is_inert():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    bad_lines = [
        "",  # empty
        "not json at all",
        "[1,2,3]",
        '"string"',
        "null",
        json.dumps({"cmd": "view_rotate"}),  # no envelope fields
        json.dumps({"v": 2, "session": session, "seq": 2,
                    "req": "x", "cmd": "view_rotate", "ts": 1000.0}),
        json.dumps({"v": 1, "session": "evil", "seq": 2,
                    "req": "x", "cmd": "view_rotate", "ts": 1000.0}),
        json.dumps({"v": 1, "session": session, "seq": 0,
                    "req": "x", "cmd": "view_rotate", "ts": 1000.0}),
        json.dumps({"v": 1, "session": session, "seq": 2,
                    "req": "x", "cmd": "view_rotate", "ts": 1.0}),
        json.dumps({"v": 1, "session": session, "seq": 2,
                    "req": "x", "cmd": "os.system", "ts": 1000.0,
                    "params": {"c": "calc"}}),
        json.dumps({"v": 1, "session": session, "seq": 2,
                    "req": "x", "cmd": "view_rotate", "ts": 1000.0,
                    "params": "drop table"}),
        json.dumps({"v": 1, "session": session, "seq": 2,
                    "req": True, "cmd": "view_rotate", "ts": 1000.0}),
        "x" * 5000,  # oversize line
    ]
    for line in bad_lines:
        response = disp.handle_line(line)
        assert response["ok"] is False, line
    # nothing reached ops, state unchanged
    assert ops.calls == ["disconnect", "session_reset"]
    assert disp.armed is True  # armed survived; no side effects


def test_disconnect_freezes_and_reconnect_requires_hello():
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    cmd(disp, session, 2, "select_mode", {"mode": "aim"})
    cmd(disp, session, 3, "stamp")
    assert ops.draft

    disp.on_disconnect()
    assert disp.armed is False
    # old session id is dead
    r = cmd(disp, session, 4, "status")
    assert not r["ok"]


# --- X-06: dispatcher latency measurement -----------------------------


def test_dispatch_latency_measurement():
    """Measurement only: record handle_line latency distribution.
    No pass/fail threshold — FR-023/PR-001 keep performance acceptance
    undecided until non-clinical measurement is agreed."""
    ops, disp = make_dispatcher()
    session = hello(disp)
    arm(disp, session)
    latencies = []
    for i in range(200):
        line = json.dumps({
            "v": 1, "session": session, "seq": 100 + i,
            "req": f"m{i}", "cmd": "status", "ts": 1000.0,
        })
        start = time.perf_counter()
        disp.handle_line(line)
        latencies.append((time.perf_counter() - start) * 1000.0)
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"\nX-06 dispatch latency ms: p50={p50:.3f} "
          f"p95={p95:.3f} max={latencies[-1]:.3f}")


def make_dispatcher(now_value=1000.0):
    ops = FakeOps()
    disp = CommandDispatcher(ops, ttl_ms=2000.0,
                             now=lambda: now_value)
    return ops, disp
