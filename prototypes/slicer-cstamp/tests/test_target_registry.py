import copy
import pytest
from cstamp.target_registry import TargetRegistry


def fixture():
    row = dict(target_id='synthetic-target', scene_id='synthetic-scene', model_name='surface',
               model_sha256='a'*64, transform_sha256='b'*64, registration_reference='self-test fixture')
    return {'schema_version':1, 'targets':[row]}, {**row,'model_id':'volatile-node-1'}


def test_registration_survives_node_reallocation_without_granting_new_target():
    doc, observed = fixture(); registry = TargetRegistry(doc)
    first = registry.match(observed)
    observed['model_id'] = 'volatile-node-2'
    assert registry.match(observed) == first
    observed['model_sha256'] = 'c'*64
    with pytest.raises(ValueError): registry.match(observed)


def test_registry_is_immutable_and_missing_permission_is_rejected():
    doc, observed = fixture(); registry=TargetRegistry(doc)
    doc['targets'][0]['model_name']='different'
    assert registry.match(observed)['target_id']=='synthetic-target'
    with pytest.raises(ValueError): TargetRegistry({'schema_version':1,'targets':[]}).match(observed)


def test_ambiguous_registration_and_unknown_schema_fail_closed():
    doc, observed=fixture(); duplicate=copy.deepcopy(doc['targets'][0]);duplicate['target_id']='second'
    doc['targets'].append(duplicate)
    with pytest.raises(ValueError): TargetRegistry(doc).match(observed)
    with pytest.raises(ValueError): TargetRegistry({'schema_version':2,'targets':[]})
