import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cstamp.storage_selection import load_selection, save_selection


def setup_paths(tmp_path):
    events, plans = tmp_path/'events.jsonl', tmp_path/'plans.jsonl'
    events.touch(); plans.touch()
    return tmp_path/'selection.json', str(events), str(plans)


def test_roundtrip_preserves_ledger_bytes(tmp_path):
    config, events, plans = setup_paths(tmp_path)
    result = save_selection(config, events, plans)
    assert load_selection(config) == result
    assert Path(events).read_bytes() == Path(plans).read_bytes() == b''


def test_missing_settings_only_allows_first_start(tmp_path):
    assert load_selection(tmp_path/'absent.json') is None


@pytest.mark.parametrize('payload', ['{', '[]', '{"schema_version":true}', '{"schema_version":2}'])
def test_bad_settings_rejected(tmp_path, payload):
    path = tmp_path/'bad.json'; path.write_text(payload)
    with pytest.raises((ValueError, TypeError)):
        load_selection(path)


def test_removed_ledger_is_not_created_or_fallen_back(tmp_path):
    config, events, plans = setup_paths(tmp_path)
    save_selection(config, events, plans)
    Path(events).unlink()
    with pytest.raises(FileNotFoundError): load_selection(config)
    assert not Path(events).exists()


def test_reject_same_ledger_and_settings_alias(tmp_path):
    config, events, plans = setup_paths(tmp_path)
    with pytest.raises(ValueError): save_selection(config, events, events)
    with pytest.raises(ValueError): save_selection(events, events, plans)
    assert Path(events).read_bytes() == b''


def test_bad_ledger_cannot_replace_previous_setting(tmp_path):
    config, events, plans = setup_paths(tmp_path)
    save_selection(config, events, plans); before = config.read_bytes()
    bad = tmp_path/'bad.jsonl'; bad.write_text('{"event_id":"invalid"}\n')
    with pytest.raises(ValueError): save_selection(config, str(bad), plans)
    assert config.read_bytes() == before


def test_atomic_write_failure_keeps_previous_selection(tmp_path, monkeypatch):
    config, events, plans = setup_paths(tmp_path)
    save_selection(config, events, plans); before = config.read_bytes()
    def fail(*_): raise OSError('simulated replace failure')
    monkeypatch.setattr('cstamp.storage_selection.os.replace', fail)
    with pytest.raises(OSError): save_selection(config, events, plans)
    assert config.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_reject_relative_path(tmp_path):
    config, events, plans = setup_paths(tmp_path)
    with pytest.raises(ValueError): save_selection(config, 'events.jsonl', plans)
