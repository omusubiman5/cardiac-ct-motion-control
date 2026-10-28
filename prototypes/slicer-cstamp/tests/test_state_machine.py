import math

import pytest

from cstamp import (
    CStampController,
    EventLedger,
    StampState,
    StateError,
)


ANCHOR = (1.0, 2.0, 3.0)
NORMAL = (0.0, 0.0, 1.0)


@pytest.fixture
def controller():
    return CStampController()


@pytest.fixture
def ledger(tmp_path):
    return EventLedger(tmp_path / "ledger.jsonl")


def _commit(controller, ledger):
    return controller.commit(ledger.append, {"input_method": "mouse"})


# AC-001: one stamp shows one DRAFT and zero committed events
def test_stamp_creates_single_draft_and_no_event(controller, ledger):
    draft = controller.stamp(ANCHOR, NORMAL)

    assert controller.state is StampState.DRAFT
    assert draft.placement.anchor == ANCHOR
    assert ledger.events() == []


# AC-010: held or repeated stamp input creates only one draft
def test_second_stamp_is_rejected_while_draft(controller, ledger):
    first = controller.stamp(ANCHOR, NORMAL)

    with pytest.raises(StateError):
        controller.stamp((5.0, 5.0, 5.0), NORMAL)

    assert controller.draft.draft_id == first.draft_id
    assert ledger.events() == []


# AC-002 / AC-011: direction-only adjustment leaves anchor and 0 events
def test_direction_adjustment_keeps_anchor_and_no_events(
    controller, ledger
):
    controller.stamp(ANCHOR, NORMAL)
    controller.rotate_opening(math.radians(30.0))

    placement = controller.draft.placement
    assert placement.anchor == ANCHOR
    assert placement.in_plane_angle == pytest.approx(math.radians(30.0))
    assert ledger.events() == []


def test_opening_direction_changes_monotonically(controller):
    controller.stamp(ANCHOR, NORMAL)
    before = controller.draft.placement.opening_dir()

    controller.rotate_opening(0.1)
    mid = controller.draft.placement.opening_dir()
    controller.rotate_opening(0.1)
    after = controller.draft.placement.opening_dir()

    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    assert dot(before, mid) < 1.0
    assert dot(mid, after) < 1.0
    assert dot(before, after) < dot(before, mid)
    assert controller.draft.placement.anchor == ANCHOR


# OP-008: reverse_path flips only the path direction
def test_reverse_path_flips_only_path_dir(controller):
    controller.stamp(ANCHOR, NORMAL)
    before = controller.draft.placement

    controller.reverse_path()
    after = controller.draft.placement

    assert after.path_dir == -before.path_dir
    assert after.anchor == before.anchor
    assert after.normal == before.normal
    assert after.opening_dir() == before.opening_dir()


# OP-009: reset restores the deterministic initial direction
def test_reset_direction_restores_initial(controller):
    controller.stamp(ANCHOR, NORMAL)
    controller.rotate_opening(0.4)
    controller.tilt_plane(0.0, 0.2)
    controller.reverse_path()

    controller.reset_direction()
    p = controller.draft.placement

    assert p.in_plane_angle == 0.0
    assert p.path_dir == 1
    for a, b in zip(p.normal, (0.0, 0.0, 1.0)):
        assert a == pytest.approx(b)


# AC-003: one explicit commit produces exactly one matching event
def test_commit_produces_exactly_one_matching_event(controller, ledger):
    draft = controller.stamp(ANCHOR, NORMAL)
    controller.rotate_opening(0.25)
    displayed = controller.draft.placement

    event = _commit(controller, ledger)

    assert controller.state is StampState.COMMITTED
    assert len(ledger.events()) == 1
    assert event["draft_id"] == draft.draft_id
    assert event["placement"]["anchor"] == list(displayed.anchor)
    assert event["placement"]["opening_dir"] == pytest.approx(
        list(displayed.opening_dir())
    )
    # C shape is fully reconstructable from the stored event
    assert len(event["shape_points"]) == controller.template.segments + 1
    assert event["integrity"]
    assert ledger.verify_integrity(event)


