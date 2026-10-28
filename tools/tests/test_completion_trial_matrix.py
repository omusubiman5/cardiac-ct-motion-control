"""Pending test preparation only; these tests do not supply real-hand results."""
import importlib.util
import itertools
import json
import subprocess
import sys
from pathlib import Path


SCRIPT=Path(__file__).resolve().parents[1]/'create_completion_trial_matrix.py'
spec=importlib.util.spec_from_file_location('completion_trial_matrix',SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_original_hv_and_clear_shape_conditions_are_preserved_exactly():
    value=module.matrix()
    assert {row['case'] for row in value['cases']} == (
        {f'H-{i:02}' for i in range(1,13)} | {f'V-{i:02}' for i in range(1,11)})
    expected=[]
    for shape,side,distance,tilt,attempt in itertools.product(
            ('open_palm','thumb','point','two','three','fist'),('left','right'),
            ('distance1','distance2'),('tilt1','tilt2'),range(1,11)):
        expected.append({'case':'V-05','shape':shape,'side':side,'distance_condition':distance,
                         'tilt_condition':tilt,'attempt':attempt,'expected_intent':None,
                         'status':'NOT RUN','actual_response':None})
    assert value['v05_clear_shape_trials']==expected
    assert len(expected)==480


def test_thumb_down_covers_user_orientation_both_hands_distance_and_tilt_without_c_actions():
    rows=module.matrix()['v05_supplementary_clear_shape_trials']
    assert len(rows)==80
    assert {(r['side'],r['distance_condition'],r['tilt_condition'],r['attempt']) for r in rows} == set(
        itertools.product(('left','right'),('distance1','distance2'),('tilt1','tilt2'),range(1,11)))
    for row in rows:
        assert row['standard_category']=='Thumb_Down' and row['shape']=='thumb_down'
        assert row['wrist_orientation']=='③：手首が画面の横側'
        assert row['expected_menu_delta']==1 and row['expected_slicer_operation_count']==0
        assert row['supplementary'] is True


def test_transition_unknown_exit_reentry_and_direction_intents_are_explicit():
    rows=module.matrix()['v05_transition_unknown_trials']
    scenarios={r['scenario'] for r in rows}
    assert {'point-to-two','two-to-three','fist-to-thumb-up','open-palm-to-thumb-up',
            'fist-to-pinch','unknown-half-folded','unknown-partial-hand','short-hand-exit',
            'released-hand-reentry','thumb-up-down-roundtrip','thumb-down-outside-menu',
            'fist-hold-back'} == scenarios
    for scenario in scenarios:
        selected=[r for r in rows if r['scenario']==scenario]
        assert {(r['side'],r['attempt']) for r in selected} == set(
            itertools.product(('left','right'),range(1,11)))
        assert all(r['precondition'] and r['steps'] and r['expectation'] for r in selected)
    assert all('補助条件' in r['repetition_basis'] and r['supplementary'] for r in rows)
    roundtrip=next(r for r in rows if r['scenario']=='thumb-up-down-roundtrip')
    assert '上→下→下→上' in roundtrip['expectation']
    assert '最終選択は開始位置と同じ' in roundtrip['expectation']


def test_no_generated_trial_claims_execution_and_guides_exist():
    value=module.matrix()
    rows=(value['cases']+value['v05_clear_shape_trials']+
          value['v05_supplementary_clear_shape_trials']+value['v05_transition_unknown_trials']+
          value['v07_long_trials'])
    assert all(r['status']=='NOT RUN' for r in rows)
    assert not any(r.get('real_hand_verified',False) for r in rows)
    assert all(r.get('actual_response') is None and not r.get('observations') for r in rows)
    assert value['preparation']['actual_started_at'] is None
    assert all(v is None for v in value['preparation']['condition_measurements'].values())
    assert value['operator_feedback']['accepted_by_user'] is False
    additional=value['v05_supplementary_clear_shape_trials']+value['v05_transition_unknown_trials']
    assert len({r['trial_id'] for r in additional})==len(additional)
    assert all((module.ROOT/p).is_file() for p in value['preparation']['guides'])


def test_cli_writes_new_pending_matrix_but_preserves_existing_evidence(tmp_path):
    path=tmp_path/'matrix.json'
    result=subprocess.run([sys.executable,str(SCRIPT),str(path)],capture_output=True,text=True)
    assert result.returncode==0, result.stderr
    value=json.loads(path.read_text(encoding='utf-8'))
    assert len(value['v05_clear_shape_trials'])==480
    before=path.read_bytes()
    repeated=subprocess.run([sys.executable,str(SCRIPT),str(path)],capture_output=True,text=True)
    assert repeated.returncode!=0 and path.read_bytes()==before
