import math

import pytest

from cstamp import CTemplate


def test_same_definition_produces_same_hash():
    assert CTemplate().sha256() == CTemplate().sha256()


def test_different_radius_produces_different_hash():
    assert CTemplate(radius=10.0).sha256() != CTemplate(radius=8.0).sha256()


def test_local_points_form_arc_with_opening_gap():
    template = CTemplate(radius=10.0, opening_deg=60.0, segments=32)
    points = template.local_points()

    assert len(points) == 33
    # every point lies on the circle of the given radius in z=0
    for x, y, z in points:
        assert math.hypot(x, y) == pytest.approx(10.0)
        assert z == 0.0
    # the gap is centered on +X: start/end are the two lips of the opening
    start, end = points[0], points[-1]
    half = math.radians(30.0)
    assert start[0] == pytest.approx(10.0 * math.cos(half))
    assert start[1] == pytest.approx(10.0 * math.sin(half))
    assert end[0] == pytest.approx(10.0 * math.cos(half))
    assert end[1] == pytest.approx(-10.0 * math.sin(half))


def test_path_dir_minus_one_swaps_start_and_end():
    template = CTemplate()
    forward = template.local_points(path_dir=1)
    backward = template.local_points(path_dir=-1)

    assert forward[0] == backward[-1]
    assert forward[-1] == backward[0]
    assert len(forward) == len(backward)
