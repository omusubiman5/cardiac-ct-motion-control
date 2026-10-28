"""Actual isolated Slicer process termination immediately before/after ledger replace."""
import argparse,hashlib,json,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'prototypes/cmos-motion-poc'),str(ROOT/'prototypes/slicer-cstamp')]
from session_client import SlicerSessionClient
from cstamp.ledger import EventLedger

def run(out,phase,stage):
    out=out.resolve()
    if not out.is_relative_to(ROOT/'work'):raise ValueError('project isolated output required')
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'))
    if ready['port']==18944:raise ValueError('normal endpoint forbidden')
    client=SlicerSessionClient(port=ready['port'],timeout=1);client.runtime_manifest=ready['runtime_manifest']
    path=out/'events.jsonl'
    def send(cmd,params=None):
        response=client.send(cmd,params);assert response['ok'],(cmd,response);return response
    def draft():
        send('select_mode',{'mode':'aim'});send('aim',{'nx':.5,'ny':.5});send('stamp')
        for _ in range(40):
            displayed=send('status')['result'].get('displayed')
            if displayed:return {k:displayed[k] for k in ('draft_id','rev','hash')}
            time.sleep(.05)
        raise AssertionError('renderer ACK missing')
    try:
        if stage=='inject':
            if (out/'crash-request.json').exists():raise FileExistsError('use a new crash run')
            send('arm');send('commit',draft())
            before=path.read_bytes();proof=draft()
            value={'id':uuid.uuid4().hex,'kind':'crash-'+phase+'-replace'}
            temporary=out/'fault-control.tmp';temporary.write_text(json.dumps(value));temporary.replace(out/'fault-control.json')
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                ack=out/'fault-ack.json'
                if ack.exists() and json.loads(ack.read_text()).get('id')==value['id']:break
                time.sleep(.03)
            else:raise AssertionError('crash hook not acknowledged')
            response=client.send('commit',proof)
            request=client.last_request
            deadline=time.monotonic()+3
            while not (out/'crash-stage.json').exists() and time.monotonic()<deadline:time.sleep(.03)
            actual=json.loads((out/'crash-stage.json').read_text(encoding='utf-8'))
            assert actual['request_id']==request and actual['pid']==ready['pid']
            stored=EventLedger(path);events=stored.events()
            assert len(events)==(1 if phase=='before' else 2)
            if phase=='before':assert path.read_bytes()==before and stored.request_result(request) is None
            else:assert stored.request_result(request) is not None
            result={'phase':phase,'terminated_slicer_pid':ready['pid'],'req':request,
                'baseline_sha256':hashlib.sha256(before).hexdigest(),'ledger_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'events_after_process_termination':len(events),'no_partial_json':True,'response':response,'actual_stage':actual}
            with (out/'crash-request.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
            return {'phase':phase,'injection_observed':True,'terminated_slicer_pid':ready['pid'],'stored_events':len(events)}
        previous=json.loads((out/'crash-request.json').read_text(encoding='utf-8'))
        assert previous['terminated_slicer_pid']!=ready['pid'],'a separate actual Slicer restart is required'
        response=client.send('query_result',{'req':previous['req']})
        assert response['ok'] is (phase=='after'),response
        assert response['state']['armed'] is False
        send('arm');loaded=send('load_session')
        assert loaded['result']['restored']==(1 if phase=='before' else 2)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==previous['ledger_sha256']
        result={'passed':True,'phase':phase,'original_pid':previous['terminated_slicer_pid'],'restarted_pid':ready['pid'],
                'restored_events':loaded['result']['restored'],'persisted_result_found':response['ok'],
                'ledger_unchanged_on_reload':True,'real_hand_verified':False,
                'kind':'self-verification; actual Slicer/Qt process termination at atomic persistence stage and actual GUI restart'}
        send('disarm')
        with (out/'slicer-crash-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
        return result
    finally:client.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);parser.add_argument('--phase',choices=['before','after'],required=True)
    parser.add_argument('--stage',choices=['inject','verify'],required=True);args=parser.parse_args()
    print(json.dumps(run(args.out,args.phase,args.stage),ensure_ascii=False))
