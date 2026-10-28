"""Local MediaPipe canned gesture adapter; does not dispatch operations."""
from dataclasses import dataclass
from motion_engine import Point
from motion_engine import classify_gesture, Gesture
from gesture_fsm import classify_shape, extended_fingers, thumb_geometry, Shape
import math


@dataclass(frozen=True)
class StandardObservation:
    hand_count: int
    landmarks: dict | None
    image_landmarks_3d: tuple
    world_landmarks: tuple
    category: str
    gesture_score: float
    handedness: str
    handedness_score: float
    timestamp: float

    @property
    def confidence(self):
        # Compatibility with the existing per-frame gate, not gesture confidence.
        return self.handedness_score


def operation_shape(obs, *, image_aspect=1., pinch_threshold=.055,
                    thumb_ratio=.45, min_gesture_score=.65):
    """Keep view gestures; only the standard model may assert fist/thumb."""
    if obs.hand_count != 1 or obs.landmarks is None:
        return Shape.NONE
    if not all(math.isfinite(p.x) and math.isfinite(p.y) for p in obs.landmarks.values()):
        return Shape.UNKNOWN
    accepted = math.isfinite(obs.gesture_score) and obs.gesture_score >= min_gesture_score
    if obs.category in {'Closed_Fist', 'Thumb_Up', 'Thumb_Down'}:
        if accepted:
            if obs.category == 'Thumb_Down':
                return Shape.THUMB_DOWN
            return Shape.FIST if obs.category == 'Closed_Fist' else Shape.THUMB
        # Marginal model score: verify the pose with deterministic
        # landmark geometry instead of trusting the softmax. Anything
        # ambiguous still fails closed to UNKNOWN.
        geo = classify_shape(obs.landmarks, pinch_threshold, thumb_ratio,
                             image_aspect=image_aspect)
        if obs.category == 'Closed_Fist':
            return Shape.FIST if geo is Shape.FIST else Shape.UNKNOWN
        tg = thumb_geometry(obs.landmarks, image_aspect=image_aspect)
        thumb_straight = (tg is not None and tg['angle_deg'] >= 145.0
                          and tg['length_ratio'] > thumb_ratio
                          and tg['outside_ratio'] >= 0.6)
        ext = extended_fingers(obs.landmarks, image_aspect=image_aspect)
        # The model's top label already chooses up vs down; geometry only
        # confirms the pose. An open palm also extends the thumb, so the
        # thumb-only fallback additionally requires all fingers curled.
        if obs.category == 'Thumb_Up':
            if (geo is Shape.THUMB
                    or (ext == [False, False, False, False]
                        and thumb_straight and tg['forward_ratio'] > -0.35)):
                return Shape.THUMB
            return Shape.UNKNOWN
        # Thumb_Down cancels the provisional C with no further confirm, so
        # all four fingers must be unambiguously curled (an ambiguous
        # finger state or an open palm can never rescue a cancel).
        if (ext == [False, False, False, False] and thumb_straight
                and tg['forward_ratio'] <= -0.35):
            return Shape.THUMB_DOWN
        return Shape.UNKNOWN
    if obs.category in {'ILoveYou', 'Victory'}:
        if accepted:
            return Shape.ILOVEYOU if obs.category == 'ILoveYou' else Shape.TWO
        # Marginal model score: deterministic finger-pattern check.
        ext = extended_fingers(obs.landmarks, image_aspect=image_aspect)
        if obs.category == 'Victory':
            return Shape.TWO if ext == [True, True, False, False] else Shape.UNKNOWN
        # MediaPipe ILoveYou includes the extended thumb; a horns-only
        # pose (index+pinky, thumb folded) must not arm or resume.
        tg_ily = thumb_geometry(obs.landmarks, image_aspect=image_aspect)
        thumb_out = (tg_ily is not None and tg_ily['length_ratio'] > thumb_ratio
                     and tg_ily['outside_ratio'] >= 0.6)
        if ext == [True, False, False, True] and thumb_out:
            return Shape.ILOVEYOU
        return Shape.UNKNOWN
    continuous = classify_gesture(obs.landmarks, pinch_threshold)
    if continuous is not Gesture.NONE:
        return {Gesture.ROTATE:Shape.OPEN_PALM, Gesture.PAN:Shape.POINT,
                Gesture.ZOOM:Shape.PINCH}[continuous]
    shape = classify_shape(obs.landmarks, pinch_threshold, thumb_ratio,
                           image_aspect=image_aspect)
    return shape if shape in {Shape.TWO, Shape.THREE} else Shape.UNKNOWN


def decode_result(result, timestamp):
    count = len(result.hand_landmarks)
    if count != 1:
        return StandardObservation(count, None, (), (), 'No_Hand' if count == 0 else 'Multiple_Hands', 0., '', 0., timestamp)
    landmarks = result.hand_landmarks[0]
    gestures = result.gestures[0] if result.gestures else []
    category = max(gestures, key=lambda c: c.score) if gestures else None
    hands = result.handedness[0] if result.handedness else []
    handedness = max(hands, key=lambda c: c.score) if hands else None
    world = result.hand_world_landmarks[0] if result.hand_world_landmarks else []
    return StandardObservation(
        count, {i: Point(p.x, p.y) for i,p in enumerate(landmarks)},
        tuple((p.x,p.y,p.z) for p in landmarks),
        tuple((p.x,p.y,p.z) for p in world),
        category.category_name if category else 'None',
        float(category.score) if category else 0.,
        handedness.category_name if handedness else '',
        float(handedness.score) if handedness else 0., timestamp)


class StandardGestureRecognizer:
    def __init__(self, model_path, min_detection_confidence=.65, min_tracking_confidence=.65):
        import mediapipe as mp
        self.mp = mp
        self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(
            mp.tasks.vision.GestureRecognizerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=2,
                min_hand_detection_confidence=min_detection_confidence,
                min_hand_presence_confidence=.5,
                min_tracking_confidence=min_tracking_confidence))

    def recognize(self, rgb, timestamp):
        result = self.recognizer.recognize_for_video(
            self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb),
            int(timestamp * 1000))
        return decode_result(result, timestamp)

    def close(self):
        self.recognizer.close()
