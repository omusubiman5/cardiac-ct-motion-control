from __future__ import annotations

import hashlib
import json
import os
import uuid
import copy
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping


def _canonical(data: Mapping) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _integrity(data: Mapping) -> str:
    return hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()


class EventLedger:
    """Append-only JSONL store for committed C-stamp events.

    Each line is one immutable event (FR-014, FR-027, FR-030). Corrections
    must link a new event to the original via ``correction_of``; existing
    lines are never rewritten.
    """

    def __init__(
        self,
        path: str | Path,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.path = Path(path)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._events: list[dict] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    event = json.loads(line)
                    if not isinstance(event, dict) or not self.verify_integrity(event):
                        raise ValueError('ledger integrity verification failed')
                    if event.get('order') != len(self._events):
                        raise ValueError('ledger order verification failed')
                    if any(e['event_id']==event.get('event_id') for e in self._events):
                        raise ValueError('duplicate event identity')
                    self._events.append(event)
        self._disk_hash = hashlib.sha256(self.path.read_bytes()).hexdigest() if self.path.exists() else None

    def append(self, event: Mapping) -> dict:
        stored = copy.deepcopy(dict(event))
        stored.pop("integrity",None)
        stored.setdefault("event_id", self._id_factory())
        if any(e['event_id']==stored['event_id'] for e in self._events):
            raise ValueError('duplicate event identity')
        stored["order"] = len(self._events)
        stored.setdefault("committed_at", self._clock().isoformat())
        stored["integrity"] = _integrity(stored)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # A complete ledger and its embedded request receipts become visible
        # in one replace. A crash cannot expose an appended partial JSON line.
        lock_path = self.path.with_suffix(self.path.suffix + '.lock')
        with lock_path.open('a+b') as lock:
            lock.seek(0)
            if os.name == 'nt':
                import msvcrt
                if lock_path.stat().st_size == 0:
                    lock.write(b'0'); lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            temporary = None
            try:
                disk_hash = hashlib.sha256(self.path.read_bytes()).hexdigest() if self.path.exists() else None
                if disk_hash != self._disk_hash:
                    raise ValueError('ledger changed since load; reload before writing')
                with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.path.parent,
                                                 prefix=self.path.name+'.', suffix='.tmp', delete=False) as stream:
                    temporary = Path(stream.name)
                    for row in [*self._events, stored]:
                        stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                    stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, self.path)
                self.last_persisted_ns = __import__('time').perf_counter_ns()
                temporary = None
                self._disk_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
                if os.name == 'nt':
                    lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        self._events.append(stored)
        return copy.deepcopy(stored)

    def events(self) -> list[dict]:
        return copy.deepcopy(self._events)

    def find(self, event_id: str) -> dict | None:
        for event in self._events:
            if event.get("event_id") == event_id:
                return copy.deepcopy(event)
        return None

    def count_for_draft(self, draft_id: str) -> int:
        return sum(1 for e in self._events if e.get("draft_id") == draft_id)

    def verify_integrity(self, event: Mapping) -> bool:
        payload = {k: v for k, v in event.items() if k != "integrity"}
        return _integrity(payload) == event.get("integrity")

    def request_result(self, request_id: str) -> dict | None:
        for event in self._events:
            receipt = event.get('request_receipt') or {}
            if receipt.get('req') == request_id:
                return {'ok': True, 'event_id': event['event_id'],
                        'result': {'draft_revision': event.get('draft_revision')},
                        'persisted': True, 'binding':copy.deepcopy(receipt.get('params') or {})}
        return None
