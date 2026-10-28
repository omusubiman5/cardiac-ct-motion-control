from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable

from .geometry import (
    Vec3,
    apply_mat3,
    cross,
    normalize,
    orthonormal_basis,
    rotation_matrix,
)
from .placement import Placement
from .template import CTemplate


class StampState(str, Enum):
    IDLE = "IDLE"
    DRAFT = "DRAFT"
    COMMITTED = "COMMITTED"
    CANCELLED = "CANCELLED"


class StateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Draft:
    draft_id: str
    placement: Placement
    initial_placement: Placement
    template_id: str
    template_version: str
    template_sha256: str
    committed_event_id: str | None = None
    # bumped on every adjustment; commit binds the committed snapshot
    # to the displayed revision (docs/23 ONI-001)
    revision: int = 0


class CStampController:
    """Input-independent C-stamp state machine (docs/03).

    IDLE --stamp--> DRAFT --adjust--> DRAFT --commit--> COMMITTED
                       |--cancel--> CANCELLED --end--> IDLE
    COMMITTED --stamp--> DRAFT

    A commit produces exactly one ledger event per draft; cancelling
    produces none. Recognition loss freezes the draft in place: only an
    explicit resume or cancel continues (OP-013).
    """

    def __init__(
        self,
        template: CTemplate | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.template = template or CTemplate()
        self._counter = itertools.count(1)
        self._id_factory = id_factory or (
            lambda: f"draft-{next(self._counter):04d}"
        )
        self.state = StampState.IDLE
        self._draft: Draft | None = None
        self._draft_template: CTemplate | None = None
        self._frozen = False
        self._last_committed_event_id: str | None = None

    @property
    def draft(self) -> Draft | None:
        return self._draft

    @property
    def frozen(self) -> bool:
        return self._frozen

    @property
    def last_committed_event_id(self) -> str | None:
        return self._last_committed_event_id

    @property
    def draft_template(self) -> CTemplate:
        return getattr(self, "_draft_template", None) or self.template

    def set_diameter_mm(self, diameter_mm: float, apply_to_draft: bool = False):
        """Set next dimensions; changing a draft requires an explicit edit."""
        if isinstance(diameter_mm, bool) or not isinstance(diameter_mm, (int, float)):
            raise ValueError("diameter must be a number in mm")
        if not math.isfinite(diameter_mm) or not 0.1 <= diameter_mm <= 200.0:
            raise ValueError("diameter must be between 0.1 and 200 mm")
        draft = self._require_adjustable() if apply_to_draft else None
        template = replace(self.draft_template if draft else self.template,
                           radius=float(diameter_mm) / 2.0)
        if draft:
            self._draft = replace(draft, template_sha256=template.sha256(),
                                  revision=draft.revision + 1)
            self._draft_template = template
        self.template = template
        return template

    # --- T-002 stamp -------------------------------------------------

    def stamp(
        self,
        anchor: Vec3,
        normal: Vec3,
        preferred_u: Vec3 | None = None,
    ) -> Draft:
        if self.state is StampState.DRAFT:
            raise StateError(
                "a DRAFT already exists; commit or cancel it first"
            )
        u, v, n = orthonormal_basis(normal, preferred_u)
        placement = Placement(
            anchor=tuple(float(c) for c in anchor),
            u=u,
            v=v,
            normal=n,
        )
        self._draft_template = self.template
        self._draft = Draft(
            draft_id=self._id_factory(),
            placement=placement,
            initial_placement=placement,
            template_id=self.template.template_id,
            template_version=self.template.version,
            template_sha256=self.template.sha256(),
        )
        self.state = StampState.DRAFT
        self._frozen = False
        return self._draft

    # --- T-003 direction adjustment -----------------------------------

    def rotate_opening(self, delta_angle: float) -> Placement:
        """Rotate the C opening inside the placement plane (OP-006)."""
        draft = self._require_adjustable()
        self._update(
            in_plane_angle=draft.placement.in_plane_angle + delta_angle
        )
        return self._draft.placement

    def tilt_plane(self, axis_in_plane_angle: float, delta_angle: float) -> Placement:
        """Tilt the placement plane around an in-plane axis while the
        anchor stays fixed (OP-007). axis_in_plane_angle picks the hinge
        direction inside the current plane."""
        draft = self._require_adjustable()
        p = draft.placement
        axis = apply_mat3(
            rotation_matrix(p.normal, axis_in_plane_angle), p.u
        )
        r = rotation_matrix(axis, delta_angle)
        self._update(
            normal=normalize(apply_mat3(r, p.normal)),
            u=normalize(apply_mat3(r, p.u)),
            v=normalize(apply_mat3(r, p.v)),
        )
        return self._draft.placement

    def reverse_path(self) -> Placement:
        """Flip start->end direction only (OP-008)."""
        draft = self._require_adjustable()
        self._update(path_dir=-draft.placement.path_dir)
        return self._draft.placement

    def move_draft(self, anchor: Vec3, normal: Vec3) -> Placement:
        """Move the draft anchor to a new surface point. Direction is
        carried over deterministically: the previous ``u`` is projected
        onto the new plane; if it degenerates (nearly parallel to the
        new normal) the deterministic face basis is used instead.
        ``in_plane_angle`` and ``path_dir`` never change."""
        draft = self._require_adjustable()
        p = draft.placement
        n = normalize(normal)
        u_projected = tuple(
            p.u[i] - sum(p.u[j] * n[j] for j in range(3)) * n[i]
            for i in range(3)
        )
        length = math.sqrt(sum(c * c for c in u_projected))
        if length > 1e-6:
            u = tuple(c / length for c in u_projected)
            v = normalize(cross(n, u))
        else:
            u, v, n = orthonormal_basis(normal)
        self._update(anchor=tuple(float(c) for c in anchor), u=u, v=v,
                     normal=n)
        return self._draft.placement

    def seed_draft(self, placement: Placement) -> Draft:
        """Create a DRAFT from an existing placement (correction flow):
        the new draft starts exactly at the stored placement; committing
        it must carry ``correction_of`` for the source event."""
        if self.state is StampState.DRAFT:
            raise StateError(
                "a DRAFT already exists; commit or cancel it first"
            )
        self._draft_template = self.template
        self._draft = Draft(
            draft_id=self._id_factory(),
            placement=placement,
            initial_placement=placement,
            template_id=self.template.template_id,
            template_version=self.template.version,
            template_sha256=self.template.sha256(),
        )
        self.state = StampState.DRAFT
        self._frozen = False
        return self._draft

    def reset_direction(self) -> Placement:
        """Restore the deterministic initial direction (OP-009)."""
        draft = self._require_adjustable()
        initial = draft.initial_placement
        self._update(
            u=initial.u,
            v=initial.v,
            normal=initial.normal,
            in_plane_angle=initial.in_plane_angle,
            path_dir=initial.path_dir,
        )
        return self._draft.placement

    # --- T-004 commit -------------------------------------------------

    def commit(
        self,
        ledger_append: Callable[[dict], dict],
        event: dict,
        expected_revision: int | None = None,
    ) -> dict:
        """Commit the current draft. Exactly one event per draft id:
        a repeated commit returns the stored event id without appending
        (AC-005), even after the state already moved to COMMITTED.

        ``expected_revision`` binds the commit to the revision the
        operator last saw on screen: if the draft changed since, the
        commit is rejected instead of committing a stale snapshot."""
        if (
            self.state is StampState.COMMITTED
            and self._draft is not None
            and self._draft.committed_event_id is not None
        ):
            return {
                "event_id": self._draft.committed_event_id,
                "deduplicated": True,
            }
        draft = self._require_draft()
        if self._frozen:
            raise StateError("draft is frozen after recognition loss")
        if (
            expected_revision is not None
            and expected_revision != draft.revision
        ):
            raise StateError(
                f"draft changed since display "
                f"(shown rev {expected_revision}, "
                f"current rev {draft.revision})"
            )
        event = dict(event)
        event["draft_id"] = draft.draft_id
        event["draft_revision"] = draft.revision
        event["template"] = {
            "template_id": draft.template_id,
            "version": draft.template_version,
            "sha256": draft.template_sha256,
            "definition": self.draft_template.definition(),
            "units": "mm",
            "diameter_mm": self.draft_template.radius * 2.0,
        }
        event["placement"] = _placement_dict(draft.placement)
        event["shape_points"] = [
            list(p)
            for p in draft.placement.transform_points(
                self.draft_template.local_points(draft.placement.path_dir)
            )
        ]
        stored = ledger_append(event)
        self._draft = replace(
            draft, committed_event_id=stored["event_id"]
        )
        self._last_committed_event_id = stored["event_id"]
        self.state = StampState.COMMITTED
        return stored

    # --- T-005 cancel -------------------------------------------------

    def cancel(self) -> None:
        self._require_draft()
        self._draft = None
        self._frozen = False
        self.state = StampState.IDLE

    # --- recognition loss / resume ------------------------------------

    def on_recognition_loss(self) -> None:
        """Freeze the draft where it is; recognition resuming alone must
        not restart adjustment or commit (OP-013, SR-008)."""
        if self.state is StampState.DRAFT:
            self._frozen = True

    def resume(self) -> None:
        self._frozen = False

    # --- helpers ------------------------------------------------------

    def _require_draft(self) -> Draft:
        if self.state is not StampState.DRAFT or self._draft is None:
            raise StateError("no active DRAFT")
        return self._draft

    def _require_adjustable(self) -> Draft:
        draft = self._require_draft()
        if self._frozen:
            raise StateError("draft is frozen after recognition loss")
        return draft

    def _update(self, **changes) -> None:
        self._draft = replace(
            self._draft,
            placement=replace(self._draft.placement, **changes),
            revision=self._draft.revision + 1,
        )


def _placement_dict(p: Placement) -> dict:
    return {
        "anchor": list(p.anchor),
        "plane": {
            "u": list(p.u),
            "v": list(p.v),
            "normal": list(p.normal),
        },
        "in_plane_angle": p.in_plane_angle,
        "opening_dir": list(p.opening_dir()),
        "path_dir": p.path_dir,
        "transform_3x4": p.transform_3x4(),
    }
