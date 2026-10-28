"""Self-check from folded-hand geometry to the menu decide action."""
from gesture_fsm import Shape, classify_shape
from motion_engine import Point
from tests.test_gesture_fsm import make_landmarks
from tests.test_panel_menu import rig, gesture


def test_folded_long_thumb_decides_the_highlighted_menu_item():
    clock, client, ops = rig()
    gesture(clock, ops, Shape.ILOVEYOU)
    assert ops.panel_menu.page == 'main'
    lm = make_landmarks()
    lm[2], lm[3], lm[4], lm[8] = Point(.40,.78), Point(.36,.71), Point(.49,.65), Point(.50,.80)
    shape = classify_shape(lm)
    assert shape is Shape.FIST
    # the first main item is 視点操作; the folded shape selects it
    gesture(clock, ops, shape)
    assert client.sent == [('select_mode', {'mode': 'view'})]
    assert not ops.panel_menu.opened
