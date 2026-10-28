"""PlanStore: append-only plan versioning (FR-034)."""
import pytest

from cstamp.plan_revision import PlanStore, diff_versions


def test_saved_version_is_read_only_copy_and_rejects_unknown_or_boolean_version():
    store=PlanStore();store.create_plan(plan_id='history',items=_items('a'))
    store.begin_revision('history');store.edit_item('history','a',{'label':'new'});store.save_revision('history')
    old=store.saved_version('history',1);old.items[0]['placement']['anchor'][0]=999
    assert store.saved_version('history',1).items[0]['placement']['anchor']==[0,0,0]
    assert store.saved_version('history',2).items[0]['label']=='new'
    for value in (True,0,3,'1',None):
        with pytest.raises(ValueError):store.saved_version('history',value)


def test_saved_plan_comparison_separates_position_direction_and_metadata():
    from cstamp.plan_revision import PlanVersion,compare_saved_geometry
    old=PlanVersion('p',1,[{'item_id':'m','placement':{'anchor':[0,0,0],'angle':0}},
        {'item_id':'r','placement':{'anchor':[0,0,0],'angle':0}}, {'item_id':'gone'},
        {'item_id':'label','placement':{'anchor':[0,0,0]},'label':'old'}],0)
    new=PlanVersion('p',2,[{'item_id':'m','placement':{'anchor':[1,0,0],'angle':0}},
        {'item_id':'r','placement':{'anchor':[0,0,0],'angle':1}}, {'item_id':'new'},
        {'item_id':'label','placement':{'anchor':[0,0,0]},'label':'changed'}],1)
    delta=compare_saved_geometry(old,new)
    assert delta['added']==['new'] and delta['removed']==['gone']
    assert delta['moved']==['m'] and delta['rotated']==['r']


def _items(*ids):
    return [{"event_id": i, "placement": {"anchor": [0, 0, 0]}}
            for i in ids]


def test_create_plan_assigns_version_1():
    store = PlanStore()
    v = store.create_plan(items=_items("a", "b"))
    assert v.version == 1
    assert store.get(v.plan_id).current.items[0]["event_id"] == "a"


def test_duplicate_plan_id_rejected():
    store = PlanStore()
    v = store.create_plan(plan_id="p1")
    with pytest.raises(ValueError):
        store.create_plan(plan_id="p1")


def test_edit_requires_open_revision():
    store = PlanStore()
    v = store.create_plan(plan_id="p1", items=_items("a"))
    with pytest.raises(ValueError, match="begin_revision"):
        store.edit_item("p1", "a", {"label": "x"})


def test_revision_edit_then_save_keeps_previous_version():
    store = PlanStore()
    store.create_plan(plan_id="p1", items=_items("a", "b"))
    store.begin_revision("p1")
    store.edit_item("p1", "b", {"label": "moved"})
    record = store.save_revision("p1")

    plan = store.get("p1")
    assert len(plan.versions) == 2
    # previous version untouched
    assert "label" not in plan.versions[0].items[1]
    assert plan.current.items[1]["label"] == "moved"
    assert record["version"] == 2
    assert record["based_on"] == 1
    assert record["diff"]["changed"] == ["b"]


def test_delete_and_add_items_diff():
    store = PlanStore()
    store.create_plan(plan_id="p1", items=_items("a", "b"))
    store.begin_revision("p1")
    store.delete_item("p1", "a")
    store.add_item("p1", {"event_id": "c"})
    record = store.save_revision("p1")
    assert record["diff"]["removed"] == ["a"]
    assert record["diff"]["added"] == ["c"]


def test_move_item_marks_order_changed():
    store = PlanStore()
    store.create_plan(plan_id="p1", items=_items("a", "b", "c"))
    store.begin_revision("p1")
    store.move_item("p1", 0, 2)
    record = store.save_revision("p1")
    assert record["diff"]["order_changed"] is True
    assert record["diff"]["changed"] == []


def test_edit_rejects_non_editable_fields():
    store = PlanStore()
    store.create_plan(plan_id="p1", items=_items("a"))
    store.begin_revision("p1")
    with pytest.raises(ValueError, match="not editable"):
        store.edit_item("p1", "a", {"event_id": "forged"})


def test_rendered_geometry_revision_keeps_original_provenance_and_size_history():
    original={'event_id':'a','creator':'original','template':{'radius':5},'placement':{'anchor':[0,0,0]}}
    store=PlanStore();store.create_plan(plan_id='p',items=[original]);store.begin_revision('p')
    geometry={'placement':{'anchor':[1,0,0]},'shape_points':[[1,2,3]],'template':{'radius':6},
              'target_identity':{'target_id':'registered'},'displayed_snapshot':{'hash':'rendered'}}
    with pytest.raises(ValueError):store.replace_rendered_geometry('p','a',{'placement':geometry['placement']})
    store.replace_rendered_geometry('p','a',geometry);geometry['template']['radius']=99
    store.save_revision('p')
    plan=store.get('p')
    assert plan.versions[0].items[0]['template']['radius']==5
    assert plan.current.items[0]['template']['radius']==6
    assert plan.current.items[0]['creator']=='original' and plan.current.items[0]['event_id']=='a'


def test_second_begin_revision_rejected():
    store = PlanStore()
    store.create_plan(plan_id="p1")
    store.begin_revision("p1")
    with pytest.raises(ValueError):
        store.begin_revision("p1")


def test_cancel_revision_discards_working_copy():
    store = PlanStore()
    store.create_plan(plan_id="p1", items=_items("a"))
    store.begin_revision("p1")
    store.delete_item("p1", "a")
    store.cancel_revision("p1")
    assert store.get("p1").current.items[0]["event_id"] == "a"
    assert store.get("p1").working is None


def test_save_revision_records_reason():
    store = PlanStore()
    store.create_plan(plan_id="p1")
    store.begin_revision("p1")
    store.pending_reason = "anatomy-review"
    record = store.save_revision("p1")
    assert record["reason"] == "anatomy-review"
    # pending reason is consumed
    assert store.pending_reason is None


def test_diff_versions_empty_previous():
    from cstamp.plan_revision import PlanVersion
    new = PlanVersion(plan_id="p", version=1, items=_items("x"),
                      created_ts=0.0)
    diff = diff_versions(None, new)
    assert diff["added"] == ["x"]
    assert diff["removed"] == []
