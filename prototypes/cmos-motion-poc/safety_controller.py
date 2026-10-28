from __future__ import annotations

import time
import math
from dataclasses import dataclass
from enum import Enum
from typing import Callable


def fresh_frame(timestamp: float, now: float, max_age: float) -> bool:
    return math.isfinite(timestamp) and math.isfinite(now) and 0 <= now - timestamp <= max_age


class ControllerState(str, Enum):
    DISABLED = "disabled"
    READY = "ready"
    TRACKING = "tracking"
    EXECUTING = "executing"
    FAULT = "fault"


@dataclass(frozen=True)
class Observation:
    """One recognizer output. timestamp is the frame's monotonic time."""

    hand_count: int
    timestamp: float
    confidence: float
    intent_valid: bool


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    release: bool
    reason: str
    state: ControllerState


class SafetyController:
    """Fail-closed output gate (ADR-001).

    DISABLED -> arm -> READY -> TRACKING -> EXECUTING.
    Any of hand_count != 1, missing/stale observation, or an invalid
    intent drops to READY with release=True. FAULT requires a manual
    re-arm; camera reconnection alone never returns to EXECUTING.
    """

    def __init__(
        self,
        max_frame_age: float = 0.25,
        min_confidence: float = 0.5,
        stability_frames: int = 3,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_frame_age = max_frame_age
        self.min_confidence = min_confidence
        self.stability_frames = stability_frames
        self._now = now
        self.state = ControllerState.DISABLED
        self.fault_reason = ""
        self._stable = 0

    def arm(self) -> GateResult:
        if self.state in (
            ControllerState.DISABLED,
            ControllerState.FAULT,
        ):
            self.state = ControllerState.READY
            self._stable = 0
            self.fault_reason = ""
        return self._result(False, False, "armed; waiting for stable input")

    def disarm(self) -> GateResult:
        self.state = ControllerState.DISABLED
        self._stable = 0
        return self._result(False, True, "disabled")

    def fault(self, reason: str) -> GateResult:
        self.state = ControllerState.FAULT
        self.fault_reason = reason
        self._stable = 0
        return self._result(False, True, f"fault: {reason}")

    def update(self, obs: Observation | None) -> GateResult:
        if self.state is ControllerState.DISABLED:
            return self._result(False, False, "disabled")
        if self.state is ControllerState.FAULT:
            return self._result(False, False, f"fault: {self.fault_reason}")

        if obs is None:
            return self._degrade("no observation")
        if not fresh_frame(obs.timestamp, self._now(), self.max_frame_age):
            return self._degrade("stale frame")
        if obs.hand_count != 1:
            return self._degrade(f"hand_count={obs.hand_count}")
        if obs.confidence < self.min_confidence:
            return self._degrade("low confidence")
        if not obs.intent_valid:
            return self._degrade("intent ambiguous")

        if self.state is ControllerState.READY:
            self.state = ControllerState.TRACKING
            self._stable = 1
            return self._result(False, False, "tracking baseline")
        if self.state is ControllerState.TRACKING:
            self._stable += 1
            if self._stable >= self.stability_frames:
                self.state = ControllerState.EXECUTING
            return self._result(
                self.state is ControllerState.EXECUTING,
                False,
                self.state.value,
            )
        return self._result(True, False, "executing")

    def _degrade(self, reason: str) -> GateResult:
        """Recognition lost / ambiguous / multiple hands: release held
        input and drop to READY. Never auto-fault on transient loss."""
        if self.state in (
            ControllerState.TRACKING,
            ControllerState.EXECUTING,
        ):
            self.state = ControllerState.READY
            self._stable = 0
            return self._result(False, True, f"released: {reason}")
        self.state = ControllerState.READY
        self._stable = 0
        return self._result(False, False, f"waiting: {reason}")

    def _result(self, allowed: bool, release: bool, reason: str) -> GateResult:
        return GateResult(allowed, release, reason, self.state)
