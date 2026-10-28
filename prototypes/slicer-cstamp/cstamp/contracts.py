"""Immutable displayed-draft contract; a renderer must explicitly acknowledge it."""
import copy
import hashlib
import json
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


class DisplayContract:
    def __init__(self):
        self.pending = None
        self.displayed = None
        self.saving = False
        self.acknowledged_ns = None

    def request(self, draft, template, target):
        if self.saving:
            raise RuntimeError('save in progress')
        from .state_machine import _placement_dict
        value = {'draft_id': draft.draft_id, 'rev': draft.revision,
                 'placement': _placement_dict(draft.placement),
                 'template': template.definition(), 'target': copy.deepcopy(target)}
        value['hash'] = digest(value)
        self.pending = value
        self.displayed = None
        self.acknowledged_ns = None
        return copy.deepcopy(value)

    def acknowledge(self, snapshot_hash):
        if self.pending and self.pending['hash'] == snapshot_hash:
            self.displayed = copy.deepcopy(self.pending)
            self.acknowledged_ns = time.perf_counter_ns()
            return True
        return False

    def require(self, params, draft):
        value = self.displayed
        if self.saving or not value or not draft:
            raise RuntimeError('display not acknowledged or save in progress')
        for key in ('draft_id', 'rev', 'hash'):
            expected = draft.draft_id if key == 'draft_id' else draft.revision if key == 'rev' else value[key]
            if params.get(key) != expected or value[key] != expected:
                raise RuntimeError('displayed draft identity/version/hash mismatch')
        return copy.deepcopy(value)
