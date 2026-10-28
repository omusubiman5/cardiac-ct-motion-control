from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from config import AppConfig


class Gesture(str, Enum):
    NONE = "none"
    ROTATE = "rotate"
    PAN = "pan"
    ZOOM = "zoom"


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class MotionAction:
    kind: Gesture
    dx: int = 0
    dy: int = 0
    amount: int = 0


TIP_AND_PIP = ((8, 6), (12, 10), (16, 14), (20, 18))
PALM_POINTS = (0, 5, 9, 13, 17)


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def classify_gesture(
    landmarks: Mapping[int, Point], pinch_threshold: float = 0.055
) -> Gesture:
    required = {0, 4, 5, 8, 6, 9, 12, 10, 13, 16, 14, 17, 20, 18}
    if not required.issubset(landmarks):
        return Gesture.NONE

    if _distance(landmarks[4], landmarks[8]) <= pinch_threshold:
        return Gesture.ZOOM

    extended = [landmarks[tip].y < landmarks[pip].y for tip, pip in TIP_AND_PIP]
    if all(extended):
        return Gesture.ROTATE
    if extended[0] and not any(extended[1:]):
        return Gesture.PAN
    return Gesture.NONE


def palm_center(landmarks: Mapping[int, Point]) -> Point | None:
    if not all(index in landmarks for index in PALM_POINTS):
        return None
    return Point(
        sum(landmarks[index].x for index in PALM_POINTS) / len(PALM_POINTS),
        sum(landmarks[index].y for index in PALM_POINTS) / len(PALM_POINTS),
    )


class MotionEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.enabled = False
        self.gesture = Gesture.NONE
        self._filtered: Point | None = None
        self._zoom_residual = 0.0

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.reset_tracking()

    def reset_tracking(self) -> None:
        self.gesture = Gesture.NONE
        self._filtered = None
        self._zoom_residual = 0.0

    def update(self, landmarks: Mapping[int, Point] | None) -> MotionAction | None:
        if not self.enabled or landmarks is None:
            self.reset_tracking()
            return None

        gesture = classify_gesture(landmarks, self.config.pinch_threshold)
        center = palm_center(landmarks)
        if gesture is Gesture.NONE or center is None:
            self.reset_tracking()
            return None

        if gesture is not self.gesture or self._filtered is None:
            self.gesture = gesture
            self._filtered = center
            self._zoom_residual = 0.0
            return None

        alpha = self.config.smoothing_alpha
        filtered = Point(
            alpha * center.x + (1.0 - alpha) * self._filtered.x,
            alpha * center.y + (1.0 - alpha) * self._filtered.y,
        )
        dx_norm = filtered.x - self._filtered.x
        dy_norm = filtered.y - self._filtered.y
        self._filtered = filtered

        dx_norm = 0.0 if abs(dx_norm) < self.config.deadzone else dx_norm
        dy_norm = 0.0 if abs(dy_norm) < self.config.deadzone else dy_norm

        limit = self.config.max_motion_pixels
        if gesture is Gesture.ROTATE:
            dx = _clamp_round(dx_norm * self.config.rotate_gain, limit)
            dy = _clamp_round(dy_norm * self.config.rotate_gain, limit)
            return None if dx == 0 and dy == 0 else MotionAction(gesture, dx=dx, dy=dy)

        if gesture is Gesture.PAN:
            dx = _clamp_round(dx_norm * self.config.pan_gain, limit)
            dy = _clamp_round(dy_norm * self.config.pan_gain, limit)
            return None if dx == 0 and dy == 0 else MotionAction(gesture, dx=dx, dy=dy)

        self._zoom_residual += -dy_norm * self.config.zoom_gain
        amount = math.trunc(self._zoom_residual)
        self._zoom_residual -= amount
        return None if amount == 0 else MotionAction(gesture, amount=amount)


def _clamp_round(value: float, limit: int) -> int:
    return max(-limit, min(limit, round(value)))

