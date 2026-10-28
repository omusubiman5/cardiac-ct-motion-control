"""Hand-shape classification and discrete/hold gesture detection.

Deterministic shape classes (no learned classifier, ADR-002 contract):
OPEN_PALM, POINT (index only), TWO, THREE, FIST, THUMB (thumb only),
PINCH, UNKNOWN. Ambiguous landmarks always yield UNKNOWN which produces
no action (SR-001/SR-002).

``GestureLatch`` turns a stable shape into exactly one discrete edge
event; a new edge requires a release (NONE/UNKNOWN/other shape) first,
so holding a gesture never fires twice (OP-003/SR-010).

``HoldDetector`` measures how long one shape has been held and fires
once per hold — used for the dedicated arm path that must work while
the system is still disarmed.
"""

from __future__ import annotations

import math
import time
from enum import Enum
from typing import Callable, Mapping

from motion_engine import Point


class Shape(str, Enum):
    NONE = "none"
    OPEN_PALM = "open_palm"
    ILOVEYOU = "iloveyou"  # standard-model-only dedicated start
    POINT = "point"        # index finger only
    TWO = "two"            # index + middle
    THREE = "three"        # index + middle + ring
    FIST = "fist"          # all fingers folded
    THUMB = "thumb"        # thumb only, fingers folded
    THUMB_DOWN = "thumb_down"  # standard classifier; menu back only
    PINCH = "pinch"        # thumb tip touches index tip
    UNKNOWN = "unknown"


FINGERS = ((8, 6), (12, 10), (16, 14), (20, 18))  # index..pinky tip/pip
_PALM_WIDTH_POINTS = (5, 17)                     # index mcp, pinky mcp


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _metric_landmarks(landmarks, image_aspect):
    """Convert geometry to image-height units; leave control coordinates intact."""
    if not math.isfinite(image_aspect) or image_aspect <= 0:
        raise ValueError('image_aspect must be finite and positive')
    return {i: Point(p.x * image_aspect, p.y) for i, p in landmarks.items()}


def thumb_geometry(landmarks, *, image_aspect=1.0):
    """Normalize thumb joint extension and palm separation by hand size."""
    required = {0, 2, 3, 4, 5, 9, 13, 17}
    if landmarks is None or not required.issubset(landmarks):
        return None
    landmarks = _metric_landmarks(landmarks, image_aspect)
    if not all(math.isfinite(landmarks[i].x) and math.isfinite(landmarks[i].y)
               for i in required):
        return None
    width = _distance(landmarks[5], landmarks[17])
    a, joint, tip = landmarks[2], landmarks[3], landmarks[4]
    u = (a.x - joint.x, a.y - joint.y)
    v = (tip.x - joint.x, tip.y - joint.y)
    lengths = math.hypot(*u) * math.hypot(*v)
    if width <= 1e-6 or lengths <= 1e-8:
        return None
    cosine = max(-1.0, min(1.0, (u[0]*v[0] + u[1]*v[1]) / lengths))
    center = Point(sum(landmarks[i].x for i in (5, 9, 13, 17))/4,
                   sum(landmarks[i].y for i in (5, 9, 13, 17))/4)
    axis = (center.x - landmarks[0].x, center.y - landmarks[0].y)
    axis_length = math.hypot(*axis)
    if axis_length <= 1e-6:
        return None
    forward = ((tip.x-center.x)*axis[0] + (tip.y-center.y)*axis[1]) / axis_length / width
    return {'angle_deg': math.degrees(math.acos(cosine)),
            'length_ratio': _distance(tip, a)/width,
            'outside_ratio': _distance(tip, center)/width,
            'forward_ratio': forward}


def extended_fingers(landmarks, *, image_aspect=1.0):
    """Boolean per-finger extension (index..pinky), same rule as classify_shape.
    Returns None when the landmarks are incomplete or degenerate."""
    required = {tip for tip, _ in FINGERS} | {pip for _, pip in FINGERS} | {tip - 3 for tip, _ in FINGERS}
    if landmarks is None or not required.issubset(landmarks):
        return None
    m = _metric_landmarks(landmarks, image_aspect)
    if any(_distance(m[pip], m[tip - 3]) <= 1e-6 for tip, pip in FINGERS):
        return None
    return [
        ((m[tip].x - m[pip].x) * (m[pip].x - m[tip - 3].x) +
         (m[tip].y - m[pip].y) * (m[pip].y - m[tip - 3].y)) > 0
        for tip, pip in FINGERS
    ]


