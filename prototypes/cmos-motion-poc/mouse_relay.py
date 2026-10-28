from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Protocol

from config import AppConfig
from motion_engine import Gesture, MotionAction


INPUT_MOUSE = 0
WHEEL_DELTA = 120

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800

_BUTTON_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
}


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    )


class _INPUTUNION(ctypes.Union):
    _fields_ = (("mi", _MOUSEINPUT),)


class _INPUT(ctypes.Structure):
    _anonymous_ = ("value",)
    _fields_ = (("type", wintypes.DWORD), ("value", _INPUTUNION))


@dataclass(frozen=True)
class RelayStatus:
    applied: bool
    message: str


class MouseTransport(Protocol):
    def move_relative(self, dx: int, dy: int) -> None: ...

    def button_down(self, button: str) -> None: ...

    def button_up(self, button: str) -> None: ...

    def wheel(self, clicks: int) -> None: ...


TargetGuard = Callable[[], tuple[bool, str]]


class PreviewMouseRelay:
    def apply(self, action: MotionAction | None) -> RelayStatus:
        if action is None:
            return RelayStatus(False, "preview: no mouse motion")
        if action.kind is Gesture.ZOOM:
            return RelayStatus(False, f"preview: wheel {action.amount:+d}")
        return RelayStatus(
            False,
            f"preview: {action.kind.value} drag {action.dx:+d},{action.dy:+d}",
        )

    def release_all(self) -> None:
        return None


class WindowsMouseRelay:
    """Relays approved motion actions to mouse-only Windows SendInput events."""

    def __init__(
        self,
        config: AppConfig,
        target_guard: TargetGuard,
        transport: MouseTransport | None = None,
    ) -> None:
        self.config = config
        self.target_guard = target_guard
        self.transport = transport or SendInputMouseTransport()
        self._held_button: str | None = None

    def apply(self, action: MotionAction | None) -> RelayStatus:
        allowed, reason = self.target_guard()
        if not allowed:
            self.release_all()
            return RelayStatus(False, f"blocked: {reason}")

        if action is None:
            self.release_all()
            return RelayStatus(False, "target ready: no mouse motion")

        try:
            if action.kind is Gesture.ZOOM:
                self.release_all()
                if action.amount:
                    self.transport.wheel(action.amount)
                return RelayStatus(True, f"applied: wheel {action.amount:+d}")

            if action.kind not in {Gesture.ROTATE, Gesture.PAN}:
                self.release_all()
                return RelayStatus(False, f"blocked: unsupported action {action.kind}")

            button = (
                self.config.rotate_button
                if action.kind is Gesture.ROTATE
                else self.config.pan_button
            )
            self._hold(button)
            self.transport.move_relative(action.dx, action.dy)
            return RelayStatus(
                True,
                f"applied: {action.kind.value} drag {action.dx:+d},{action.dy:+d}",
            )
        except Exception:
            self.release_all()
            raise

    def _hold(self, button: str) -> None:
        if button not in _BUTTON_FLAGS:
            raise ValueError(f"Unsupported mouse button: {button}")
        if self._held_button == button:
            return
        self.release_all()
        self.transport.button_down(button)
        self._held_button = button

    def release_all(self) -> None:
        if self._held_button is None:
            return
        button = self._held_button
        self._held_button = None
        self.transport.button_up(button)


class SendInputMouseTransport:
    """Mouse-only Win32 transport. It has no keyboard or hotkey API."""

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._send_input = self._user32.SendInput
        self._send_input.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(_INPUT),
            ctypes.c_int,
        )
        self._send_input.restype = wintypes.UINT

    def move_relative(self, dx: int, dy: int) -> None:
        self._send(MOUSEEVENTF_MOVE, dx=dx, dy=dy)

    def button_down(self, button: str) -> None:
        self._send(_BUTTON_FLAGS[button][0])

    def button_up(self, button: str) -> None:
        self._send(_BUTTON_FLAGS[button][1])

    def wheel(self, clicks: int) -> None:
        self._send(MOUSEEVENTF_WHEEL, mouse_data=clicks * WHEEL_DELTA)

    def _send(
        self,
        flags: int,
        *,
        dx: int = 0,
        dy: int = 0,
        mouse_data: int = 0,
    ) -> None:
        event = _INPUT(
            type=INPUT_MOUSE,
            mi=_MOUSEINPUT(
                dx=dx,
                dy=dy,
                mouseData=mouse_data & 0xFFFFFFFF,
                dwFlags=flags,
                time=0,
                dwExtraInfo=0,
            ),
        )
        sent = self._send_input(1, ctypes.byref(event), ctypes.sizeof(_INPUT))
        if sent != 1:
            error = ctypes.get_last_error()
            raise OSError(error, "SendInput failed for mouse event")
