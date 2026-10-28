from __future__ import annotations

import json
import socket
from dataclasses import dataclass

from motion_engine import Gesture, MotionAction


@dataclass(frozen=True)
class BridgeStatus:
    applied: bool
    message: str


class SlicerCommandBridge:
    """Sends typed view commands to the CStampModule loopback server
    (127.0.0.1). One JSON line per command; rotate/pan carry pixel deltas
    mapped to degrees, zoom carries a multiplicative ratio.

    Fail-closed: any transport error drops the connection and returns a
    non-applied status; the caller must treat that as 'no action'.
    """

    ROTATE_DEG_PER_PIXEL = 0.25
    PAN_SCALE = 1.0
    ZOOM_RATIO_PER_CLICK = 1.02

    def __init__(self, host: str = "127.0.0.1", port: int = 18944,
                 timeout: float = 1.0) -> None:
        if host != "127.0.0.1":
            raise ValueError("SlicerCommandBridge is loopback-only")
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: socket.socket | None = None

    def apply(self, action: MotionAction | None) -> BridgeStatus:
        if action is None:
            return BridgeStatus(False, "no motion")
        if action.kind is Gesture.ZOOM:
            if not action.amount:
                return BridgeStatus(False, "no motion")
            ratio = self.ZOOM_RATIO_PER_CLICK ** action.amount
            payload = {"cmd": "zoom", "ratio": round(ratio, 6)}
        elif action.kind is Gesture.ROTATE:
            payload = {
                "cmd": "rotate",
                "dx": action.dx * self.ROTATE_DEG_PER_PIXEL,
                "dy": action.dy * self.ROTATE_DEG_PER_PIXEL,
            }
        elif action.kind is Gesture.PAN:
            payload = {
                "cmd": "pan",
                "dx": action.dx * self.PAN_SCALE,
                "dy": action.dy * self.PAN_SCALE,
            }
        else:
            return BridgeStatus(False, f"unsupported action {action.kind}")
        try:
            self._send(payload)
        except OSError as error:
            self._close()
            return BridgeStatus(False, f"blocked: {error}")
        return BridgeStatus(True, f"sent: {payload['cmd']}")

    def release_all(self) -> None:
        return None  # loopback channel holds no pressed buttons

    def _send(self, payload: dict) -> None:
        if self._socket is None:
            self._socket = socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            )
        self._socket.sendall(
            (json.dumps(payload) + "\n").encode("utf-8")
        )

    def _close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None

    def close(self) -> None:
        self._close()
