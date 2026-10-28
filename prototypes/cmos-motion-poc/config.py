from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    camera_index: int = 0
    camera_backend: str = "dshow"
    camera_width: int = 1280
    camera_height: int = 720
    mirror: bool = True
    min_detection_confidence: float = 0.65
    min_tracking_confidence: float = 0.65
    smoothing_alpha: float = 0.35
    deadzone: float = 0.003
    rotate_gain: float = 1400.0
    pan_gain: float = 1000.0
    zoom_gain: float = 60.0
    max_motion_pixels: int = 80
    pinch_threshold: float = 0.055
    target_window_title: str = ""
    rotate_button: str = "left"
    pan_button: str = "middle"
    recognizer: str = "tasks"
    min_gesture_confidence: float = 0.65
    model_path: str = "models/hand_landmarker.task"
    allowed_target_exes: list = field(default_factory=list)
    input_timeout_s: float = 600.0
    output_mode: str = "preview"
    slicer_port: int = 18944
    # non-contact operation path (output_mode == "slicer")
    gesture_hold_s: float = 0.35
    arm_hold_s: float = 1.5
    thumb_ratio: float = 0.45
    aim_rate_hz: float = 25.0
    rotate_deadzone: float = 0.002
    rotate_deg_per_norm: float = 220.0
    pan_px_per_norm: float = 900.0
    zoom_ratio_per_norm: float = 1.6
    # discrete wheel tick -> smooth zoom ratio step (FR-022)
    wheel_zoom_ratio: float = 1.15
    opening_deg_per_norm: float = 400.0
    tilt_deg_per_norm: float = 400.0
    # Sustained recognition loss (seconds) required before a draft is
    # frozen; transient dropouts between gestures never freeze.
    loss_grace_s: float = 1.5
    zoom_deadzone: float = 0.02
    zoom_accel: float = 4.0
    zoom_max_velocity: float = 2.0
    zoom_min_ratio: float = 0.2
    zoom_max_ratio: float = 8.0
    zoom_release_tau: float = 0.08

    @classmethod
    def load(cls, path: Path | None) -> "AppConfig":
        values: dict[str, Any] = {}
        if path is not None:
            values = json.loads(path.read_text(encoding="utf-8"))
            known = {field.name for field in fields(cls)}
            unknown = sorted(set(values) - known)
            if unknown:
                raise ValueError(f"Unknown config keys: {', '.join(unknown)}")
        config = cls(**values)
        config.validate()
        return config

    def validate(self) -> None:
        defaults = type(self)()
        for item in fields(self):
            value, default = getattr(self, item.name), getattr(defaults, item.name)
            if isinstance(default, bool):
                valid = isinstance(value, bool)
            elif isinstance(default, int):
                valid = isinstance(value, int) and not isinstance(value, bool)
            elif isinstance(default, float):
                valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            elif isinstance(default, str):
                valid = isinstance(value, str)
            else:
                valid = isinstance(value, list) and all(isinstance(v, str) for v in value)
            if not valid:
                raise ValueError(f'{item.name} has an invalid type or nonfinite value')
        from zoom_engine import ZoomConfig
        ZoomConfig(deadzone=self.zoom_deadzone, accel=self.zoom_accel,
                   max_velocity=self.zoom_max_velocity, min_ratio=self.zoom_min_ratio,
                   max_ratio=self.zoom_max_ratio, release_tau=self.zoom_release_tau).validate()
        if not 0 < self.min_detection_confidence <= 1 or not 0 < self.min_tracking_confidence <= 1:
            raise ValueError('confidence thresholds must be in (0,1]')
        if self.camera_index < 0:
            raise ValueError("camera_index must be non-negative")
        if self.camera_width <= 0 or self.camera_height <= 0:
            raise ValueError("camera dimensions must be positive")
        if not 0.0 < self.smoothing_alpha <= 1.0:
            raise ValueError("smoothing_alpha must be in (0, 1]")
        if self.deadzone < 0.0:
            raise ValueError("deadzone must be non-negative")
        if self.max_motion_pixels <= 0:
            raise ValueError("max_motion_pixels must be positive")
        if self.pinch_threshold <= 0.0:
            raise ValueError("pinch_threshold must be positive")
        if self.rotate_button not in {"left", "middle", "right"}:
            raise ValueError("rotate_button must be left, middle, or right")
        if self.pan_button not in {"left", "middle", "right"}:
            raise ValueError("pan_button must be left, middle, or right")
        if self.recognizer not in {"tasks", "legacy", "standard"}:
            raise ValueError("recognizer must be tasks, legacy or standard")
        if not 0 <= self.min_gesture_confidence <= 1:
            raise ValueError('min_gesture_confidence must be between 0 and 1')
        if self.input_timeout_s <= 0.0:
            raise ValueError("input_timeout_s must be positive")
        if self.output_mode not in {"preview", "mouse", "slicer"}:
            raise ValueError("output_mode must be preview, mouse, or slicer")
        if not 1024 <= self.slicer_port <= 65535:
            raise ValueError("slicer_port must be 1024-65535")
        if self.gesture_hold_s <= 0.0:
            raise ValueError("gesture_hold_s must be positive")
        if self.arm_hold_s <= 0.0:
            raise ValueError("arm_hold_s must be positive")
        if self.thumb_ratio <= 0.0:
            raise ValueError("thumb_ratio must be positive")
        if self.aim_rate_hz <= 0.0:
            raise ValueError("aim_rate_hz must be positive")
        if self.rotate_deadzone < 0.0:
            raise ValueError("rotate_deadzone must be non-negative")
        if self.rotate_deg_per_norm <= 0.0:
            raise ValueError("rotate_deg_per_norm must be positive")
        if self.pan_px_per_norm <= 0.0:
            raise ValueError("pan_px_per_norm must be positive")
        if self.zoom_ratio_per_norm <= 0.0:
            raise ValueError("zoom_ratio_per_norm must be positive")
        if not 1.0 < self.wheel_zoom_ratio <= 2.0:
            raise ValueError("wheel_zoom_ratio must be in (1.0, 2.0]")
        if self.opening_deg_per_norm <= 0.0:
            raise ValueError("opening_deg_per_norm must be positive")
        if self.tilt_deg_per_norm <= 0.0:
            raise ValueError("tilt_deg_per_norm must be positive")
        if self.loss_grace_s < 0.0:
            raise ValueError("loss_grace_s must be non-negative")

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)

