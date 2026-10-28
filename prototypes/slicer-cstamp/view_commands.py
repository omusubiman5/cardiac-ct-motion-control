"""Typed view-command contract for the C-stamp / motion-control path.

The only commands that may reach the 3D view are ROTATE, PAN and ZOOM.
Everything else is rejected silently (fail-closed). No keyboard input,
no window switching, no arbitrary commands.

A command is a single JSON object per line:
    {"cmd": "rotate", "dx": 1.5, "dy": -0.5}   # degrees
    {"cmd": "pan",    "dx": 2.0, "dy": 1.0}    # pixels -> scene units
    {"cmd": "zoom",   "ratio": 1.02}           # multiplicative dolly
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum


class ViewCommandKind(str, Enum):
    ROTATE = "rotate"
    PAN = "pan"
    ZOOM = "zoom"


@dataclass(frozen=True)
class ViewCommand:
    kind: ViewCommandKind
    dx: float = 0.0
    dy: float = 0.0
    ratio: float = 1.0


MAX_DELTA = 45.0          # degrees or pixels per command
MIN_ZOOM_RATIO = 0.5
MAX_ZOOM_RATIO = 2.0


def parse_command(line: str | bytes) -> ViewCommand | None:
    """Parse one JSON line. Returns None for anything that is not a
    well-formed ROTATE/PAN/ZOOM command — invalid input is inert."""
    try:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if len(line) > 4096:
            return None
        data = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    cmd = data.get("cmd")
    if cmd == ViewCommandKind.ROTATE.value or cmd == ViewCommandKind.PAN.value:
        dx = _finite_number(data.get("dx"))
        dy = _finite_number(data.get("dy"))
        if dx is None or dy is None:
            return None
        # Clamp rather than reject: a fast gesture frame would otherwise
        # lose its entire motion, which feels like the input is ignored.
        dx = max(-MAX_DELTA, min(MAX_DELTA, dx))
        dy = max(-MAX_DELTA, min(MAX_DELTA, dy))
        return ViewCommand(ViewCommandKind(cmd), dx=dx, dy=dy)

    if cmd == ViewCommandKind.ZOOM.value:
        ratio = _finite_number(data.get("ratio"))
        if ratio is None:
            return None
        if not MIN_ZOOM_RATIO <= ratio <= MAX_ZOOM_RATIO:
            return None
        return ViewCommand(ViewCommandKind.ZOOM, ratio=ratio)

    return None


def _finite_number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def apply_to_camera(camera, command: ViewCommand) -> None:
    """Apply a validated command to a vtkCamera in place."""
    if command.kind is ViewCommandKind.ROTATE:
        if command.dx:
            camera.Azimuth(-command.dx)
        if command.dy:
            camera.Elevation(command.dy)
        camera.OrthogonalizeViewUp()
    elif command.kind is ViewCommandKind.PAN:
        _pan_camera(camera, command.dx, command.dy)
    elif command.kind is ViewCommandKind.ZOOM:
        if command.ratio != 1.0:
            camera.Dolly(command.ratio)


def _pan_camera(camera, dx_pixels: float, dy_pixels: float) -> None:
    """Translate camera position and focal point in the view plane."""
    # Approximate scene scale from camera distance; a real viewer should
    # scale by renderer height, but pan magnitude is capped upstream.
    distance = camera.GetDistance() or 1.0
    scale = distance * 0.002
    pos = list(camera.GetPosition())
    focal = list(camera.GetFocalPoint())
    view_up = camera.GetViewUp()
    # camera frame: forward = focal - position
    forward = _normalize([f - p for f, p in zip(focal, pos)])
    right = _normalize(_cross(forward, view_up))
    up = _normalize(_cross(right, forward))
    offset = [
        -dx_pixels * scale * right[i] - dy_pixels * scale * up[i]
        for i in range(3)
    ]
    camera.SetPosition(*[p + o for p, o in zip(pos, offset)])
    camera.SetFocalPoint(*[f + o for f, o in zip(focal, offset)])


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize(v):
    norm = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return [c / norm for c in v]
