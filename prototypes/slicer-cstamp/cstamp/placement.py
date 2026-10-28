from __future__ import annotations

from dataclasses import dataclass

from .geometry import (
    Mat3,
    Vec3,
    apply_mat3,
    columns_to_mat3,
    cross,
    normalize,
    rotation_matrix,
)


@dataclass(frozen=True)
class Placement:
    """Position and orientation of one C stamp on a surface.

    The plane is defined by (u, v, normal). in_plane_angle rotates the C
    inside that plane relative to u. opening_dir is the in-plane vector
    the C gap faces. path_dir +1/-1 selects the start-to-end direction of
    the arc and never alters anchor, opening direction, or shape.
    """

    anchor: Vec3
    u: Vec3
    v: Vec3
    normal: Vec3
    in_plane_angle: float = 0.0
    path_dir: int = 1

    def opening_dir(self) -> Vec3:
        return normalize(
            apply_mat3(
                rotation_matrix(self.normal, self.in_plane_angle), self.u
            )
        )

    def in_plane_perp(self) -> Vec3:
        return normalize(cross(self.normal, self.opening_dir()))

    def rotation_mat3(self) -> Mat3:
        """Columns: opening_dir -> local X, in-plane perp -> local Y,
        normal -> local Z."""
        return columns_to_mat3(
            self.opening_dir(), self.in_plane_perp(), self.normal
        )

    def transform_point(self, local: Vec3) -> Vec3:
        rotated = apply_mat3(self.rotation_mat3(), local)
        return (
            self.anchor[0] + rotated[0],
            self.anchor[1] + rotated[1],
            self.anchor[2] + rotated[2],
        )

    def transform_points(self, local_points: list[Vec3]) -> list[Vec3]:
        return [self.transform_point(p) for p in local_points]

    def transform_3x4(self) -> list[list[float]]:
        """Full transform from template-local to model coordinates."""
        r = self.rotation_mat3()
        return [
            [r[0][0], r[0][1], r[0][2], self.anchor[0]],
            [r[1][0], r[1][1], r[1][2], self.anchor[1]],
            [r[2][0], r[2][1], r[2][2], self.anchor[2]],
        ]


def placement_from_dict(data: dict) -> Placement:
    """Rebuild a stored placement (read-only reconstruction, FR-026)."""
    plane = data["plane"]
    return Placement(
        anchor=tuple(data["anchor"]),
        u=tuple(plane["u"]),
        v=tuple(plane["v"]),
        normal=tuple(plane["normal"]),
        in_plane_angle=data["in_plane_angle"],
        path_dir=data["path_dir"],
    )
