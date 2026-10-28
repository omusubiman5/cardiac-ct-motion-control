from datetime import datetime, timezone

import pytest

from cstamp import EventLedger


FIXED_TIME = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def ledger(tmp_path):
    counter = iter(range(1, 100))
    return EventLedger(
        tmp_path / "events.jsonl",
        clock=lambda: FIXED_TIME,
        id_factory=lambda: f"ev-{next(counter):04d}",
    )


def test_append_assigns_order_timestamp_and_integrity(ledger):
    event = ledger.append({"draft_id": "d-1"})

    assert event["event_id"] == "ev-0001"
    assert event["order"] == 0
    assert event["committed_at"] == FIXED_TIME.isoformat()
    assert ledger.verify_integrity(event)


def test_events_are_append_only_and_ordered(ledger):
    first = ledger.append({"draft_id": "d-1"})
    second = ledger.append({"draft_id": "d-2"})

    assert [e["event_id"] for e in ledger.events()] == [
        first["event_id"],
        second["event_id"],
    ]
    assert [e["order"] for e in ledger.events()] == [0, 1]


# AC-018: save, close, reload reproduces every stored field
def test_reload_reproduces_events(ledger, tmp_path):
    ledger.append({"draft_id": "d-1", "placement": {"anchor": [1, 2, 3]}})

    reloaded = EventLedger(
        ledger.path,
        clock=lambda: FIXED_TIME,
        id_factory=lambda: "unused",
    )

    assert reloaded.events() == ledger.events()
    assert reloaded.verify_integrity(reloaded.events()[0])


def test_integrity_detects_tampering(ledger):
    event = dict(ledger.append({"draft_id": "d-1"}))
    event["draft_id"] = "d-evil"

    assert not ledger.verify_integrity(event)


def test_count_for_draft(ledger):
    ledger.append({"draft_id": "d-1"})
    ledger.append({"draft_id": "d-2"})
    ledger.append({"draft_id": "d-1"})

    assert ledger.count_for_draft("d-1") == 2
    assert ledger.count_for_draft("d-2") == 1
