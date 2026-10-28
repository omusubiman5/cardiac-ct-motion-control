"""Self-verification: failure injection and immutable contracts, not real-hand acceptance."""
import copy
import json
import os
import pytest
from cstamp import CStampController, CTemplate, EventLedger
from cstamp.contracts import DisplayContract
from cstamp.plan_revision import PlanStore
from cstamp.plan import compare_placement, PlanTracker
from cstamp.state_machine import _placement_dict


def prepared():
    controller = CStampController(CTemplate(radius=5))
    controller.stamp((0,0,0), (0,0,1))
    contract = DisplayContract()
    snapshot = contract.request(controller.draft, controller.draft_template, {'model':'synthetic'})
    return controller, contract, snapshot


def test_commit_requires_real_ack_and_exact_identity():
    controller, contract, snapshot = prepared()
    params = {k:snapshot[k] for k in ('draft_id','rev','hash')}
    with pytest.raises(RuntimeError): contract.require(params,controller.draft)
    assert not contract.acknowledge('other')
    assert contract.acknowledge(snapshot['hash'])
    assert contract.require(params,controller.draft) == snapshot
    for field in params:
        wrong = dict(params); wrong[field] = 'wrong'
        with pytest.raises(RuntimeError): contract.require(wrong,controller.draft)
    controller.rotate_opening(.2)
    with pytest.raises(RuntimeError): contract.require(params,controller.draft)


def test_save_lock_blocks_snapshot_and_second_commit():
    c, contract, s = prepared(); contract.acknowledge(s['hash']); contract.saving=True
    with pytest.raises(RuntimeError): contract.request(c.draft,c.draft_template,{})
    with pytest.raises(RuntimeError): contract.require(s,c.draft)


def test_atomic_replace_failure_keeps_disk_and_draft(tmp_path, monkeypatch):
    path = tmp_path/'events.jsonl'; ledger = EventLedger(path)
    ledger.append({'event_id':'first'})
    original = path.read_bytes()
    c,_,_ = prepared()
    def fail(*args): raise OSError('injected replace failure')
    monkeypatch.setattr(os,'replace',fail)
    with pytest.raises(OSError): c.commit(ledger.append,{})
    assert path.read_bytes() == original
    assert c.state.value == 'DRAFT'
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('corruption',['edit','truncated','order'])
def test_corrupted_ledger_never_loads(tmp_path,corruption):
    path=tmp_path/'e.jsonl'; ledger=EventLedger(path); ledger.append({'value':1})
    row=json.loads(path.read_text())
    if corruption=='edit': row['value']=2; path.write_text(json.dumps(row))
    elif corruption=='order': row['order']=9; path.write_text(json.dumps(row))
    else: path.write_text(path.read_text()[:-8])
    with pytest.raises((ValueError,json.JSONDecodeError)): EventLedger(path)


def test_persistent_receipt_and_deep_immutability(tmp_path):
    path=tmp_path/'e.jsonl'; ledger=EventLedger(path)
    data={'placement':{'anchor':[1,2,3]},'request_receipt':{'req':'unique'}}
    result=ledger.append(data); data['placement']['anchor'][0]=99
    result['placement']['anchor'][0]=88
    restored=EventLedger(path)
    assert restored.events()[0]['placement']['anchor']==[1,2,3]
    assert restored.request_result('unique')['persisted']
    assert restored.request_result('missing') is None


def test_stale_writer_does_not_replace_other_commits(tmp_path):
    path=tmp_path/'e.jsonl'; first,second=EventLedger(path),EventLedger(path)
    first.append({'event_id':'a'})
    with pytest.raises(ValueError,match='changed since load'): second.append({'event_id':'b'})
    assert len(EventLedger(path).events())==1


def test_nested_plan_immutability_and_history_restore():
    store=PlanStore(); original=store.create_plan('p',[{'event_id':'a','placement':{'anchor':[0,0,0]}}])
    created={'record_type':'plan_created','plan_id':'p','version':1,'items':copy.deepcopy(original.items),
             'created_ts':original.created_ts,'creator':original.creator,'approval':original.approval}
    store.begin_revision('p'); store.edit_item('p','a',{'placement':{'anchor':[1,0,0]}})
    assert original.items[0]['placement']['anchor']==[0,0,0]
    saved=store.save_revision('p'); recovered=PlanStore(); recovered.restore([created,saved])
    assert len(recovered.get('p').versions)==2
    assert recovered.get('p').current.items[0]['placement']['anchor']==[1,0,0]
    broken=copy.deepcopy(saved); broken['version']=4
    with pytest.raises(ValueError): recovered.restore([created,broken])
    assert recovered.get('p').current.version==2


def test_active_target_not_nearest_future_item():
    c,_,_=prepared(); p=_placement_dict(c.draft.placement)
    tracker=PlanTracker(); far=copy.deepcopy(p);far['anchor']=[100,0,0]
    tracker.load([{'event_id':'active','placement':far},{'event_id':'future','placement':p}])
    result=tracker.record_performed({'event_id':'performed','placement':p},active_only=True)
    assert not result.matched
    assert tracker.current.event_id=='active'
    assert compare_placement(p,far)['anchor_delta_mm']==100


def test_nonfinite_ledger_values_never_reach_disk(tmp_path):
    path=tmp_path/'events.jsonl'
    ledger=EventLedger(path)
    ledger.append({'event_id':'finite','placement':{'anchor':[1,2,3]}})
    before=path.read_bytes()
    with pytest.raises(ValueError):
        ledger.append({'event_id':'bad','placement':{'anchor':[float('nan'),2,3]}})
    assert path.read_bytes()==before
    assert [r['event_id'] for r in EventLedger(path).events()]==['finite']
