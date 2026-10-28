import pytest
from gesture_fsm import Shape
from motion_engine import Point
from op_controller import OperationController
from tests.test_gesture_fsm import make_landmarks
from tests.test_op_controller import Clock, FakeClient, hold
from tests.test_standard_gesture import observation
from standard_gesture import operation_shape


def test_palm_no_longer_starts_and_uncertain_iloveyou_does_not_start():
    clock, client = Clock(), FakeClient()
    ops = OperationController(client, now=clock, arm_hold_s=.2)
    hold(ops, clock, Shape.OPEN_PALM, 2)
    hold(ops, clock, operation_shape(observation('ILoveYou', .2)), 2)
    assert client.sent == []


@pytest.mark.parametrize('shape,command', [(Shape.OPEN_PALM,'view_rotate'),
                                         (Shape.POINT,'view_pan'), (Shape.PINCH,'zoom')])
def test_resume_in_frame_stabilizes_then_seeds_motion_without_jump(shape, command):
    clock, client = Clock(), FakeClient()
    ops = OperationController(client, now=clock, arm_hold_s=.2, gesture_hold_s=.2)
    lm = make_landmarks(index=True, middle=True, ring=True, pinky=True)
    hold(ops, clock, Shape.ILOVEYOU, .8, lm)
    # arming returns home: the main menu opens
    assert client.sent == [('arm', {}), ('menu_open', {})]
    hold(ops, clock, Shape.NONE, .3)
    ops.menu_open = False   # operator dismissed the menu (e.g. thumb-down)
    # Hand stays visible throughout. Large repositioning while changing
    # shape must not turn into camera movement during the settle window.
    for i in range(3):
        shifted = {k:Point(p.x+i*.03,p.y+i*.03) for k,p in lm.items()}
        ops.update(shape, shifted)
        clock.t += .04
    assert all(cmd in {'arm', 'menu_open'} for cmd,_ in client.sent)
    # after the hold window the settled hand drives the motion
    for i in range(4, 12):
        shifted = {k:Point(p.x+i*.03,p.y+i*.03) for k,p in lm.items()}
        ops.update(shape, shifted)
        clock.t += .04
    cmds = [cmd for cmd,_ in client.sent]
    assert command in cmds
    assert all(cmd in {'arm', 'menu_open', command} for cmd in cmds)


def test_unknown_then_work_shape_preserves_mode_and_draft():
    clock, client = Clock(), FakeClient()
    client.last_state.update(armed=True, mode='move', draft=True)
    ops = OperationController(client, now=clock, gesture_hold_s=.35)
    for i in range(16):
        lm = {k: Point(p.x+i*.01, p.y) for k, p in make_landmarks().items()}
        ops.update(Shape.OPEN_PALM, lm)
        clock.t += .05
        if i == 4:
            ops.update(Shape.UNKNOWN, None)
            clock.t += .05
    assert ops.mode == 'move' and ops.draft
    # open palm only ever rotates the camera — the draft is untouched
    assert client.sent
    assert all(cmd == 'view_rotate' for cmd,_ in client.sent)


def test_iloveyou_while_armed_returns_home_and_preserves_draft():
    clock, client = Clock(), FakeClient()
    client.last_state.update(armed=True, draft=True, mode='move')
    ops = OperationController(client, now=clock)
    hold(ops, clock, Shape.ILOVEYOU, .5)
    # armed I Love You = return to the start: menu opens, draft kept
    assert client.sent == [('menu_open', {})]
    assert ops.draft and ops.mode == 'move'


def test_iloveyou_while_armed_and_draft_frozen_resumes_draft():
    clock, client = Clock(), FakeClient()
    client.last_state.update(armed=True, draft=True, mode='move')
    ops = OperationController(client, now=clock)
    ops.draft_frozen = True
    hold(ops, clock, Shape.ILOVEYOU, .5)
    # frozen draft: I Love You resumes editing without opening the menu —
    # an open menu would eat the next FIST as a selection and block the
    # confirm path (仮置き→🤟解除→グー→グー確定 must not detour).
    assert client.sent == [('resume_draft', {})]
    assert ops.draft and ops.mode == 'move'
    assert not ops.menu_open


def test_iloveyou_without_frozen_draft_does_not_resume():
    clock, client = Clock(), FakeClient()
    client.last_state.update(armed=True, draft=True, mode='move')
    ops = OperationController(client, now=clock)
    hold(ops, clock, Shape.ILOVEYOU, .5)
    assert client.sent == [('menu_open', {})]
