from __future__ import annotations

import math

Vec3 = tuple[float, float, float]
Mat3 = tuple[Vec3, Vec3, Vec3]


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def is_near_zero(a: Vec3, eps: float = 1e-12) -> bool:
    return norm(a) < eps


def normalize(a: Vec3) -> Vec3:
    length = norm(a)
    if length < 1e-12:
        raise ValueError("cannot normalize a zero-length vector")
    return scale(a, 1.0 / length)


def rotation_matrix(axis: Vec3, angle: float) -> Mat3:
    """Rodrigues rotation matrix around a unit axis."""
    k = normalize(axis)
    c, s = math.cos(angle), math.sin(angle)
    kx, ky, kz = k
    t = 1.0 - c
    return (
        (c + kx * kx * t, kx * ky * t - kz * s, kx * kz * t + ky * s),
        (ky * kx * t + kz * s, c + ky * ky * t, ky * kz * t - kx * s),
        (kz * kx * t - ky * s, kz * ky * t + kx * s, c + kz * kz * t),
    )


def apply_mat3(m: Mat3, v: Vec3) -> Vec3:
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def columns_to_mat3(x: Vec3, y: Vec3, z: Vec3) -> Mat3:
    return (
        (x[0], y[0], z[0]),
        (x[1], y[1], z[1]),
        (x[2], y[2], z[2]),
    )


def orthonormal_basis(normal: Vec3, preferred_u: Vec3 | None = None) -> tuple[Vec3, Vec3, Vec3]:
    """Deterministic tangent basis for a placement plane.

    Returns (u, v, n). When preferred_u is given it is projected onto the
    plane; otherwise a fixed reference axis picks u so that the same
    (normal) input always produces the same basis.
    """
    n = normalize(normal)
    if preferred_u is not None:
        projected = sub(preferred_u, scale(n, dot(preferred_u, n)))
        if not is_near_zero(projected):
            u = normalize(projected)
        else:
            u = _reference_tangent(n)
    else:
        u = _reference_tangent(n)
    return u, cross(n, u), n


def _reference_tangent(n: Vec3) -> Vec3:
    reference = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    return normalize(cross(reference, n))
