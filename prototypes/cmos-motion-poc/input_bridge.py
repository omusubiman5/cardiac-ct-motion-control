from __future__ import annotations

import ctypes
from dataclasses import dataclass

from config import AppConfig
from motion_engine import Gesture, MotionAction


@dataclass(frozen=True)
class BridgeStatus:
    applied: bool
    message: str


class PreviewBridge:
    def apply(self, action: MotionAction | None) -> BridgeStatus:
        if action is None:
            return BridgeStatus(False, "preview: no motion")
        if action.kind is Gesture.ZOOM:
            return BridgeStatus(False, f"preview: zoom {action.amount:+d}")
        return BridgeStatus(False, f"preview: {action.kind.value} {action.dx:+d},{action.dy:+d}")

    def release_all(self) -> None:
        return None


class WindowsInputBridge:
    def __init__(self, config: AppConfig) -> None:
        if not config.target_window_title.strip():
            raise ValueError("target_window_title is required with --enable-input")
        import pyautogui

        self.config = config
        self.pyautogui = pyautogui
        self.pyautogui.PAUSE = 0
        self._held_button: str | None = None

    def apply(self, action: MotionAction | None) -> BridgeStatus:
        title = foreground_window_title()
        if self.config.target_window_title.casefold() not in title.casefold():
            self.release_all()
            return BridgeStatus(False, f"blocked: foreground is '{title or 'unknown'}'")

        if action is None:
            self.release_all()
            return BridgeStatus(False, "target ready: no motion")

        if action.kind is Gesture.ZOOM:
            self.release_all()
            if action.amount:
                self.pyautogui.scroll(action.amount, _pause=False)
            return BridgeStatus(True, f"applied: zoom {action.amount:+d}")

        button = (
            self.config.rotate_button
            if action.kind is Gesture.ROTATE
            else self.config.pan_button
        )
        self._hold(button)
        self.pyautogui.moveRel(action.dx, action.dy, duration=0, _pause=False)
        return BridgeStatus(True, f"applied: {action.kind.value} {action.dx:+d},{action.dy:+d}")

    def _hold(self, button: str) -> None:
        if self._held_button == button:
            return
        self.release_all()
        self.pyautogui.mouseDown(button=button, _pause=False)
        self._held_button = button

    def release_all(self) -> None:
        if self._held_button is not None:
            self.pyautogui.mouseUp(button=self._held_button, _pause=False)
            self._held_button = None


def foreground_window_title() -> str:
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value

