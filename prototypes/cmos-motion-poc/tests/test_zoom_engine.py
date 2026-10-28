import pytest

from zoom_engine import SmoothZoom, ZoomConfig


def test_deadzone_blocks_tiny_input():
    zoom = SmoothZoom()
    zoom.update(0.005, 1 / 60)
    zoom.update(0.005, 1 / 60)

    assert zoom.ratio == 1.0
    assert zoom.velocity == 0.0


# AC-012: constant zoom-in, release, constant zoom-out
def test_monotonic_zoom_in_stop_and_zoom_out():
    zoom = SmoothZoom()
    ratios = []
    for _ in range(60):
        ratios.append(zoom.update(0.8, 1 / 60).ratio)

    assert all(a < b for a, b in zip(ratios, ratios[1:]))
    assert all(v <= ZoomConfig().max_velocity + 1e-9 for v in
               [zoom.velocity])

    for _ in range(120):
        zoom.update(None, 1 / 60)
    assert zoom.velocity == pytest.approx(0.0)
    stopped = zoom.ratio
    zoom.update(None, 1 / 60)
    assert zoom.ratio == stopped  # no drift after stop

    ratios = []
    for _ in range(60):
        ratios.append(zoom.update(-0.8, 1 / 60).ratio)
    assert all(a > b for a, b in zip(ratios, ratios[1:]))


def test_ratio_is_clamped_at_max_and_no_drift():
    zoom = SmoothZoom(ZoomConfig(max_velocity=10.0, max_ratio=1.2))
    for _ in range(600):
        zoom.update(1.0, 1 / 60)

    assert zoom.ratio == pytest.approx(1.2)
    zoom.update(1.0, 1 / 60)
    assert zoom.ratio == pytest.approx(1.2)


def test_zero_strength_decays_to_stop():
    zoom = SmoothZoom()
    for _ in range(60):
        zoom.update(0.9, 1 / 60)
    for _ in range(60):
        zoom.update(0.0, 1 / 60)

    # zero strength keeps velocity at target=0 via accel approach
    assert zoom.velocity <= zoom.config.accel * zoom.config.max_velocity / 60