# AC-005: duplicated commit input does not create a second event
def test_duplicate_commit_does_not_append(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    first = _commit(controller, ledger)
    assert controller.state is StampState.COMMITTED

    second = _commit(controller, ledger)

    assert second["deduplicated"] is True
    assert second["event_id"] == first["event_id"]
    assert len(ledger.events()) == 1
    assert ledger.count_for_draft(first["draft_id"]) == 1


# AC-004 / AC-014: cancel works right after stamp and after adjustment
def test_cancel_after_stamp_leaves_no_trace(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    controller.cancel()

    assert controller.state is StampState.IDLE
    assert controller.draft is None
    assert ledger.events() == []


def test_cancel_after_adjustment_leaves_committed_untouched(
    controller, ledger
):
    controller.stamp(ANCHOR, NORMAL)
    committed = _commit(controller, ledger)

    controller.stamp((4.0, 5.0, 6.0), NORMAL)
    controller.rotate_opening(0.3)
    controller.cancel()

    assert controller.state is StampState.IDLE
    assert len(ledger.events()) == 1
    assert ledger.find(committed["event_id"]) == committed


# OP-013 / SR-008: recognition loss freezes; only resume or cancel proceeds
def test_recognition_loss_freezes_draft(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    before = controller.draft.placement
    controller.on_recognition_loss()

    assert controller.frozen
    with pytest.raises(StateError):
        controller.rotate_opening(0.1)
    with pytest.raises(StateError):
        _commit(controller, ledger)

    after = controller.draft.placement
    assert after == before
    assert ledger.events() == []


def test_resume_after_freeze_requires_explicit_call(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    controller.on_recognition_loss()
    controller.resume()

    controller.rotate_opening(0.2)
    assert ledger.events() == []


def test_cancel_is_allowed_while_frozen(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    controller.on_recognition_loss()
    controller.cancel()

    assert controller.state is StampState.IDLE
    assert ledger.events() == []


# MOVE_DRAFT: anchor moves; direction is carried over deterministically
def test_move_draft_keeps_direction_params(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    controller.rotate_opening(0.3)
    controller.reverse_path()
    before = controller.draft.placement

    moved = controller.move_draft((5.0, 6.0, 7.0), NORMAL)

    assert moved.anchor == (5.0, 6.0, 7.0)
    assert moved.in_plane_angle == before.in_plane_angle
    assert moved.path_dir == before.path_dir
    for a, b in zip(moved.normal, NORMAL):
        assert a == pytest.approx(b)
    assert ledger.events() == []


def test_move_draft_to_tilted_surface_projects_u(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)

    moved = controller.move_draft((1.0, 2.0, 4.0), (0.0, 0.5, 0.866))

    # u is projected onto the new plane: still orthonormal
    dot_u_n = sum(a * b for a, b in zip(moved.u, moved.normal))
    dot_v_n = sum(a * b for a, b in zip(moved.v, moved.normal))
    assert dot_u_n == pytest.approx(0.0)
    assert dot_v_n == pytest.approx(0.0)
    assert math.isclose(
        math.sqrt(sum(c * c for c in moved.u)), 1.0, abs_tol=1e-9
    )
    # repeating the same move is stable to floating-point precision
    controller.move_draft((1.0, 2.0, 4.0), (0.0, 0.5, 0.866))
    again = controller.draft.placement
    assert again.u == pytest.approx(moved.u)
    assert again.v == pytest.approx(moved.v)
    assert again.normal == pytest.approx(moved.normal)


def test_move_draft_degenerate_projection_uses_face_basis(controller):
    controller.stamp(ANCHOR, NORMAL)
    # move to a surface whose normal is parallel to the old u axis
    old_u = controller.draft.placement.u
    moved = controller.move_draft((0.0, 0.0, 1.0), old_u)
    assert math.isclose(
        math.sqrt(sum(c * c for c in moved.u)), 1.0, abs_tol=1e-9
    )
    assert math.isclose(
        math.sqrt(sum(c * c for c in moved.v)), 1.0, abs_tol=1e-9
    )


def test_move_draft_frozen_is_rejected(controller):
    controller.stamp(ANCHOR, NORMAL)
    controller.on_recognition_loss()
    with pytest.raises(StateError):
        controller.move_draft((9.0, 9.0, 9.0), NORMAL)


# seed_draft: correction flow starts from a stored placement
def test_seed_draft_reuses_placement_and_marks_new_draft(controller):
    controller.stamp(ANCHOR, NORMAL)
    controller.rotate_opening(0.5)
    original = controller.draft.placement
    controller.cancel()

    seeded = controller.seed_draft(original)

    assert controller.state is StampState.DRAFT
    assert seeded.placement is original
    assert seeded.placement.in_plane_angle == 0.5
    assert seeded.initial_placement is original


def test_seed_draft_commit_can_carry_correction_of(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    original_event = _commit(controller, ledger)
    original_placement = controller.draft.placement

    correction = controller.seed_draft(original_placement)
    assert correction.draft_id != original_event["draft_id"]

    stored = controller.commit(
        ledger.append,
        {"input_method": "mouse",
         "correction_of": original_event["event_id"]},
    )
    assert stored["correction_of"] == original_event["event_id"]
    # original event is immutable
    assert ledger.find(original_event["event_id"]) == original_event
    assert len(ledger.events()) == 2


def test_seed_draft_rejected_while_draft(controller):
    controller.stamp(ANCHOR, NORMAL)
    with pytest.raises(StateError):
        controller.seed_draft(controller.draft.placement)


# COMMITTED --stamp--> DRAFT
def test_stamp_after_commit_creates_new_draft(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    _commit(controller, ledger)

    second = controller.stamp((9.0, 9.0, 9.0), NORMAL)

    assert controller.state is StampState.DRAFT
    assert second.draft_id != "draft-0000"
    assert len(ledger.events()) == 1


# ONI-001: commit binds the displayed draft revision
def test_revision_increments_on_adjustment(controller):
    controller.stamp(ANCHOR, NORMAL)
    assert controller.draft.revision == 0
    controller.rotate_opening(0.1)
    assert controller.draft.revision == 1
    controller.reverse_path()
    assert controller.draft.revision == 2


def test_commit_records_draft_revision(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    controller.rotate_opening(0.5)
    stored = controller.commit(ledger.append, {})
    assert stored["draft_revision"] == 1


def test_commit_with_stale_revision_rejected(controller, ledger):
    controller.stamp(ANCHOR, NORMAL)
    shown_rev = controller.draft.revision  # operator sees rev 0
    controller.rotate_opening(0.5)          # draft now rev 1
    with pytest.raises(StateError, match="changed since display"):
        controller.commit(
            ledger.append, {}, expected_revision=shown_rev
        )
    assert len(ledger.events()) == 0
    # committing with the current revision succeeds
    stored = controller.commit(
        ledger.append, {},
        expected_revision=controller.draft.revision,
    )
    assert stored["draft_revision"] == 1


def test_commit_failure_keeps_draft(controller, ledger):
    """X-01/OP-011: a failing ledger append must leave the DRAFT in
    place and produce no COMMITTED transition."""
    controller.stamp(ANCHOR, NORMAL)

    def failing_append(event):
        raise OSError("disk full")

    with pytest.raises(OSError):
        controller.commit(failing_append, {})
    assert controller.state is StampState.DRAFT
    assert controller.draft is not None
