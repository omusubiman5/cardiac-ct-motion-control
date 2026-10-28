"""Plan version management (FR-034, docs/23 unit 7).

A plan is a named, ordered set of planned-C items. Edits never touch
the stored version: ``begin_revision`` opens a working copy,
``edit_item``/``delete_item``/``move_item`` mutate it, and
``save_revision`` freezes the working copy as version N+1 while
recording the diff against the previous version. The stored version is
append-only — an approved plan is never overwritten in place.
"""

from __future__ import annotations

import itertools
import copy
import time
from dataclasses import dataclass, field


# item fields a revision may patch; anything else is rejected so a
# revision cannot silently rewrite provenance fields.
EDITABLE_FIELDS = {"placement", "shape_points", "label", "note"}


@dataclass
class PlanVersion:
    plan_id: str
    version: int
    items: list[dict]
    created_ts: float
    creator: str = "operator"
    approval: str = "draft"


@dataclass
class Plan:
    plan_id: str
    versions: list[PlanVersion] = field(default_factory=list)
    working: PlanVersion | None = None

    @property
    def current(self) -> PlanVersion | None:
        return self.versions[-1] if self.versions else None


class PlanStore:
    """Append-only plan registry.

    Each plan keeps every saved version; ``save_revision`` appends a
    new version and returns a ledger-style record describing the diff
    so the caller can persist it to an audit trail.
    """

    def __init__(self) -> None:
        self.plans: dict[str, Plan] = {}
        self._seq = itertools.count(1)
        self.pending_reason: str | None = None

    # --- lifecycle ---------------------------------------------------

    def create_plan(
        self,
        plan_id: str | None = None,
        items: list[dict] | None = None,
        creator: str = "operator",
    ) -> PlanVersion:
        plan_id = plan_id or f"plan-{next(self._seq):04d}"
        if plan_id in self.plans:
            raise ValueError("plan already exists")
        plan = Plan(plan_id=plan_id)
        version = PlanVersion(
            plan_id=plan_id,
            version=1,
            items=copy.deepcopy(items or []),
            created_ts=time.time(),
            creator=creator,
        )
        plan.versions.append(version)
        self.plans[plan_id] = plan
        return version

    def get(self, plan_id: str) -> Plan:
        plan = self.plans.get(plan_id)
        if plan is None:
            raise KeyError("unknown plan")
        return plan

    # --- revision editing ---------------------------------------------

    def begin_revision(self, plan_id: str) -> PlanVersion:
        """Open a working copy of the current version. The stored
        version itself is never mutated."""
        plan = self.get(plan_id)
        if plan.working is not None:
            raise ValueError("a revision is already open")
        current = plan.current
        if current is None:
            raise ValueError("plan has no versions")
        plan.working = PlanVersion(
            plan_id=plan_id,
            version=current.version + 1,
            items=copy.deepcopy(current.items),
            created_ts=time.time(),
            creator=current.creator,
            approval="draft",
        )
        return plan.working

    def saved_version(self, plan_id: str, number: int) -> PlanVersion:
        """Return an isolated historical view, never a mutable stored version."""
        if type(number) is not int or number < 1:
            raise ValueError('saved version must be a positive integer')
        plan = self.get(plan_id)
        for version in plan.versions:
            if version.version == number:
                return copy.deepcopy(version)
        raise ValueError('saved plan version is not registered')

    def _require_working(self, plan_id: str) -> PlanVersion:
        working = self.get(plan_id).working
        if working is None:
            raise ValueError("no open revision; call begin_revision")
        return working

    def _item_index(self, working: PlanVersion, item_id: str) -> int:
        for i, item in enumerate(working.items):
            if item.get("event_id") == item_id or item.get("item_id") == item_id:
                return i
        raise KeyError("item not found")

    def edit_item(
        self, plan_id: str, item_id: str, patch: dict
    ) -> dict:
        working = self._require_working(plan_id)
        bad = set(patch) - EDITABLE_FIELDS
        if bad:
            raise ValueError(
                f"fields not editable via revision: {sorted(bad)}"
            )
        index = self._item_index(working, item_id)
        working.items[index].update(copy.deepcopy(patch))
        return working.items[index]

    def delete_item(self, plan_id: str, item_id: str) -> dict:
        working = self._require_working(plan_id)
        index = self._item_index(working, item_id)
        return working.items.pop(index)

    def replace_rendered_geometry(self, plan_id: str, item_id: str, geometry: dict) -> dict:
        """Internal rendered-C transaction; retain item ID and original provenance.

        The caller must first validate target registry and displayed hash. This
        is separate from the general metadata patch API.
        """
        required={'placement','shape_points','template','target_identity','displayed_snapshot'}
        if set(geometry)!=required:
            raise ValueError('complete rendered geometry is required')
        working=self._require_working(plan_id)
        index=self._item_index(working,item_id)
        working.items[index].update(copy.deepcopy(geometry))
        return working.items[index]

    def add_item(self, plan_id: str, item: dict) -> dict:
        working = self._require_working(plan_id)
        item_id = item.get('event_id') or item.get('item_id')
        if not item_id or any((i.get('event_id') or i.get('item_id')) == item_id for i in working.items):
            raise ValueError('unique item id required')
        working.items.append(copy.deepcopy(item))
        return item

    def move_item(
        self, plan_id: str, from_index: int, to_index: int
    ) -> dict:
        working = self._require_working(plan_id)
        if not (0 <= from_index < len(working.items) and 0 <= to_index < len(working.items)):
            raise IndexError('indices out of range')
        item = working.items.pop(from_index)
        working.items.insert(to_index, item)
        return item

    def cancel_revision(self, plan_id: str) -> None:
        self._require_working(plan_id)
        self.get(plan_id).working = None

    def save_revision(self, plan_id: str) -> dict:
        """Freeze the working copy as the newest version and return an
        append-only record describing the diff. The previous version
        remains untouched."""
        plan = self.get(plan_id)
        working = self._require_working(plan_id)
        previous = plan.current
        record = {
            "record_type": "plan_revision",
            "plan_id": plan_id,
            "version": working.version,
            "based_on": previous.version if previous else None,
            "items": copy.deepcopy(working.items),
            "creator": working.creator,
            "approval": working.approval,
            "created_ts": working.created_ts,
            "diff": diff_versions(previous, working),
            "reason": self.pending_reason or "unspecified",
            "ts": time.time(),
        }
        plan.versions.append(working)
        plan.working = None
        self.pending_reason = None
        return record

    def restore(self, records):
        """Validate the entire history before replacing the live registry."""
        from .plan_diagnostics import require_history
        require_history(records)
        restored = {}
        for row in records:
            kind = row.get('record_type')
            if kind == 'planned_item_commit':
                plan = restored.get(row['plan_id'])
                if plan is None or row['version'] != plan.current.version + 1:
                    raise ValueError('working item parent mismatch')
                plan.working = PlanVersion(row['plan_id'], row['version'], copy.deepcopy(row['working_items']),
                                           row['created_ts'], row['creator'], row['approval'])
                continue
            if kind not in {'plan_created', 'plan_revision'}:
                continue
            plan_id, number = row['plan_id'], row['version']
            plan = restored.setdefault(plan_id, Plan(plan_id))
            if number != len(plan.versions) + 1 or (number == 1) != (kind == 'plan_created'):
                raise ValueError('plan version history is not contiguous')
            if number > 1 and row.get('based_on') != number - 1:
                raise ValueError('plan revision parent mismatch')
            items = copy.deepcopy(row['items'])
            ids = [i.get('event_id') or i.get('item_id') for i in items]
            if any(not i for i in ids) or len(set(ids)) != len(ids):
                raise ValueError('invalid plan item identity')
            plan.working = None
            plan.versions.append(PlanVersion(plan_id, number, items,
                row['created_ts'], row['creator'], row['approval']))
        self.plans = restored
        self.pending_reason = None
        occupied = set(restored)
        self._seq = (i for i in itertools.count(1) if f'plan-{i:04d}' not in occupied)


