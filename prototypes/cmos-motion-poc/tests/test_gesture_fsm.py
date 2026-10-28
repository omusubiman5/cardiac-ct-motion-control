import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gesture_fsm import (  # noqa: E402
    GestureLatch,
    HoldDetector,
    Shape,
    classify_shape,
)
from motion_engine import Point  # noqa: E402


def make_landmarks(index=False, middle=False, ring=False, pinky=False,
                   thumb_out=False, pinch=False):
    """Synthetic 21-landmark hand in image coords (y down)."""
    lm = {i: Point(0.5, 0.9) for i in range(21)}
    lm[0] = Point(0.5, 0.95)
    lm[5] = Point(0.40, 0.70)
    lm[9] = Point(0.50, 0.68)
    lm[13] = Point(0.55, 0.70)
    lm[17] = Point(0.60, 0.70)
    lm[1] = Point(0.44, 0.82)
    lm[2] = Point(0.40, 0.78)
    lm[3] = Point(0.42, 0.76)
    lm[4] = Point(0.46, 0.80)
    for tip, pip, extended in (
        (8, 6, index), (12, 10, middle), (16, 14, ring), (20, 18, pinky)
    ):
        lm[pip] = Point(0.5, 0.60)
        lm[tip] = Point(0.5, 0.50 if extended else 0.72)
    if thumb_out:
        # The documented gesture is a raised thumb, beyond the knuckles.
        lm[3] = Point(0.40, 0.64)
        lm[4] = Point(0.40, 0.50)
    if pinch:
        lm[4] = Point(lm[8].x, lm[8].y)
    return lm


def test_classify_open_palm():
    assert classify_shape(make_landmarks(
        index=True, middle=True, ring=True, pinky=True
    )) is Shape.OPEN_PALM


def test_classify_point():
    assert classify_shape(make_landmarks(index=True)) is Shape.POINT


def test_classify_two_and_three():
    assert classify_shape(
        make_landmarks(index=True, middle=True)) is Shape.TWO
    assert classify_shape(make_landmarks(
        index=True, middle=True, ring=True)) is Shape.THREE


def test_classify_fist_and_thumb():
    assert classify_shape(make_landmarks()) is Shape.FIST
    assert classify_shape(make_landmarks(thumb_out=True)) is Shape.THUMB


@pytest.mark.parametrize('scale,mirror', [(1,False),(.4,False),(1,True)])
def test_long_folded_thumb_is_fist_not_menu_open(scale, mirror):
    lm = make_landmarks()
    lm[2], lm[3], lm[4] = Point(.40,.78), Point(.36,.71), Point(.49,.65)
    lm[8] = Point(.50,.80)  # Folded tip below the thumb; no pinch contact.
    lm = {i:Point((1-p.x if mirror else p.x)*scale, p.y*scale) for i,p in lm.items()}
    assert classify_shape(lm) is Shape.FIST


def test_straight_thumb_inside_knuckles_does_not_open_menu():
    lm = make_landmarks()
    lm[2], lm[3], lm[4] = Point(.40,.78), Point(.45,.75), Point(.50,.72)
    lm[8] = Point(.50,.80)
    assert classify_shape(lm) is Shape.FIST


def test_missing_thumb_joint_cannot_be_invented_as_fist_or_thumb():
    lm = make_landmarks()
    del lm[3]
    assert classify_shape(lm) is Shape.UNKNOWN


def test_partly_extended_thumb_is_inert_not_fist_cancel():
    lm = make_landmarks()
    lm[2], lm[3], lm[4], lm[8] = Point(.40,.78), Point(.34,.69), Point(.24,.675), Point(.50,.80)
    assert classify_shape(lm) is Shape.UNKNOWN


@pytest.mark.parametrize('mirror', [False, True])
def test_straight_thumb_on_side_of_fist_does_not_open_menu(mirror):
    lm = make_landmarks()
    # All three previous THUMB criteria pass (180deg, long, outside),
    # but this thumb lies beside the clenched knuckles, not above them.
    lm[2], lm[3], lm[4] = Point(.40,.78), Point(.36,.735), Point(.32,.69)
    if mirror:
        lm = {i:Point(1-p.x,p.y) for i,p in lm.items()}
    assert classify_shape(lm) is Shape.FIST


