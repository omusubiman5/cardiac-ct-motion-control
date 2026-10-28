"""Actual VTK geometry/transform change must be rejected BEFORE C mutation."""
import argparse,json,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient


def run(out):
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'));assert ready['port']!=18944
    client=SlicerSessionClient(port=ready['port']);client.runtime_manifest=ready['runtime_manifest'];records=[]
    def send(cmd,params=None,ok=True):
        response=client.send(cmd,params);records.append({'cmd':cmd,'expected_ok':ok,'response':response})
        assert response.get('ok') is ok,(cmd,response);return response
    def fault(kind):
        value={'id':uuid.uuid4().hex,'kind':kind};temporary=out/'fault-control.tmp'
        temporary.write_text(json.dumps(value));temporary.replace(out/'fault-control.json')
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            path=out/'fault-ack.json'
            if path.exists() and json.loads(path.read_text()).get('id')==value['id']:return
            time.sleep(.03)
        raise AssertionError('fault not acknowledged')
    send('arm');send('select_mode',{'mode':'aim'});send('aim',{'nx':.5,'ny':.5});send('stamp')
    for _ in range(40):
        before=send('status')['result']
        if before.get('displayed'):break
        time.sleep(.05)
    revision=before['rev'];send('select_mode',{'mode':'rotate'})
    results=[]
    try:
        for kind in ('model-shape-change','model-transform-change','model-remove'):
            fault(kind);send('rotate_opening',{'delta_deg':15},False)
            state=send('status')
            assert state['result']['rev']==revision and state['result'].get('displayed') is None
            assert state['state']['armed'] is False
            results.append({'fault':kind,'revision_unchanged':True,'armed':False,'display_ack_invalidated':True})
            fault('restore');send('arm');send('resume_draft')
        result={'passed':True,'conditions':results,'records':records,'real_hand_verified':False}
        with (out/'target-change-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
        return {k:v for k,v in result.items() if k!='records'}
    finally:
        fault('restore');client.send('disarm');client.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args();print(json.dumps(run(args.out)))
