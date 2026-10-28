import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cstamp.plan import PlanTracker  # noqa: E402


def _event(event_id, anchor, layer="PLANNED", angle=0.0):
    return {
        "event_id": event_id,
        "layer": layer,
        "placement": {
            "anchor": list(anchor),
            "plane": {
                "u": [1.0, 0.0, 0.0],
                "v": [0.0, 1.0, 0.0],
                "normal": [0.0, 0.0, 1.0],
            },
            "in_plane_angle": angle,
            "path_dir": 1,
        },
    }


def _performed(event_id, anchor, angle=0.0, normal=None):
    event = _event(event_id, anchor, layer="PERFORMED", angle=angle)
    if normal is not None:
        event["placement"]["plane"]["normal"] = list(normal)
    return event


def test_load_preserves_order_and_current():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0)), _event("p2", (10, 0, 0))])
    assert tracker.current.event_id == "p1"
    assert tracker.remaining() == 2


def test_match_nearest_within_tolerance():
    tracker = PlanTracker(anchor_tolerance_mm=10.0)
    tracker.load([_event("p1", (0, 0, 0)), _event("p2", (50, 0, 0))])
    result = tracker.record_performed(_performed("x1", (2, 1, 0)))
    assert result.matched
    assert result.planned_event_id == "p1"
    assert result.anchor_delta_mm == pytest.approx(math.sqrt(5.0))
    assert result.normal_delta_deg == pytest.approx(0.0)
    assert tracker.current.event_id == "p2"


def test_out_of_plan_when_beyond_anchor_tolerance():
    tracker = PlanTracker(anchor_tolerance_mm=5.0)
    tracker.load([_event("p1", (0, 0, 0))])
    result = tracker.record_performed(_performed("x1", (20, 0, 0)))
    assert not result.matched
    assert result.planned_event_id is None
    assert tracker.out_of_plan_ids == ["x1"]
    # planned entry is NOT consumed by an out-of-plan event
    assert tracker.remaining() == 1


def test_out_of_plan_when_normal_too_far():
    tracker = PlanTracker(normal_tolerance_deg=10.0)
    tracker.load([_event("p1", (0, 0, 0))])
    result = tracker.record_performed(
        _performed("x1", (1, 0, 0), normal=(0.0, 1.0, 0.0))
    )
    assert not result.matched


def test_in_plane_delta_wrapped():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0), angle=math.radians(170))])
    result = tracker.record_performed(
        _performed("x1", (0, 0, 0), angle=math.radians(-170))
    )
    assert result.matched
    assert result.in_plane_delta_deg == pytest.approx(20.0)


def test_skip_advances_and_blocks_match():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0)), _event("p2", (50, 0, 0))])
    skipped = tracker.skip_current()
    assert skipped.event_id == "p1"
    assert tracker.current.event_id == "p2"
    # skipped plan is no longer a match candidate
    result = tracker.record_performed(_performed("x1", (0, 0, 0)))
    assert not result.matched


def test_matched_entry_not_reused():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0))])
    assert tracker.record_performed(_performed("x1", (0, 0, 0))).matched
    # second performed at the same spot is out-of-plan
    assert not tracker.record_performed(_performed("x2", (0, 0, 0))).matched


def test_status_counts():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0)), _event("p2", (100, 0, 0))])
    tracker.skip_current()
    tracker.record_performed(_performed("x1", (95, 0, 0)))
    tracker.record_performed(_performed("x2", (999, 0, 0)))
    status = tracker.status()
    assert status == {
        "total": 2,
        "remaining": 0,
        "matched": 1,
        "skipped": 1,
        "out_of_plan": 1,
    }


def test_match_record_shape():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0))])
    record = tracker.record_performed(
        _performed("x1", (1, 0, 0))
    ).record()
    assert record["record_type"] == "plan_match"
    assert record["matched"] is True
    assert record["performed_event_id"] == "x1"
    assert record["planned_event_id"] == "p1"


def test_empty_plan_everything_out_of_plan():
    tracker = PlanTracker()
    result = tracker.record_performed(_performed("x1", (0, 0, 0)))
    assert not result.matched


def test_invalid_tolerance_rejected():
    with pytest.raises(ValueError):
        PlanTracker(anchor_tolerance_mm=0.0)


def test_reorder_moves_entry_and_updates_current():
    tracker = PlanTracker()
    tracker.load([
        _event("p1", (0, 0, 0)),
        _event("p2", (10, 0, 0)),
        _event("p3", (20, 0, 0)),
    ])
    moved = tracker.reorder(2, 0)
    assert moved.event_id == "p3"
    assert [e.event_id for e in tracker.entries] == ["p3", "p1", "p2"]
    assert tracker.current.event_id == "p3"


def test_reorder_never_consumes_or_converts_entries():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0)), _event("p2", (50, 0, 0))])
    tracker.reorder(1, 0)
    # reorder only changes order; nothing is matched, skipped, or moved
    # to the performed ledger
    assert tracker.remaining() == 2
    assert tracker.status()["matched"] == 0
    assert all(e.event["layer"] == "PLANNED" for e in tracker.entries)


def test_reorder_out_of_range_rejected():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0))])
    with pytest.raises(IndexError):
        tracker.reorder(0, 5)
    with pytest.raises(IndexError):
        tracker.reorder(-1, 0)


def test_select_makes_entry_the_next_ghost():
    tracker = PlanTracker()
    tracker.load([
        _event("p1", (0, 0, 0)),
        _event("p2", (10, 0, 0)),
        _event("p3", (20, 0, 0)),
    ])
    picked = tracker.select(2)
    assert picked.event_id == "p3"
    assert tracker.current.event_id == "p3"
    # consumed entries stay in place ahead of the reordered one
    tracker.record_performed(_performed("x1", (20, 0, 0)))
    assert tracker.current.event_id == "p1"


def test_select_consumed_entry_rejected():
    tracker = PlanTracker()
    tracker.load([_event("p1", (0, 0, 0))])
    tracker.skip_current()
    with pytest.raises(ValueError):
        tracker.select(0)
