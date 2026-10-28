"""Real Qt/Slicer/TCP, synthetic API input. Never describes this as physical hand testing."""
import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient


def run(out):
    if (out/'tcp-results.json').exists():
        raise FileExistsError('use a new run directory; prior test evidence must be preserved')
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'))
    assert ready['port']!=18944
    client=SlicerSessionClient(port=ready['port'],timeout=3)
    client.runtime_manifest=ready['runtime_manifest']
    records=[];started=time.perf_counter()
    def send(cmd,params=None,ok=True):
        t=time.perf_counter();response=client.send(cmd,params)
        records.append({'cmd':cmd,'response':response,'expected_ok':ok,
                        'latency_ms':(time.perf_counter()-t)*1000,'trace':client.last_trace})
        assert response.get('ok') is ok,(cmd,response)
        return response
    def shown():
        for _ in range(40):
            value=send('status')['result'].get('displayed')
            if value:return {k:value[k] for k in ('draft_id','rev','hash')}
            time.sleep(.05)
        raise AssertionError('actual renderer ACK did not arrive')
    try:
        send('arm');send('select_mode',{'mode':'aim'});send('aim',{'nx':.5,'ny':.5});send('stamp')
        proof=shown();send('commit',{**proof,'hash':'wrong'},False)
        send('select_mode',{'mode':'rotate'});send('rotate_opening',{'delta_deg':15});send('commit',proof,False)
        send('select_mode',{'mode':'tilt'});send('tilt',{'delta_deg':10});send('reverse');send('reset_dir')
        saved=send('commit',shown());req=client.last_request;event=saved['event_id']
        client.close();send('query_result',{'req':req});send('arm')
        send('create_plan');send('select_layer',{'layer':'PLANNED'});send('select_mode',{'mode':'aim'})
        send('aim',{'nx':.5,'ny':.5});send('stamp');send('commit',shown())
        state=send('status')['result'];send('select_reason',{'reason':'operator'})
        send('save_plan_revision',{'plan_revision':state['plan_revision']})
        state=send('status')['result'];send('begin_plan_revision',{'plan_revision':state['plan_revision']})
        send('select_plan_item',{'index':0});state=send('status')['result']
        send('select_reason',{'reason':'plan_superseded'})
        send('delete_plan_item',{'plan_revision':state['plan_revision'],'item_id':state['selected_plan_item']})
        audit=send('status')['result']['pending_audit']
        send('confirm_audit',{'audit':{**audit,'item_id':'wrong'}},False);send('confirm_audit',{'audit':audit})
        send('select_mode',{'mode':'review'});send('select_event',{'nx':.5,'ny':.5})
        send('select_reason',{'reason':'operator'});send('revoke_event',{'event_id':event})
        send('confirm_audit',{'audit':send('status')['result']['pending_audit']})
        send('select_layer',{'layer':'PERFORMED'});send('select_mode',{'mode':'aim'})
        send('aim',{'nx':.5,'ny':.5});send('stamp');send('select_mode',{'mode':'rotate'})
        send('recognition_lost');send('rotate_opening',{'delta_deg':5},False)
        send('resume_draft');send('rotate_opening',{'delta_deg':5})
        client.close();send('status');send('rotate_opening',{'delta_deg':5},False)
        # Actual prepared configuration change invalidates an already connected session.
        policy_path=out/'runtime.json';original=policy_path.read_bytes()
        changed=json.loads(original);changed['recognizer']['settings']['changed_for_test']=True
        policy_path.write_text(json.dumps(changed),encoding='utf-8')
        send('arm',ok=False)
        policy_path.write_bytes(original);client.close();send('status');send('arm')
        # A same-named target with a different registration cannot become allowed.
        target_path=out/'targets.json';original=target_path.read_bytes()
        changed=json.loads(original);changed['targets'][0]['model_sha256']='f'*64
        target_path.write_text(json.dumps(changed),encoding='utf-8')
        send('rotate_opening',{'delta_deg':5},False)
        target_path.write_bytes(original)
        result={'passed':True}
    except Exception:
        result={'passed':False,'error':traceback.format_exc()}
    finally:
        client.close()
        result.update(records=records,duration_s=time.perf_counter()-started,real_hand_verified=False,
                      environment={'slicer':'real GUI','input':'synthetic API','port':ready['port'],'source_sha256':ready['source_sha256']})
        (out/'tcp-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:v for k,v in result.items() if k!='records'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    result=run(args.out);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['passed'] else 1)
