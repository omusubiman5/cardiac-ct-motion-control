"""Fault injection in actual isolated Slicer. Synthetic API self-verification."""
import argparse
import hashlib
import json
import sys
import time
import traceback
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient


def run(out):
    if (out/'fault-results.json').exists():raise FileExistsError('use a new run')
    ready=json.loads((out/'ready.json').read_text());assert ready['port']!=18944
    client=SlicerSessionClient(port=ready['port']);client.runtime_manifest=ready['runtime_manifest'];records=[]
    def send(cmd,params=None,expected=True):
        response=client.send(cmd,params);records.append({'cmd':cmd,'response':response,'expected_ok':expected})
        assert response.get('ok') is expected,(cmd,response)
        return response
    def fault(kind):
        value={'id':uuid.uuid4().hex,'kind':kind};path=out/'fault-control.json'
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value));temporary.replace(path)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            if (out/'fault-ack.json').exists() and json.loads((out/'fault-ack.json').read_text()).get('id')==value['id']:return
            time.sleep(.03)
        raise AssertionError('fault was not acknowledged')
    def digest():
        path=out/'events.jsonl';return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    def shown():
        for _ in range(40):
            proof=send('status')['result'].get('displayed')
            if proof:return {key:proof[key] for key in ('draft_id','rev','hash')}
            time.sleep(.05)
        raise AssertionError('ACK missing')
    try:
        send('arm');send('select_mode',{'mode':'aim'});send('aim',{'nx':.5,'ny':.5})
        fault('render-hold');before=digest();stamp=send('stamp');state=send('status')['result']
        assert state.get('displayed') is None
        send('commit',{'draft_id':stamp['draft_id'],'rev':state['rev'],'hash':'0'*64},False)
        assert digest()==before
        fault('restore');proof=shown();fault('save-failure');send('commit',proof,False)
        assert digest()==before and send('status')['state']['draft']
        fault('restore');fault('drop-commit-response')
        send('commit',proof,False);request=client.last_request
        fault('restore');result=send('query_result',{'req':request})
        event=result['result']['response']['event_id'];send('query_result',{'req':request})
        rows=[json.loads(line) for line in (out/'events.jsonl').read_text().splitlines()]
        assert len([row for row in rows if row.get('event_id')==event])==1
        assert send('status')['state']['armed'] is False
        send('arm');send('commit',proof,False)
        assert len((out/'events.jsonl').read_text().splitlines())==len(rows)
        result={'passed':True,'saved_req':request,'event_id':event,'saved_once':True}
    except Exception:result={'passed':False,'error':traceback.format_exc()}
    finally:
        fault('restore');client.send('disarm');client.close()
    result.update(records=records,real_hand_verified=False,input='synthetic API in real isolated Slicer')
    with (out/'fault-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return {k:v for k,v in result.items() if k!='records'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    result=run(args.out);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['passed'] else 1)
