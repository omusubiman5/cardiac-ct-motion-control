import math
import pytest
from cstamp import CStampController, StateError


def test_next_size_does_not_resize_existing_draft_or_saved_shape():
    c = CStampController()
    c.stamp((0, 0, 0), (0, 0, 1))
    old_hash = c.draft.template_sha256
    c.set_diameter_mm(10)
    assert c.template.radius == 5 and c.draft_template.radius == 10
    saved = c.commit(lambda event: dict(event, event_id="self-check"), {})
    assert saved["template"]["diameter_mm"] == 20
    assert saved["template"]["sha256"] == old_hash
    assert max(math.dist((0, 0, 0), p) for p in saved["shape_points"]) == pytest.approx(10)


def test_current_resize_changes_only_template_and_revision():
    c = CStampController()
    c.stamp((1, 2, 3), (0, 0, 1))
    before = c.draft
    c.set_diameter_mm(10, apply_to_draft=True)
    assert c.draft.placement == before.placement
    assert c.draft.draft_id == before.draft_id
    assert c.draft.revision == before.revision + 1
    assert c.draft.template_sha256 != before.template_sha256
    assert c.draft_template.radius == 5


@pytest.mark.parametrize("value", [True, 0, -1, 201, float("nan"), float("inf"), "10"])
def test_invalid_size_is_inert(value):
    c = CStampController()
    old = c.template
    with pytest.raises(ValueError):
        c.set_diameter_mm(value)
    assert c.template is old


def test_frozen_draft_cannot_be_resized_implicitly():
    c = CStampController()
    c.stamp((0, 0, 0), (0, 0, 1))
    c.on_recognition_loss()
    before = c.draft
    with pytest.raises(StateError):
        c.set_diameter_mm(10, apply_to_draft=True)
    assert c.draft is before and c.frozen
