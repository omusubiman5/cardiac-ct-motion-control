"""Self-verification of losses, ownership, input exclusivity and total zoom bounds."""
import pytest
from input_lease import InputLease
from op_controller import OperationController
from tests.test_op_controller import Clock, FakeClient


def test_process_lease_excludes_second_input_then_releases(tmp_path):
    first,second=InputLease(18945,tmp_path),InputLease(18945,tmp_path)
    first.acquire()
    with pytest.raises(OSError,match='already active'): second.acquire()
    first.release();second.acquire();second.release()


def test_loss_notifies_once_and_does_not_resume_without_explicit_request():
    clock,client=Clock(),FakeClient()
    client.last_state.update(armed=True,draft=True,mode='rotate')
    ops=OperationController(client,now=clock,panel_menu=True)
    # transient loss below the grace window never freezes
    ops.recognition_lost('low confidence');ops.recognition_lost('missing')
    assert client.sent==[]
    # sustained loss past the grace window freezes once
    clock.t+=2.0
    ops.recognition_lost('missing')
    assert [cmd for cmd,_ in client.sent]==['recognition_lost']
    assert ops._loss_notified
    ops._send('resume_draft')
    assert not ops._loss_notified


def test_mouse_owner_is_not_reported_as_live_hand_execution():
    client=FakeClient();client.last_state.update(armed=True,input_owner='mouse')
    assert not OperationController(client).armed


def test_ui_arm_and_all_accepted_commands_reset_inactivity_clock():
    clock,client=Clock(),FakeClient();ops=OperationController(client,now=clock)
    ops._send('arm');assert ops.last_accepted_at==100
    clock.t=110;ops._send('status');assert ops.last_accepted_at==100
    ops._send('view_rotate',{'dx':1,'dy':0});assert ops.last_accepted_at==110


def test_wheel_total_ratio_is_bounded_and_never_drifts_after_release():
    client=FakeClient();client.last_state['armed']=True
    ops=OperationController(client)
    product=1
    for _ in range(500): product*=ops.zoom_step(100)['ok'] and client.sent[-1][1]['ratio']
    assert product==pytest.approx(ops._zoom.config.max_ratio)
    assert ops._zoom.velocity==0
    for _ in range(500): ops.zoom_step(-100)
    assert ops._zoom.ratio==pytest.approx(ops._zoom.config.min_ratio)
