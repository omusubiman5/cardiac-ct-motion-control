import copy
import pytest
from cstamp.runtime_contract import RuntimePolicy, canonical_hash
from cstamp.plan_diagnostics import inspect_records
from cstamp.plan_revision import PlanStore


def document():
    return {'schema_version':1, 'slicer_version':'5.12.3','target_registry_sha256':'a'*64,
            'recognizer':{'settings':{'hold':1.5},'camera':{'index':1,'width':1280,'height':720,'backend':'DSHOW','device_path_sha256':'d'*64},
                          'software_sha256':{'app.py':'c'*64},'model_sha256':'b'*64,
                          'python_version':'3.12','windows_version':'test'}}


def test_runtime_order_independence_and_actual_value_mismatch():
    doc=document();policy=RuntimePolicy(doc)
    assert canonical_hash(dict(reversed(list(doc.items()))))==policy.sha256
    assert policy.verify(doc['recognizer'],'5.12.3','a'*64)==policy.sha256
    actual=copy.deepcopy(doc['recognizer']);actual['camera']['width']=640
    with pytest.raises(ValueError):policy.verify(actual,'5.12.3','a'*64)
    with pytest.raises(ValueError):policy.verify_local('5.12.4','a'*64)
    with pytest.raises(ValueError):policy.verify_local('5.12.3','f'*64)


def test_runtime_immutable_and_finite():
    doc=document();policy=RuntimePolicy(doc);doc['recognizer']['settings']['hold']=3
    assert policy.document['recognizer']['settings']['hold']==1.5
    doc['recognizer']['settings']['hold']=float('nan')
    with pytest.raises(ValueError):RuntimePolicy(doc)


def test_old_history_reports_line_and_does_not_replace_loaded_registry():
    rows=[{'record_type':'plan_created','plan_id':'old','version':1}]
    result=inspect_records(rows)
    assert not result['structurally_recoverable']
    assert 'items' in result['issues'][0]['missing']
    store=PlanStore();store.create_plan('existing',[])
    with pytest.raises(ValueError,match='行1'):store.restore(rows)
    assert 'existing' in store.plans
