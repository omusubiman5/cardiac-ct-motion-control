import pytest

from cstamp import (
    CStampController,
    CTemplate,
    EventLedger,
    StampState,
    placement_from_dict,
)


def _commit(controller, ledger, input_method="mouse"):
    return controller.commit(ledger.append, {"input_method": input_method})


# AC-015: a point display may replace the C view, but the committed event
# keeps the full C shape, position and orientation
def test_committed_event_retains_full_c_data(tmp_path):
    controller = CStampController()
    ledger = EventLedger(tmp_path / "events.jsonl")
    controller.stamp((1.0, 2.0, 3.0), (0.0, 0.0, 1.0))
    controller.rotate_opening(0.3)

    event = _commit(controller, ledger)

    # the simplified display needs only the anchor; the event still
    # carries the whole C so nothing is lost by switching the view
    assert event["placement"]["anchor"] == [1.0, 2.0, 3.0]
    assert len(event["shape_points"]) == controller.template.segments + 1
    assert event["placement"]["in_plane_angle"] == pytest.approx(0.3)


# AC-016: selecting a committed point re-displays the same C shape
def test_reconstructed_c_matches_committed_shape(tmp_path):
    controller = CStampController()
    ledger = EventLedger(tmp_path / "events.jsonl")
    controller.stamp((1.0, 2.0, 3.0), (0.0, 0.0, 1.0))
    controller.rotate_opening(0.3)
    event = _commit(controller, ledger)

    placement = placement_from_dict(event["placement"])
    rebuilt = placement.transform_points(
        CTemplate().local_points(placement.path_dir)
    )

    for stored, rebuilt_pt in zip(event["shape_points"], rebuilt):
        assert stored == pytest.approx(list(rebuilt_pt))


# AC-017: three commits at different placements are stored as three
# independent, ordered events, each reconstructable on its own
def test_three_sequential_commits_are_independent_and_ordered(tmp_path):
    controller = CStampController()
    ledger = EventLedger(tmp_path / "events.jsonl")
    placements = [
        ((0.0, 0.0, 0.0), 0.0),
        ((5.0, 0.0, 0.0), 0.2),
        ((10.0, 0.0, 0.0), 0.4),
    ]

    events = []
    for anchor, angle in placements:
        controller.stamp(anchor, (0.0, 0.0, 1.0))
        controller.rotate_opening(angle)
        events.append(_commit(controller, ledger))
        assert controller.state is StampState.COMMITTED

    ids = {e["event_id"] for e in ledger.events()}
    assert len(ids) == 3
    assert [e["order"] for e in ledger.events()] == [0, 1, 2]

    for event, (anchor, angle) in zip(ledger.events(), placements):
        placement = placement_from_dict(event["placement"])
        rebuilt = placement.transform_points(
            CTemplate().local_points(placement.path_dir)
        )
        assert event["placement"]["anchor"] == list(anchor)
        for stored, pt in zip(event["shape_points"], rebuilt):
            assert stored == pytest.approx(list(pt))


# AC-018: after save + reload every stored field reproduces
def test_save_close_reload_reproduces_all_fields(tmp_path):
    controller = CStampController()
    ledger = EventLedger(tmp_path / "events.jsonl")
    controller.stamp((1.0, 2.0, 3.0), (0.0, 0.0, 1.0))
    controller.rotate_opening(0.15)
    _commit(controller, ledger)
    controller.stamp((2.0, 0.0, 1.0), (0.0, 0.0, 1.0))
    _commit(controller, ledger)

    reloaded = EventLedger(tmp_path / "events.jsonl")

    assert reloaded.events() == ledger.events()
    for event in reloaded.events():
        assert reloaded.verify_integrity(event)
        placement_from_dict(event["placement"])
