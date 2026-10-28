"""Self checks of real controller gestures; no claim of real-hand acceptance."""
from gesture_fsm import Shape
from op_controller import OperationController
from tests.test_op_controller import Clock, FakeClient
import pytest


def rig():
    clock, client = Clock(), FakeClient()
    client.last_state["armed"] = True
    return clock, client, OperationController(client, gesture_hold_s=0.2, now=clock, panel_menu=True)


def test_saved_plan_version_menu_keeps_integer_version_and_original_binding():
    clock,client,ops=rig()
    binding={'plan_id':'p','version':2,'hash':'original'}
    ops.panel_menu.choices={'plan_versions':[1,2]}
    ops.panel_menu.show('plan_versions');ops.panel_menu.choice_revision=binding.copy()
    assert ops.panel_menu.entries[0].label=='第1版'
    ops.status_details={'plan_revision':{'plan_id':'different'}}
    gesture(clock,ops,Shape.FIST)
    assert ('select_plan_version',{'version':1,'plan_revision':binding}) in client.sent


def gesture(clock, ops, shape):
    ops.update(Shape.NONE, None)
    clock.t += 0.25
    ops.update(Shape.NONE, None)
    ops.update(shape, None)
    clock.t += 0.25
    return ops.update(shape, None)


def test_main_c_choice_dispatches_only_aim():
    clock, client, ops = rig()
    gesture(clock, ops, Shape.ILOVEYOU)
    assert len(ops.panel_menu.entries) == 2
    gesture(clock, ops, Shape.THUMB_DOWN)
    assert client.sent == []
    gesture(clock, ops, Shape.FIST)
    assert client.sent == [("select_mode", {"mode": "aim"})]
    assert not ops.menu_open


def test_confirm_requires_a_second_released_fist_and_binds_revision():
    clock, client, ops = rig()
    client.last_state["draft"] = True
    ops._last_draft_rev = 7
    ops.status_details = {"displayed":{"draft_id":"d7","rev":7,"hash":"rendered"}}
    original = client.send
    def send(cmd, params=None):
        response = original(cmd, params)
        if cmd == "status":
            response["result"] = {"rev":ops._last_draft_rev,"displayed":{"draft_id":"d7","rev":ops._last_draft_rev,"hash":"rendered"}}
        return response
    client.send = send
    gesture(clock, ops, Shape.FIST)
    assert ops.panel_menu.page == "confirm"
    assert client.sent == [("status", {})]
    clock.t += 2
    ops.update(Shape.FIST, None)
    assert client.sent == [("status", {})]
    gesture(clock, ops, Shape.FIST)
    assert client.sent == [("status", {}), ("commit", {"draft_id":"d7","rev":7,"hash":"rendered"}),
                           ("select_mode", {"mode": "view"})]
    assert not ops.menu_open


def test_back_from_confirm_does_not_cancel_draft():
    clock, client, ops = rig()
    client.last_state["draft"] = True
    gesture(clock, ops, Shape.FIST)
    # down past the last confirm entry returns to the edit page
    gesture(clock, ops, Shape.THUMB_DOWN)
    gesture(clock, ops, Shape.THUMB_DOWN)
    assert ops.panel_menu.page == "edit"
    assert client.sent == [("status", {})] and ops.draft


@pytest.mark.parametrize("page", ["plans", "plan_versions", "creators", "storages", "plan_items"])
def test_down_past_end_returns_from_registered_choice_without_dispatch(page):
    clock, client, ops = rig()
    # A local return must not select, save, revoke or cancel data, even if a
    # draft becomes visible while the choices page is already open.
    client.last_state["draft"] = True
    ops.panel_menu.show(page)
    ops.menu_open = True
    gesture(clock, ops, Shape.THUMB_DOWN)
    assert ops.panel_menu.page == "records" and ops.menu_open
    ops.panel_menu.index = len(ops.panel_menu.entries) - 1
    gesture(clock, ops, Shape.THUMB_DOWN)
    assert ops.panel_menu.page == "main" and ops.menu_open
    ops.panel_menu.index = len(ops.panel_menu.entries) - 1
    gesture(clock, ops, Shape.THUMB_DOWN)
    assert not ops.menu_open and ops.draft
    clock.t += 2
    ops.update(Shape.THUMB_DOWN, None)
    assert client.sent == [] and ops.draft


def test_revision_change_refuses_commit():
    clock, client, ops = rig()
    client.last_state["draft"] = True
    ops._last_draft_rev = 7
    gesture(clock, ops, Shape.FIST)
    ops._last_draft_rev = 8
    gesture(clock, ops, Shape.FIST)
    assert client.sent == [("status", {})]
    assert "変わりました" in ops.panel_menu.notice


def test_transport_loss_clears_confirmation():
    clock, client, ops = rig()
    client.last_state["draft"] = True
    ops._last_draft_rev = 2
    gesture(clock, ops, Shape.FIST)
    client.connected = False
    ops.update(Shape.FIST, None)
    assert not ops.panel_menu.opened
    assert ops.panel_menu.confirm_revision is None
    assert client.sent == [("status", {})]


def test_main_menu_contains_only_the_tree_branches():
    # The approved tree puts only view work and the C branch in the hand
    # menu; records/correction/stop are mouse operations (詳細マウス操作).
    clock, client, ops = rig()
    gesture(clock, ops, Shape.ILOVEYOU)
    assert [entry.key for entry in ops.panel_menu.entries] == ["view", "c"]
    # past the last entry closes the menu without dispatching anything
    for _ in range(2):
        gesture(clock, ops, Shape.THUMB_DOWN)
    assert not ops.panel_menu.opened and client.sent == []


def test_draft_edit_selection_uses_guarded_typed_command_not_old_server_menu():
    clock, client, ops = rig()
    client.last_state["draft"] = True
    gesture(clock, ops, Shape.ILOVEYOU)
    gesture(clock, ops, Shape.THUMB_DOWN)
    gesture(clock, ops, Shape.FIST)
    assert ops.panel_menu.page == "edit"
    gesture(clock, ops, Shape.THUMB_DOWN)
    gesture(clock, ops, Shape.FIST)
    assert client.sent == [("cancel", {}), ("select_mode", {"mode": "view"})]
    assert not ops.menu_open


def test_refused_selection_keeps_menu_visible():
    clock, client, ops = rig()
    client.send = lambda cmd, params: {"ok": False, "reason": "target window is not foreground"}
    gesture(clock, ops, Shape.ILOVEYOU)
    gesture(clock, ops, Shape.FIST)
    assert ops.menu_open
    assert "foreground" in ops.panel_menu.notice