def classify_shape(
    landmarks: Mapping[int, Point] | None,
    pinch_threshold: float = 0.055,
    thumb_ratio: float = 0.45,
    *,
    image_aspect: float = 1.0,
) -> Shape:
    """Classify a 21-landmark hand into a deterministic Shape.

    thumb_ratio is the minimum MCP-tip length relative to palm width.
    THUMB also needs a straight IP joint and a tip outside the folded
    knuckles. A long bent thumb does not qualify as THUMB.
    Each finger's MCP->PIP axis is used instead of screen vertical."""
    required = {0, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20}
    if landmarks is None or not required.issubset(landmarks):
        return Shape.NONE

    if not all(math.isfinite(p.x) and math.isfinite(p.y) for p in landmarks.values()):
        return Shape.UNKNOWN
    # Keep the existing normalized contact threshold for pinch compatibility.
    pinch_contact = _distance(landmarks[4], landmarks[8]) <= pinch_threshold
    landmarks = _metric_landmarks(landmarks, image_aspect)
    center = Point(sum(landmarks[i].x for i in (5, 9, 13, 17))/4,
                   sum(landmarks[i].y for i in (5, 9, 13, 17))/4)
    axis = (center.x-landmarks[0].x, center.y-landmarks[0].y)
    if math.hypot(*axis) <= 1e-6:
        return Shape.UNKNOWN
    extended = [
        ((landmarks[tip].x-landmarks[pip].x)*(landmarks[pip].x-landmarks[tip-3].x) +
         (landmarks[tip].y-landmarks[pip].y)*(landmarks[pip].y-landmarks[tip-3].y)) > 0
        for tip, pip in FINGERS
    ]
    if any(_distance(landmarks[pip], landmarks[tip-3]) <= 1e-6 for tip,pip in FINGERS):
        return Shape.UNKNOWN
    # A closed fist can bring both tips close together. Pinch additionally
    # needs the index tip beyond its knuckle; an enclosed folded tip is inert.
    index_forward = ((landmarks[8].x-landmarks[5].x)*axis[0] +
                     (landmarks[8].y-landmarks[5].y)*axis[1]) > 0
    if pinch_contact and index_forward and (extended[0] or any(extended[1:])):
        return Shape.PINCH
    if pinch_contact and index_forward:
        return Shape.UNKNOWN  # folded pinch vs fist is ambiguous: never cancel
    geometry = thumb_geometry(landmarks)
    thumb_out = (geometry is not None and geometry['angle_deg'] >= 145.0
                 and geometry['length_ratio'] > thumb_ratio
                 and geometry['outside_ratio'] >= 0.75
                 and geometry['forward_ratio'] >= 0.35)
    count = sum(extended)

    if count == 4:
        return Shape.OPEN_PALM
    if count == 0:
        if geometry is None:
            return Shape.UNKNOWN
        if (geometry['forward_ratio'] <= 0.15
                and geometry['outside_ratio'] <= 1.10):
            # A thumb resting on the side of curled fingers can appear
            # straight and long. It has not risen beyond the knuckles.
            return Shape.FIST
        if (not thumb_out and geometry['angle_deg'] > 120.0
                and geometry['outside_ratio'] > 0.60
                and geometry['length_ratio'] > thumb_ratio):
            # Between a closed thumb and a clearly extended thumb: do
            # not invent FIST, which could cancel a draft outside menus.
            return Shape.UNKNOWN
        return Shape.THUMB if thumb_out else Shape.FIST
    if extended[0] and not any(extended[1:]):
        return Shape.POINT
    if extended[0] and extended[1] and not any(extended[2:]):
        return Shape.TWO
    if extended[0] and extended[1] and extended[2] and not extended[3]:
        return Shape.THREE
    return Shape.UNKNOWN


class GestureLatch:
    """Edge detector: emits ``shape`` once when a discrete shape has
    been stable for ``hold_s`` seconds; rearms after a release lasting
    ``hold_s`` or a different discrete shape held stably. A dropped
    recognition frame never rearms the same held shape."""

    def __init__(
        self,
        hold_s: float = 0.35,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.hold_s = hold_s
        self._now = now
        self._candidate: Shape = Shape.NONE
        self._candidate_since = 0.0
        self._latched: Shape | None = None
        self._release_since: float | None = None

    def reset(self) -> None:
        self._candidate = Shape.NONE
        self._latched = None
        self._release_since = None

    def update(self, shape: Shape) -> Shape | None:
        """Returns the fired shape once, else None."""
        now = self._now()
        discrete = shape not in (
            Shape.NONE, Shape.UNKNOWN, Shape.OPEN_PALM, Shape.POINT,
            Shape.PINCH,
        )
        if not discrete:
            self._candidate = Shape.NONE
            # Brief recognition losses are not independent releases.
            if self._release_since is None:
                self._release_since = now
            if now - self._release_since >= self.hold_s:
                self._latched = None
            return None
        if self._release_since is not None:
            if now - self._release_since >= self.hold_s:
                self._latched = None
            self._release_since = None
        if shape == self._latched:
            return None
        if shape != self._candidate:
            self._candidate = shape
            self._candidate_since = now
            return None
        if now - self._candidate_since >= self.hold_s:
            self._latched = shape
            return shape
        return None


class HoldDetector:
    """Fires once when ``target`` is held continuously for ``hold_s``.
    Resets as soon as the shape leaves the target. ``armed`` in
    update() suppresses firing while the system is already armed —
    the same shape may then be used for continuous work."""

    def __init__(
        self,
        target: Shape,
        hold_s: float,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.target = target
        self.hold_s = hold_s
        self._now = now
        self._since: float | None = None
        self._fired = False

    def reset(self) -> None:
        self._since = None
        self._fired = False

    @property
    def elapsed_s(self) -> float:
        """Read-only progress; querying never starts or completes a hold."""
        if self._since is None:
            return 0.0
        return min(self.hold_s, max(0.0, self._now() - self._since))

    def update(self, shape: Shape, armed: bool) -> bool:
        """True exactly once per completed hold."""
        if armed or shape is not self.target:
            self._since = None
            self._fired = False
            return False
        now = self._now()
        if self._since is None:
            self._since = now
            return False
        if self._fired:
            return False
        if now - self._since >= self.hold_s:
            self._fired = True
            return True
        return False
