from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Protocol


class TargetApi(Protocol):
    def foreground_hwnd(self) -> int: ...

    def process_id_of(self, hwnd: int) -> int: ...

    def image_path_of(self, pid: int) -> str: ...

    def window_class_of(self, hwnd: int) -> str: ...


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


class StrictTargetGuard:
    """Approves output only when the foreground window belongs to an
    allowed executable (SR-006 / R-004). A window title substring is
    never accepted."""

    def __init__(
        self,
        allowed_exe_paths: set[str],
        api: TargetApi | None = None,
    ) -> None:
        self.allowed = {_norm(p) for p in allowed_exe_paths}
        self.api = api or Win32TargetApi()

    def check(self) -> tuple[bool, str]:
        hwnd = self.api.foreground_hwnd()
        if not hwnd:
            return False, "no foreground window"
        pid = self.api.process_id_of(hwnd)
        if not pid:
            return False, "foreground process unknown"
        image = self.api.image_path_of(pid)
        if not image:
            return False, "foreground image unknown"
        if _norm(image) in self.allowed:
            return True, f"target matched: {os.path.basename(image)}"
        return False, f"foreground is not an allowed target: {image}"


class Win32TargetApi:
    """Win32 implementation: foreground HWND -> PID -> image path."""

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def __init__(self) -> None:
        self._u32 = ctypes.WinDLL("user32", use_last_error=True)
        self._k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._u32.GetWindowThreadProcessId.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        )
        self._u32.GetClassNameW.argtypes = (
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        )
        self._k32.QueryFullProcessImageNameW.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        )

    def foreground_hwnd(self) -> int:
        return int(self._u32.GetForegroundWindow() or 0)

    def process_id_of(self, hwnd: int) -> int:
        pid = wintypes.DWORD(0)
        self._u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)

    def image_path_of(self, pid: int) -> str:
        handle = self._k32.OpenProcess(
            self.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buffer))
            if self._k32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                return buffer.value
            return ""
        finally:
            self._k32.CloseHandle(handle)

    def window_class_of(self, hwnd: int) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        self._u32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value
