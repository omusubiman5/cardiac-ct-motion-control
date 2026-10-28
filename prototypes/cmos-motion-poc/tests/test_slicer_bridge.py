import json
import socket
import threading
import time

import pytest

from motion_engine import Gesture, MotionAction
from slicer_bridge import SlicerCommandBridge


class _Server:
    """One-shot loopback TCP server collecting received lines."""

    def __init__(self):
        self.lines = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        conn, _ = self.sock.accept()
        buffer = b""
        conn.settimeout(0.2)
        while not self._stop.is_set():
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                self.lines.append(line.decode())
        conn.close()

    def wait_for(self, count: int, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while len(self.lines) < count and time.monotonic() < deadline:
            time.sleep(0.01)

    def close(self):
        self._stop.set()
        self.thread.join(timeout=2)
        self.sock.close()


def test_loopback_only():
    with pytest.raises(ValueError):
        SlicerCommandBridge(host="0.0.0.0")
    with pytest.raises(ValueError):
        SlicerCommandBridge(host="example.com")


def test_none_action_sends_nothing():
    bridge = SlicerCommandBridge(port=18945)  # nothing listening
    status = bridge.apply(None)
    assert not status.applied


def test_rotate_pan_zoom_payloads():
    server = _Server()
    try:
        bridge = SlicerCommandBridge(port=server.port)
        assert bridge.apply(
            MotionAction(Gesture.ROTATE, dx=10, dy=-4)
        ).applied
        assert bridge.apply(MotionAction(Gesture.PAN, dx=3, dy=5)).applied
        assert bridge.apply(MotionAction(Gesture.ZOOM, amount=2)).applied
        server.wait_for(3)
    finally:
        server.close()
    parsed = [json.loads(line) for line in server.lines]
    assert parsed[0] == {"cmd": "rotate", "dx": 2.5, "dy": -1.0}
    assert parsed[1] == {"cmd": "pan", "dx": 3.0, "dy": 5.0}
    assert parsed[2]["cmd"] == "zoom"
    assert parsed[2]["ratio"] == pytest.approx(1.02 ** 2)


def test_connection_refused_is_fail_closed():
    bridge = SlicerCommandBridge(port=18947, timeout=0.5)
    status = bridge.apply(MotionAction(Gesture.ROTATE, dx=5, dy=5))
    assert not status.applied
    assert "blocked" in status.message


def test_unsupported_gesture_inert():
    bridge = SlicerCommandBridge(port=18945)
    status = bridge.apply(MotionAction(Gesture.NONE))
    assert not status.applied
