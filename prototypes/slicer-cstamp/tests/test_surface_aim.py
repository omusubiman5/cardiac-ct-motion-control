import pytest

from cstamp import face_normal, ray_mesh_intersection


# A unit square on the z=0 plane made of two triangles (normals +z)
VERTICES = [
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (1.0, 1.0, 0.0),
    (0.0, 1.0, 0.0),
]
FACES = [(0, 1, 2), (0, 2, 3)]


def test_ray_hits_surface_and_returns_point_and_normal():
    result = ray_mesh_intersection(
        (0.5, 0.5, 5.0), (0.0, 0.0, -1.0), VERTICES, FACES
    )

    assert result.hit is True
    assert result.point == pytest.approx((0.5, 0.5, 0.0))
    assert result.normal == pytest.approx((0.0, 0.0, 1.0))
    assert result.face_index == 0


# AC-009: aiming outside the allowed surface reports "cannot place"
def test_ray_outside_surface_reports_no_hit():
    result = ray_mesh_intersection(
        (5.0, 5.0, 5.0), (0.0, 0.0, -1.0), VERTICES, FACES
    )

    assert result.hit is False
    assert result.point is None


def test_ray_parallel_to_surface_reports_no_hit():
    result = ray_mesh_intersection(
        (0.5, 0.5, 5.0), (1.0, 0.0, 0.0), VERTICES, FACES
    )

    assert result.hit is False


def test_face_normal_of_ccw_triangle_points_up():
    assert face_normal(VERTICES, FACES[0]) == pytest.approx((0.0, 0.0, 1.0))
