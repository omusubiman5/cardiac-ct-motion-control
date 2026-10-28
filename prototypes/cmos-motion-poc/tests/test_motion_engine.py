from config import AppConfig
from motion_engine import Gesture, MotionEngine, Point, classify_gesture


def hand(*, open_hand=False, point=False, pinch=False, x=0.5, y=0.5):
    landmarks = {index: Point(x, y) for index in range(21)}
    for index, offset in zip((0, 5, 9, 13, 17), (0.04, 0.02, 0.0, -0.02, -0.04)):
        landmarks[index] = Point(x + offset, y)

    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        landmarks[pip] = Point(x, y - 0.05)
        landmarks[tip] = Point(x, y + 0.05)

    if open_hand:
        for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
            landmarks[tip] = Point(x, landmarks[pip].y - 0.08)
    if point:
        landmarks[8] = Point(x, landmarks[6].y - 0.08)
    landmarks[4] = Point(x - 0.12, y)
    if pinch:
        landmarks[4] = Point(x - 0.01, y - 0.1)
        landmarks[8] = Point(x, y - 0.1)
    return landmarks


def shifted(landmarks, dx=0.0, dy=0.0):
    return {index: Point(point.x + dx, point.y + dy) for index, point in landmarks.items()}


def test_classifies_only_supported_gestures():
    assert classify_gesture(hand(open_hand=True)) is Gesture.ROTATE
    assert classify_gesture(hand(point=True)) is Gesture.PAN
    assert classify_gesture(hand(pinch=True)) is Gesture.ZOOM
    assert classify_gesture(hand()) is Gesture.NONE


def test_engine_is_disabled_by_default():
    engine = MotionEngine(AppConfig())
    assert engine.update(hand(open_hand=True)) is None
    assert engine.gesture is Gesture.NONE


def test_first_frame_arms_tracking_without_motion():
    engine = MotionEngine(AppConfig(smoothing_alpha=1.0, deadzone=0.0))
    engine.set_enabled(True)
    landmarks = hand(open_hand=True)
    assert engine.update(landmarks) is None
    action = engine.update(shifted(landmarks, dx=0.02))
    assert action is not None
    assert action.kind is Gesture.ROTATE
    assert action.dx > 0


def test_recognition_loss_resets_tracking():
    engine = MotionEngine(AppConfig(smoothing_alpha=1.0, deadzone=0.0))
    engine.set_enabled(True)
    landmarks = hand(point=True)
    engine.update(landmarks)
    assert engine.update(None) is None
    assert engine.gesture is Gesture.NONE
    assert engine.update(shifted(landmarks, dx=0.2)) is None


def test_deadzone_suppresses_small_motion():
    engine = MotionEngine(AppConfig(smoothing_alpha=1.0, deadzone=0.01))
    engine.set_enabled(True)
    landmarks = hand(open_hand=True)
    engine.update(landmarks)
    assert engine.update(shifted(landmarks, dx=0.005)) is None

