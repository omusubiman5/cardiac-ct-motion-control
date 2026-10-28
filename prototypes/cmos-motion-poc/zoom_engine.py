from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ZoomConfig:
    deadzone: float = 0.02
    accel: float = 4.0          # ratio velocity per unit strength per second
    max_velocity: float = 2.0   # max ratio change per second
    min_ratio: float = 0.2
    max_ratio: float = 8.0
    release_tau: float = 0.08   # seconds; velocity decay on release

    def validate(self) -> None:
        if self.deadzone < 0.0:
            raise ValueError("deadzone must be non-negative")
        if self.accel <= 0.0 or self.max_velocity <= 0.0:
            raise ValueError("accel and max_velocity must be positive")
        if not 0.0 < self.min_ratio < 1.0 < self.max_ratio:
            raise ValueError("min_ratio must be <1 and max_ratio >1")
        if self.release_tau <= 0.0:
            raise ValueError("release_tau must be positive")


@dataclass(frozen=True)
class ZoomState:
    ratio: float
    velocity: float


class SmoothZoom:
    """Continuous SMOOTH_ZOOM command (FR-016..FR-023).

    strength: -1..+1 continuous input (positive = zoom in). A deadzone,
    acceleration cap, velocity cap and min/max ratio are applied. On
    release (strength=None) the velocity decays to zero and the camera
    never drifts on its own.
    """

    def __init__(self, config: ZoomConfig | None = None) -> None:
        self.config = config or ZoomConfig()
        self.config.validate()
        self.ratio = 1.0
        self.velocity = 0.0

    def update(self, strength: float | None, dt: float) -> ZoomState:
        dt = max(dt, 0.0)
        if strength is None:
            # released or recognition lost: decay to full stop
            decay = min(dt / self.config.release_tau, 1.0)
            self.velocity -= self.velocity * decay
            if abs(self.velocity) < 1e-4:
                self.velocity = 0.0
        else:
            s = max(-1.0, min(1.0, strength))
            if abs(s) < self.config.deadzone:
                s = 0.0
            target = s * self.config.max_velocity
            step = self.config.accel * self.config.max_velocity * dt
            # approach target velocity; never overshoot the cap
            delta = target - self.velocity
            if abs(delta) <= step:
                self.velocity = target
            else:
                self.velocity += step if delta > 0 else -step

        new_ratio = self.ratio + self.velocity * dt
        if new_ratio <= self.config.min_ratio:
            new_ratio = self.config.min_ratio
            self.velocity = max(self.velocity, 0.0)
        elif new_ratio >= self.config.max_ratio:
            new_ratio = self.config.max_ratio
            self.velocity = min(self.velocity, 0.0)
        self.ratio = new_ratio
        return ZoomState(self.ratio, self.velocity)
