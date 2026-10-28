from __future__ import annotations

from dataclasses import dataclass

from .geometry import (
    Vec3,
    add,
    cross,
    dot,
    norm,
    normalize,
    scale,
    sub,
)


@dataclass(frozen=True)
class AimResult:
    hit: bool
    point: Vec3 | None = None
    normal: Vec3 | None = None
    face_index: int = -1
    reason: str = ""


def ray_mesh_intersection(
    origin: Vec3,
    direction: Vec3,
    vertices: list[Vec3],
    faces: list[tuple[int, int, int]],
) -> AimResult:
    """Nearest ray-triangle intersection (Moller-Trumbore)."""
    d = normalize(direction)
    best: tuple[float, int, Vec3] | None = None
    for index, (ia, ib, ic) in enumerate(faces):
        t = _ray_triangle(origin, d, vertices[ia], vertices[ib], vertices[ic])
        if t is not None and t > 1e-9 and (best is None or t < best[0]):
            best = (t, index, (vertices[ia], vertices[ib], vertices[ic]))
    if best is None:
        return AimResult(False, reason="no surface intersection")
    t, index, (a, b, c) = best
    normal = cross(sub(b, a), sub(c, a))
    return AimResult(
        True,
        point=add(origin, scale(d, t)),
        normal=normalize(normal),
        face_index=index,
    )


def _ray_triangle(
    origin: Vec3, direction: Vec3, a: Vec3, b: Vec3, c: Vec3
) -> float | None:
    eps = 1e-12
    edge1 = sub(b, a)
    edge2 = sub(c, a)
    pvec = cross(direction, edge2)
    det = dot(edge1, pvec)
    if abs(det) < eps:
        return None
    inv = 1.0 / det
    tvec = sub(origin, a)
    u = dot(tvec, pvec) * inv
    if u < -eps or u > 1.0 + eps:
        return None
    qvec = cross(tvec, edge1)
    v = dot(direction, qvec) * inv
    if v < -eps or u + v > 1.0 + eps:
        return None
    t = dot(edge2, qvec) * inv
    return t if t > eps else None


def face_normal(vertices: list[Vec3], face: tuple[int, int, int]) -> Vec3:
    a, b, c = (vertices[i] for i in face)
    n = cross(sub(b, a), sub(c, a))
    length = norm(n)
    if length < 1e-12:
        raise ValueError("degenerate face has no normal")
    return scale(n, 1.0 / length)