def test_classify_pinch_and_unknown():
    assert classify_shape(
        make_landmarks(index=True, pinch=True)) is Shape.PINCH
    # ring only extended is not a defined shape
    assert classify_shape(make_landmarks(ring=True)) is Shape.UNKNOWN
    assert classify_shape(None) is Shape.NONE


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_latch_fires_once_per_hold():
    clock = Clock()
    latch = GestureLatch(hold_s=0.3, now=clock)
    two = make_landmarks(index=True, middle=True)
    shape = classify_shape(two)
    for _ in range(3):  # 0.0s .. hold not yet complete
        assert latch.update(shape) is None
        clock.t += 0.1
    # 0.3s reached
    assert latch.update(shape) is Shape.TWO
    # holding further does not re-fire
    clock.t += 1.0
    assert latch.update(shape) is None


def test_latch_rearm_requires_release():
    clock = Clock()
    latch = GestureLatch(hold_s=0.2, now=clock)
    shape = Shape.TWO
    latch.update(shape)  # candidate starts at first observation
    clock.t += 0.3
    assert latch.update(shape) is Shape.TWO
    # release
    assert latch.update(Shape.NONE) is None
    clock.t += 0.25  # a deliberate release, not a single dropped frame
    # re-hold must satisfy hold time again
    assert latch.update(shape) is None  # candidate starts here
    clock.t += 0.25
    assert latch.update(shape) is Shape.TWO


def test_brief_recognition_loss_does_not_repeat_held_discrete_action():
    clock = Clock()
    latch = GestureLatch(hold_s=0.2, now=clock)
    latch.update(Shape.TWO)
    clock.t += 0.3
    assert latch.update(Shape.TWO) is Shape.TWO
    latch.update(Shape.NONE)
    clock.t += 0.01
    assert latch.update(Shape.TWO) is None
    clock.t += 0.5
    assert latch.update(Shape.TWO) is None


def test_latch_shape_change_restarts_stability():
    clock = Clock()
    latch = GestureLatch(hold_s=0.3, now=clock)
    assert latch.update(Shape.TWO) is None
    clock.t += 0.2
    assert latch.update(Shape.FIST) is None  # candidate changed
    clock.t += 0.2  # only 0.2s on FIST
    assert latch.update(Shape.FIST) is None
    clock.t += 0.1
    assert latch.update(Shape.FIST) is Shape.FIST


def test_latch_ignores_continuous_shapes():
    latch = GestureLatch(hold_s=0.0)
    assert latch.update(Shape.OPEN_PALM) is None
    assert latch.update(Shape.POINT) is None
    assert latch.update(Shape.PINCH) is None


def test_hold_detector_fires_once_while_disarmed():
    clock = Clock()
    hold = HoldDetector(Shape.OPEN_PALM, hold_s=1.0, now=clock)
    assert not hold.update(Shape.OPEN_PALM, armed=False)
    clock.t += 0.5
    assert not hold.update(Shape.OPEN_PALM, armed=False)
    clock.t += 0.6
    assert hold.update(Shape.OPEN_PALM, armed=False)
    clock.t += 1.0
    assert not hold.update(Shape.OPEN_PALM, armed=False)


def test_hold_detector_resets_on_release():
    clock = Clock()
    hold = HoldDetector(Shape.OPEN_PALM, hold_s=1.0, now=clock)
    hold.update(Shape.OPEN_PALM, armed=False)
    clock.t += 0.8
    hold.update(Shape.NONE, armed=False)  # released before hold_s
    clock.t += 0.5
    assert not hold.update(Shape.OPEN_PALM, armed=False)  # restarts


def test_hold_detector_suppressed_when_armed():
    clock = Clock()
    hold = HoldDetector(Shape.OPEN_PALM, hold_s=0.5, now=clock)
    clock.t += 2.0
    assert not hold.update(Shape.OPEN_PALM, armed=True)


def test_progress_is_read_only_and_resets_on_shape_loss():
    clock = Clock()
    hold = HoldDetector(Shape.OPEN_PALM, hold_s=1.5, now=clock)
    assert hold.elapsed_s == 0
    hold.update(Shape.OPEN_PALM, armed=False)
    clock.t += 2.0
    assert hold.elapsed_s == 1.5
    # Reading a completed timer cannot arm; the valid-frame update must fire.
    assert hold.update(Shape.OPEN_PALM, armed=False)
    hold.update(Shape.NONE, armed=False)
    assert hold.elapsed_s == 0
