import math
import pytest
from gesture_fsm import Shape, classify_shape
from motion_engine import Point
from tests.test_gesture_fsm import make_landmarks
from tests.test_op_controller import Clock, FakeClient
from op_controller import OperationController

@pytest.mark.parametrize('mode', ['view','rotate','tilt'])
def test_arm_hold_cannot_move_existing_camera_or_draft(mode):
    clock, client = Clock(), FakeClient()
    client.last_state.update(mode=mode, draft=mode!='view')
    ops = OperationController(client, now=clock, arm_hold_s=.2)
    for i in range(30):
        lm=make_landmarks(index=True,middle=True,ring=True,pinky=True)
        lm={k:Point(p.x+i*.01,p.y+i*.01) for k,p in lm.items()}
        ops.update(Shape.ILOVEYOU,lm)
        clock.t+=.05
    # arming may return home (menu_open) but must never move the camera
    # or an existing draft
    assert [cmd for cmd,_ in client.sent] == ['arm','menu_open']
    assert all(cmd not in {'view_rotate','view_pan','stamp','move_draft',
                           'rotate_opening','tilt','cancel','commit'}
               for cmd,_ in client.sent)

@pytest.mark.parametrize('mode',['move','rotate','tilt'])
@pytest.mark.parametrize('shape',[Shape.UNKNOWN,Shape.POINT,Shape.PINCH])
def test_c_direction_rejects_other_shapes_and_unknown_landmarks(mode,shape):
    clock,client=Clock(),FakeClient()
    client.last_state.update(armed=True,draft=True,mode=mode)
    ops=OperationController(client,now=clock)
    for i in range(10):
        lm={k:Point(p.x+i*.1,p.y+i*.1) for k,p in make_landmarks().items()}
        ops.update(shape,lm); clock.t+=.1
    # During draft editing POINT re-anchors the C and PINCH turns the
    # opening; UNKNOWN does nothing at all.
    if shape is Shape.PINCH:
        assert client.sent and all(
            cmd in {'select_mode','rotate_opening'} for cmd,_ in client.sent)
    elif shape is Shape.POINT:
        assert all(cmd in {'select_mode','move_draft'} for cmd,_ in client.sent)
    else:
        assert client.sent == []

@pytest.mark.parametrize('degrees',[0,45,90,180,-90])
def test_two_fingers_uses_hand_axis_instead_of_screen_vertical(degrees):
    lm=make_landmarks(index=True,middle=True)
    a=math.radians(degrees)
    transformed={k:Point(.5+(p.x-.5)*math.cos(a)-(p.y-.7)*math.sin(a),
                          .7+(p.x-.5)*math.sin(a)+(p.y-.7)*math.cos(a)) for k,p in lm.items()}
    assert classify_shape(transformed) is Shape.TWO

def test_thumb_index_contact_inside_closed_fist_is_not_pinch():
    lm=make_landmarks()
    lm[4]=Point(lm[8].x,lm[8].y)
    assert classify_shape(lm) is Shape.FIST

def test_unrecognized_or_absent_hand_issues_nothing_after_arm():
    clock,client=Clock(),FakeClient()
    ops=OperationController(client,now=clock)
    ops._send('arm')
    for _ in range(20):
        ops.update(Shape.NONE,None); clock.t+=.05
        ops.update(Shape.UNKNOWN,None); clock.t+=.05
    assert client.sent == [('arm', {})] and ops.armed

def test_folded_contact_ahead_of_knuckle_is_unknown_not_cancel():
    lm=make_landmarks()
    lm[8]=Point(.5,.66)
    lm[4]=lm[8]
    assert classify_shape(lm) is Shape.UNKNOWN

def test_slow_open_palm_accumulates_across_rotation_deadzone():
    clock,client=Clock(),FakeClient()
    client.last_state.update(armed=True,draft=True,mode='rotate')
    ops=OperationController(client,now=clock)
    for i in range(10):
        lm={k:Point(p.x+i*.005,p.y) for k,p in make_landmarks(index=True,middle=True,ring=True,pinky=True).items()}
        ops.update(Shape.OPEN_PALM,lm); clock.t+=.05
    # open palm always rotates the camera, even while editing a draft
    assert client.sent and all(cmd=='view_rotate' for cmd,_ in client.sent)
