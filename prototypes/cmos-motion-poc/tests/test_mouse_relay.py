from config import AppConfig
from motion_engine import Gesture, MotionAction
from mouse_relay import PreviewMouseRelay, WindowsMouseRelay


class FakeMouseTransport:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def move_relative(self, dx: int, dy: int) -> None:
        self.events.append(("move", dx, dy))

    def button_down(self, button: str) -> None:
        self.events.append(("down", button))

    def button_up(self, button: str) -> None:
        self.events.append(("up", button))

    def wheel(self, clicks: int) -> None:
        self.events.append(("wheel", clicks))


def allow_target() -> tuple[bool, str]:
    return True, "target matched"


def test_rotate_is_mouse_drag_and_none_releases_button() -> None:
    transport = FakeMouseTransport()
    relay = WindowsMouseRelay(AppConfig(), allow_target, transport)

    result = relay.apply(MotionAction(Gesture.ROTATE, dx=12, dy=-7))
    relay.apply(MotionAction(Gesture.ROTATE, dx=2, dy=3))
    relay.apply(None)

    assert result.applied is True
    assert transport.events == [
        ("down", "left"),
        ("move", 12, -7),
        ("move", 2, 3),
        ("up", "left"),
    ]


def test_switching_to_pan_changes_held_mouse_button() -> None:
    transport = FakeMouseTransport()
    relay = WindowsMouseRelay(AppConfig(), allow_target, transport)

    relay.apply(MotionAction(Gesture.ROTATE, dx=1, dy=1))
    relay.apply(MotionAction(Gesture.PAN, dx=-4, dy=6))

    assert transport.events == [
        ("down", "left"),
        ("move", 1, 1),
        ("up", "left"),
        ("down", "middle"),
        ("move", -4, 6),
    ]


def test_zoom_releases_drag_before_wheel() -> None:
    transport = FakeMouseTransport()
    relay = WindowsMouseRelay(AppConfig(), allow_target, transport)

    relay.apply(MotionAction(Gesture.ROTATE, dx=3, dy=4))
    result = relay.apply(MotionAction(Gesture.ZOOM, amount=-2))

    assert result.applied is True
    assert transport.events[-2:] == [("up", "left"), ("wheel", -2)]


def test_target_rejection_releases_and_sends_no_new_motion() -> None:
    transport = FakeMouseTransport()
    allowed = True

    def target_guard() -> tuple[bool, str]:
        return allowed, "target mismatch" if not allowed else "target matched"

    relay = WindowsMouseRelay(AppConfig(), target_guard, transport)
    relay.apply(MotionAction(Gesture.ROTATE, dx=3, dy=4))
    allowed = False

    result = relay.apply(MotionAction(Gesture.ROTATE, dx=99, dy=99))

    assert result.applied is False
    assert result.message == "blocked: target mismatch"
    assert transport.events[-1] == ("up", "left")
    assert ("move", 99, 99) not in transport.events


def test_preview_relay_never_applies_mouse_input() -> None:
    relay = PreviewMouseRelay()

    result = relay.apply(MotionAction(Gesture.PAN, dx=5, dy=6))

    assert result.applied is False
    assert result.message == "preview: pan drag +5,+6"
