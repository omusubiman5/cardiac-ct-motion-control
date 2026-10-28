"""Summarize metadata-only trials; never infer operator intent from accepted commands."""
import argparse
import json
import math
from pathlib import Path


def stage_metrics(records):
    by_req={r.get('trace',{}).get('req'):r.get('trace',{}) for r in records if isinstance(r.get('trace'),dict)}
    samples=[];seen=set();missing=[]
    for row in records:
        trace=row.get('trace') or {}
        if not isinstance(trace,dict):continue
        server=trace.get('server') or {}
        for stage,key in (('render','last_render'),('save','last_save')):
            event=server.get(key)
            if not isinstance(event,dict):continue
            moment=event.get('acknowledged_ns' if stage=='render' else 'persisted_ns')
            identity=(stage,event.get('req'),moment)
            if identity in seen:continue
            seen.add(identity)
            source=by_req.get(event.get('req')) or {}
            frame=source.get('frame') or {}
            acquired=frame.get('acquired_ns');offset=trace.get('clock_offset_interval_ns')
            if type(moment) is not int or type(acquired) is not int or not isinstance(offset,list) or len(offset)!=2 or any(type(v) is not int for v in offset):
                missing.append({'stage':stage,'req':event.get('req'),'reason':'frame timestamp or calibrated clock interval missing'})
                continue
            lower=(moment-offset[1]-acquired)/1e6;upper=(moment-offset[0]-acquired)/1e6
            if upper<0 or lower>upper:
                missing.append({'stage':stage,'req':event.get('req'),'reason':'clock/order inconsistent'});continue
            samples.append({'stage':stage,'req':event.get('req'),'minimum_ms':max(0,lower),'maximum_ms':upper})
    local=[]
    for row in records:
        trace=row.get('trace') or {};frame=trace.get('frame') or {};server=trace.get('server') or {}
        for name,source,start,end in [('acquisition_to_recognition',frame,'acquired_ns','recognized_ns'),
                                      ('recognition_to_gate',frame,'recognized_ns','gate_ns'),
                                      ('gate_to_send',{**frame,**trace},'gate_ns','sent_ns'),
                                      ('server_receive_to_accept',server,'received_ns','accepted_ns')]:
            a,b=source.get(start),source.get(end)
            if type(a)is int and type(b)is int and b>=a:
                local.append({'stage':name,'req':trace.get('req'),'ms':(b-a)/1e6})
    return {'end_to_end_bounds':samples,'same_clock_intervals':local,'unmeasurable':missing,
            'clock_method':'per-response offset interval; uncalibrated timestamps are excluded'}


def summarize(trial):
    records=trial.get('records',[])
    latency=sorted(float(r['latency_ms']) for r in records if isinstance(r.get('latency_ms'),(int,float)) and math.isfinite(r['latency_ms']))
    annotated=[r for r in records if isinstance(r.get('expected_ok'),bool)]
    wrong=sum(r['expected_ok'] is False and r.get('response',{}).get('ok') is True for r in annotated)
    duration=trial.get('duration_s')
    complete=bool(records) and len(annotated)==len(records) and isinstance(duration,(int,float)) and duration>0
    groups={}
    for row in records:
        condition=row.get('condition')
        if not isinstance(condition,dict):continue
        key=json.dumps(condition,ensure_ascii=False,sort_keys=True)
        group=groups.setdefault(key,{'condition':condition,'trials':0,'annotated':0,'matched':0,'wrong_accepted':0})
        group['trials']+=1
        if isinstance(row.get('expected_ok'),bool):
            group['annotated']+=1
            group['matched']+=row.get('response',{}).get('ok') is row['expected_ok']
            group['wrong_accepted']+=row['expected_ok'] is False and row.get('response',{}).get('ok') is True
    transitions=[]
    for event in trial.get('transitions',[]):
        value={'kind':event.get('kind'),'clock':event.get('clock'),'duration_ms':None}
        a,b=event.get('start_ns'),event.get('end_ns')
        if event.get('clock') and type(a)is int and type(b)is int and b>=a:value['duration_ms']=(b-a)/1e6
        else:value['reason']='same-clock ordered transition timestamps missing'
        transitions.append(value)
    return {'kind':'metadata analysis; intent is unknown without explicit trial annotations',
            'commands':len(records),'accepted':sum(r.get('response',{}).get('ok') is True for r in records),
            'rejected':sum(r.get('response',{}).get('ok') is False for r in records),
            'latency_sample_count':len(latency),'latency_p95_ms':latency[max(0,math.ceil(.95*len(latency))-1)] if latency else None,
            'annotated_commands':len(annotated),'wrong_accepted':wrong if annotated else None,
            'wrong_accepted_per_hour':wrong*3600/duration if complete else None,
            'environment':trial.get('environment'), 'restoration_verified':trial.get('restoration_verified'),
            'long_trial_completed':isinstance(duration,(int,float)) and duration>=600,
            'real_hand_verified':trial.get('real_hand_verified') is True,
            'condition_groups':list(groups.values()),'transitions':transitions,
            'stages':stage_metrics(records)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('trial',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(summarize(json.loads(args.trial.read_text(encoding='utf-8'))),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