def diff_versions(
    previous: PlanVersion | None, new: PlanVersion
) -> dict:
    """Describe the change between two versions: added / removed /
    changed item ids and whether the surviving order changed."""
    old_items = previous.items if previous else []
    new_items = new.items
    old_ids = [i.get("event_id") or i.get("item_id") for i in old_items]
    new_ids = [i.get("event_id") or i.get("item_id") for i in new.items]
    old_by_id = dict(zip(old_ids, old_items))
    new_by_id = dict(zip(new_ids, new_items))
    added = [i for i in new_ids if i not in old_by_id]
    removed = [i for i in old_ids if i not in new_by_id]
    changed = [
        i for i in new_ids
        if i in old_by_id and old_by_id[i] != new_by_id[i]
    ]
    surviving_old = [i for i in old_ids if i in new_by_id]
    surviving_new = [i for i in new_ids if i in old_by_id]
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "order_changed": surviving_old != surviving_new,
    }


def compare_saved_geometry(previous: PlanVersion, new: PlanVersion) -> dict:
    """Four requested plan changes; metadata edits are not called rotations."""
    difference = diff_versions(previous, new)
    before = {i.get('event_id') or i.get('item_id'): i for i in previous.items}
    after = {i.get('event_id') or i.get('item_id'): i for i in new.items}
    shared = [key for key in after if key in before]
    moved = [key for key in shared if before[key].get('placement',{}).get('anchor') != after[key].get('placement',{}).get('anchor')]
    def orientation(item):
        return {k:v for k,v in item.get('placement',{}).items() if k != 'anchor'}
    rotated = [key for key in shared if orientation(before[key]) != orientation(after[key])]
    return {**difference, 'moved':moved, 'rotated':rotated}
