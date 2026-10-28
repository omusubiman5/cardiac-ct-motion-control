"""Regression coverage for the single-meaning gesture tree (docs/57)."""
import pytest
from gesture_fsm import Shape
from motion_engine import Point
from op_controller import OperationController
from tests.test_gesture_fsm import make_landmarks
from tests.test_op_controller import Clock, FakeClient, feed, hold
from tests.test_panel_menu import rig as panel_rig, gesture


def rig():
    clock = Clock()
    client = FakeClient()
    client.last_state["armed"] = True
    return clock, client, OperationController(
        client, gesture_hold_s=0.2, now=clock)


def test_stamp_lands_on_stable_point_not_transition_wobble():
    clock, client, ops = rig()
    client.last_state["mode"] = "aim"
    lm = make_landmarks(index=True)
    lm[8] = Point(0.40, 0.40)
    # point steadily -> the still point becomes the decided point
    hold(ops, clock, Shape.POINT, 0.4, landmarks=lm)
    ops._stable_aim = (0.40, 0.40)
    # the shape change to fist wobbles the fingertip first
    lm[8] = Point(0.60, 0.60)
    out = ops.update(Shape.FIST, lm)
    clock.t += 0.25
    ops.update(Shape.FIST, lm)
    clock.t += 0.25
    cmds = [c for c, _ in client.sent]
    assert "stamp" in cmds
    aim = [p for c, p in client.sent if c == "aim"]
    # the placement re-anchors on the stable point, not the wobble
    assert aim[-1] == {"nx": 0.40, "ny": 0.40}


def test_fist_without_aim_mode_does_not_stamp():
    clock, client, ops = rig()
    hold(ops, clock, Shape.FIST, 0.3)
    assert client.sent == []


def test_iloveyou_returns_to_main_from_nested_page():
    clock, client, ops = panel_rig()
    ops.panel_menu.show("records")
    ops.menu_open = True
    gesture(clock, ops, Shape.ILOVEYOU)
    assert ops.panel_menu.page == "main" and ops.menu_open
    assert client.sent == []


def test_iloveyou_while_draft_never_discards_it():
    clock, client, ops = panel_rig()
    client.last_state["draft"] = True
    gesture(clock, ops, Shape.ILOVEYOU)
    assert ops.panel_menu.page == "main"
    assert ops.draft
    assert not any(cmd in {"cancel", "commit"} for cmd, _ in client.sent)


def test_thumb_down_at_last_item_backs_out_instead_of_wrapping():
    clock, client, ops = panel_rig()
    ops.panel_menu.show("main")
    ops.menu_open = True
    ops.panel_menu.index = len(ops.panel_menu.entries) - 1
    gesture(clock, ops, Shape.THUMB_DOWN)
    assert not ops.panel_menu.opened  # main has no parent: it closes


def test_point_during_draft_moves_draft_in_any_edit_mode():
    clock, client, ops = rig()
    client.last_state.update(mode="tilt", draft=True)
    lm = make_landmarks(index=True)
    feed(ops, clock, Shape.POINT, seconds=0.25, landmarks=lm)
    feed(ops, clock, Shape.POINT, seconds=0.05, landmarks=lm)
    feed(ops, clock, Shape.POINT, landmarks=lm)
    # the controller re-entered the move context once, then anchored
    assert client.sent[0] == ("select_mode", {"mode": "move"})
    assert any(cmd == "move_draft" for cmd, _ in client.sent)


def test_view_gestures_still_work_while_menu_is_open():
    """The tree has no mode-lockout: an open menu consumes only the
    navigation gestures; palm/point/pinch/three keep their meaning."""
    clock, client, ops = panel_rig()
    ops.panel_menu.show("main")
    ops.menu_open = True
    lm = make_landmarks(index=True, middle=True, ring=True, pinky=True)
    feed(ops, clock, Shape.OPEN_PALM, seconds=0.3, landmarks=lm)
    lm2 = dict(lm)
    for idx in lm2:
        lm2[idx] = Point(lm2[idx].x + 0.05, lm2[idx].y)
    feed(ops, clock, Shape.OPEN_PALM, seconds=0.4, landmarks=lm2)
    assert "view_rotate" in [c for c, _ in client.sent]


def test_zoom_step_still_works_while_draft():
    """The mouse wheel keeps zooming even though hand pinch is bound
    to the opening direction while a provisional C exists."""
    clock, client, ops = rig()
    client.last_state["draft"] = True
    assert ops.zoom_step(2) is not None
    assert client.sent[-1][0] == "zoom"
