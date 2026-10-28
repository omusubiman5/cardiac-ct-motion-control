import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('completion_analysis',Path(__file__).resolve().parents[1]/'analyze_completion_test.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_missing_clock_or_frame_cannot_be_reported_as_e2e_latency():
    records=[{'trace':{'req':'r','server':{'last_render':{'req':'r','acknowledged_ns':100}}}}]
    metrics=module.stage_metrics(records)
    assert metrics['end_to_end_bounds']==[]
    assert metrics['unmeasurable'][0]['reason']


def test_per_request_clock_bounds_and_asynchronous_ack_association():
    source={'trace':{'req':'edit','frame':{'acquired_ns':1000000}}}
    poll={'trace':{'req':'status','clock_offset_interval_ns':[100000,200000],
                   'server':{'last_render':{'req':'edit','acknowledged_ns':2200000}}}}
    samples=module.stage_metrics([source,poll,poll])['end_to_end_bounds']
    assert len(samples)==1
    assert samples[0]['minimum_ms']==1.0 and samples[0]['maximum_ms']==1.1


def test_incomplete_intent_and_short_trial_are_not_long_term_acceptance():
    result=module.summarize({'records':[{'response':{'ok':True}}],'duration_s':1})
    assert result['wrong_accepted_per_hour'] is None
    assert not result['long_trial_completed'] and not result['real_hand_verified']


def test_condition_totals_exclude_unknown_intent_and_invalid_recovery_clock():
    condition={'shape':'fist','side':'left'}
    result=module.summarize({'records':[
        {'condition':condition,'expected_ok':False,'response':{'ok':True}},
        {'condition':condition,'response':{'ok':False}}],
        'transitions':[{'kind':'stop','clock':'one-process','start_ns':200,'end_ns':100}]})
    group=result['condition_groups'][0]
    assert (group['trials'],group['annotated'],group['wrong_accepted'])==(2,1,1)
    assert result['transitions'][0]['duration_ms'] is None


def test_same_clock_substages_do_not_need_cross_process_subtraction():
    result=module.stage_metrics([{'trace':{'req':'r','sent_ns':1500000,
        'frame':{'acquired_ns':1000000,'recognized_ns':1200000,'gate_ns':1300000},
        'server':{'received_ns':5000000,'accepted_ns':6000000}}}])
    intervals={r['stage']:r['ms'] for r in result['same_clock_intervals']}
    assert intervals=={'acquisition_to_recognition':.2,'recognition_to_gate':.1,
                       'gate_to_send':.2,'server_receive_to_accept':1.0}
