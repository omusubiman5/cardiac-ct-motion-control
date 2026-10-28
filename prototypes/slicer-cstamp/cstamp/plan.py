"""Plan-following support: PLANNED vs PERFORMED layers (AC-019..AC-024).

A plan is an ordered list of PLANNED-layer ledger events created
preoperatively. During the operation the tracker shows the next planned
C as a ghost, matches each PERFORMED event to the nearest remaining
planned C, supports explicit skipping, and marks performed events that
match nothing as out-of-plan. Planned events are never converted into
performed events automatically.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping


PLANNED = "PLANNED"
PERFORMED = "PERFORMED"


def compare_placement(actual, planned):
    """Geometric differences against the explicitly active item, without consuming it."""
    a, b = actual or {}, planned or {}
    angle_a, angle_b = a.get('in_plane_angle'), b.get('in_plane_angle')
    normal_a, normal_b = (a.get('plane') or {}).get('normal'), (b.get('plane') or {}).get('normal')
    return {
        'anchor_delta_mm': _distance(a['anchor'], b['anchor']) if 'anchor' in a and 'anchor' in b else None,
        'normal_delta_deg': _angle_between(normal_a, normal_b) if normal_a is not None and normal_b is not None else None,
        'in_plane_delta_deg': _wrap_degrees(math.degrees(angle_a-angle_b)) if angle_a is not None and angle_b is not None else None,
        'path_dir_same': a.get('path_dir') == b.get('path_dir') if 'path_dir' in a and 'path_dir' in b else None,
    }


@dataclass
class PlanEntry:
    """One planned C loaded from a PLANNED ledger event."""

    event_id: str
    event: dict
    matched_performed_id: str | None = None
    skipped: bool = False


@dataclass(frozen=True)
class MatchResult:
    performed_event_id: str
    planned_event_id: str | None
    matched: bool
    anchor_delta_mm: float | None = None
    normal_delta_deg: float | None = None
    in_plane_delta_deg: float | None = None
    path_dir_same: bool | None = None

    def record(self) -> dict:
        """Ledger line recording the match decision (append-only)."""
        return {
            "record_type": "plan_match",
            "performed_event_id": self.performed_event_id,
            "planned_event_id": self.planned_event_id,
            "matched": self.matched,
            "anchor_delta_mm": self.anchor_delta_mm,
            "normal_delta_deg": self.normal_delta_deg,
            "in_plane_delta_deg": self.in_plane_delta_deg,
            "path_dir_same": self.path_dir_same,
        }


class PlanTracker:
    """Tracks progress through an ordered plan.

    ``record_performed`` finds the nearest unconsumed planned event
    within the tolerances; otherwise the performed event is out-of-plan
    (still recorded — an out-of-plan action is an event, not an error).
    """

    def __init__(
        self,
        anchor_tolerance_mm: float = 10.0,
        normal_tolerance_deg: float = 30.0,
    ) -> None:
        if anchor_tolerance_mm <= 0 or normal_tolerance_deg <= 0:
            raise ValueError("tolerances must be positive")
        self.anchor_tolerance_mm = anchor_tolerance_mm
        self.normal_tolerance_deg = normal_tolerance_deg
        self.entries: list[PlanEntry] = []
        self.out_of_plan_ids: list[str] = []

    # --- loading ---------------------------------------------------------

    def load(self, planned_events: Iterable[Mapping]) -> None:
        """Replace the plan with the given PLANNED-layer events,
        preserving ledger order."""
        self.entries = [
            PlanEntry(str(e["event_id"]), dict(e)) for e in planned_events
        ]
        self.out_of_plan_ids = []

    @property
    def current(self) -> PlanEntry | None:
        """The next planned C to display as the ghost target."""
        for entry in self.entries:
            if entry.matched_performed_id is None and not entry.skipped:
                return entry
        return None

    def remaining(self) -> int:
        return sum(
            1
            for e in self.entries
            if e.matched_performed_id is None and not e.skipped
        )

    def status(self) -> dict:
        return {
            "total": len(self.entries),
            "remaining": self.remaining(),
            "matched": sum(
                1 for e in self.entries if e.matched_performed_id is not None
            ),
            "skipped": sum(1 for e in self.entries if e.skipped),
            "out_of_plan": len(self.out_of_plan_ids),
        }

    # --- intraoperative operations ---------------------------------------

    def record_performed(self, performed: Mapping, active_only: bool = False) -> MatchResult:
        """Match one committed PERFORMED event against the remaining
        plan. Consumes the matched planned entry."""
        performed_id = str(performed["event_id"])
        placement = performed.get("placement") or {}
        anchor = placement.get("anchor")
        normal = (placement.get("plane") or {}).get("normal")
        in_plane = placement.get("in_plane_angle")
        path_dir = placement.get("path_dir")

        best: PlanEntry | None = None
        best_distance = math.inf
        if anchor is not None:
            for entry in self.entries:
                if active_only and entry is not self.current:
                    continue
                if entry.matched_performed_id is not None or entry.skipped:
                    continue
                planned_anchor = (
                    entry.event.get("placement") or {}
                ).get("anchor")
                if planned_anchor is None:
                    continue
                distance = _distance(anchor, planned_anchor)
                if distance < best_distance:
                    best_distance = distance
                    best = entry

        if best is not None:
            planned_normal = (
                best.event.get("placement", {}).get("plane", {}) or {}
            ).get("normal")
            normal_delta = (
                _angle_between(normal, planned_normal)
                if normal is not None and planned_normal is not None
                else None
            )
            within = best_distance <= self.anchor_tolerance_mm and (
                normal_delta is None
                or normal_delta <= self.normal_tolerance_deg
            )
            if within:
                planned_in_plane = best.event.get("placement", {}).get(
                    "in_plane_angle"
                )
                in_plane_delta = (
                    _wrap_degrees(math.degrees(in_plane - planned_in_plane))
                    if in_plane is not None and planned_in_plane is not None
                    else None
                )
                planned_dir = best.event.get("placement", {}).get("path_dir")
                path_same = (
                    path_dir == planned_dir
                    if path_dir is not None and planned_dir is not None
                    else None
                )
                best.matched_performed_id = performed_id
                return MatchResult(
                    performed_event_id=performed_id,
                    planned_event_id=best.event_id,
                    matched=True,
                    anchor_delta_mm=best_distance,
                    normal_delta_deg=normal_delta,
                    in_plane_delta_deg=in_plane_delta,
                    path_dir_same=path_same,
                )

        self.out_of_plan_ids.append(performed_id)
        return MatchResult(
            performed_event_id=performed_id,
            planned_event_id=None,
            matched=False,
        )

    def skip_current(self) -> PlanEntry | None:
        """Explicitly skip the current planned C (AC-022)."""
        entry = self.current
        if entry is not None:
            entry.skipped = True
        return entry

    def reorder(self, from_index: int, to_index: int) -> PlanEntry:
        """Move the entry at ``from_index`` to ``to_index`` in the plan
        order. Indices refer to the full entries list."""
        if not (0 <= from_index < len(self.entries)):
            raise IndexError("from_index out of range")
        if not (0 <= to_index < len(self.entries)):
            raise IndexError("to_index out of range")
        entry = self.entries.pop(from_index)
        self.entries.insert(to_index, entry)
        return entry

    def select(self, index: int) -> PlanEntry:
        """Designate the entry at ``index`` as the next ghost target by
        moving it ahead of all remaining entries."""
        if not (0 <= index < len(self.entries)):
            raise IndexError("index out of range")
        entry = self.entries[index]
        if entry.matched_performed_id is not None or entry.skipped:
            raise ValueError("entry is consumed")
        remaining_start = next(
            (i for i, e in enumerate(self.entries)
             if e.matched_performed_id is None and not e.skipped),
            len(self.entries),
        )
        self.entries.pop(index)
        self.entries.insert(remaining_start, entry)
        return entry


def _distance(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _angle_between(a, b) -> float:
    na = math.sqrt(sum(c * c for c in a)) or 1.0
    nb = math.sqrt(sum(c * c for c in b)) or 1.0
    dot = sum(x * y for x, y in zip(a, b)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def _wrap_degrees(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0
