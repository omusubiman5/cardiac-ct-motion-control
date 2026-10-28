from __future__ import annotations

import time
from dataclasses import dataclass

from motion_engine import Point


@dataclass(frozen=True)
class HandObservation:
    hand_count: int
    landmarks: dict[int, Point] | None
    confidence: float
    timestamp: float


class TasksHandRecognizer:
    """MediaPipe Tasks Hand Landmarker in synchronous VIDEO mode
    (ADR-002). The model asset must be a pinned local file; it is never
    downloaded at runtime.
    """

    def __init__(
        self,
        model_path: str,
        num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        import mediapipe as mp  # noqa: PLC0415

        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(
            options
        )
        self._mp = mp

    def recognize(self, frame_rgb, timestamp: float) -> HandObservation:
        """Returns the observation for one RGB frame. landmarks is the
        21-point map of the single detected hand, or None."""
        image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB, data=frame_rgb
        )
        result = self._landmarker.detect_for_video(
            image, int(timestamp * 1000.0)
        )
        count = len(result.hand_landmarks or [])
        if count != 1:
            return HandObservation(count, None, 0.0, timestamp)
        confidence = (
            result.handedness[0][0].score
            if result.handedness and result.handedness[0]
            else 0.0
        )
        landmarks = {
            index: Point(lm.x, lm.y)
            for index, lm in enumerate(result.hand_landmarks[0])
        }
        return HandObservation(count, landmarks, confidence, timestamp)

    def close(self) -> None:
        self._landmarker.close()


class LegacyHandRecognizer:
    """Deprecated mp.solutions.hands adapter kept only for environments
    where the pinned Tasks model asset is not yet installed. Same
    HandObservation contract as TasksHandRecognizer."""

    def __init__(
        self,
        num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        import mediapipe as mp  # noqa: PLC0415

        self._mp = mp
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=num_hands,
            model_complexity=0,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def recognize(self, frame_rgb, timestamp: float) -> HandObservation:
        result = self._hands.process(frame_rgb)
        count = len(result.multi_hand_landmarks or [])
        if count != 1:
            return HandObservation(count, None, 0.0, timestamp)
        confidence = 0.0
        if result.multi_handedness:
            classification = result.multi_handedness[0].classification
            if classification:
                confidence = float(classification[0].score)
        landmarks = {
            index: Point(lm.x, lm.y)
            for index, lm in enumerate(result.multi_hand_landmarks[0].landmark)
        }
        return HandObservation(count, landmarks, confidence, timestamp)

    def close(self) -> None:
        self._hands.close()
