from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field

from .geometry import Vec3


TEMPLATE_ID = "cstamp-c-arc"
TEMPLATE_VERSION = "1.0.0"


@dataclass(frozen=True)
class CTemplate:
    """Local C-shaped template. The opening gap is centered on the local
    +X axis; +X is the opening direction, +Z the plane normal, and the arc
    runs in the local XY plane. path_dir +1 keeps the start point at the
    upper lip (+Y side) of the opening."""

    radius: float = 10.0
    opening_deg: float = 60.0
    segments: int = 32
    template_id: str = TEMPLATE_ID
    version: str = TEMPLATE_VERSION
    extra: dict = field(default_factory=dict)

    def arc_angles(self) -> list[float]:
        half = math.radians(self.opening_deg) / 2.0
        start, end = half, 2.0 * math.pi - half
        return [
            start + (end - start) * i / self.segments
            for i in range(self.segments + 1)
        ]

    def local_points(self, path_dir: int = 1) -> list[Vec3]:
        points = [
            (self.radius * math.cos(a), self.radius * math.sin(a), 0.0)
            for a in self.arc_angles()
        ]
        if path_dir < 0:
            points.reverse()
        return points

    def definition(self) -> dict:
        return {
            "template_id": self.template_id,
            "version": self.version,
            "radius": self.radius,
            "opening_deg": self.opening_deg,
            "segments": self.segments,
            "extra": self.extra,
        }

    def sha256(self) -> str:
        canonical = json.dumps(
            self.definition(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
