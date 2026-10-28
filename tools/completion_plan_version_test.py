"""Select every saved plan version through the hand-menu controller after Slicer restart."""
import argparse,hashlib,json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'prototypes/cmos-motion-poc'),str(ROOT/'prototypes/slicer-cstamp')]
from session_client import SlicerSessionClient
from op_controller import OperationController
from gesture_fsm import Shape,classify_shape
from motion_engine import Point
from cstamp.ledger import EventLedger
from cstamp.plan_revision import PlanStore
from cstamp.contracts import digest

def run(out):
    out=out.resolve()
    if not out.is_relative_to(ROOT/'work'):raise ValueError('isolated fixture required')
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'))
    if ready['port']==18944:raise ValueError('normal endpoint forbidden')
    paths=[out/'plans.jsonl',out/'events.jsonl']
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    store=PlanStore();store.restore(EventLedger(paths[0]).events())
    poses=json.loads((ROOT/'work/illustrated-gesture-replay-input.json').read_text(encoding='utf-8'))
    records=[]
    class Client(SlicerSessionClient):
        def send(self,cmd,params=None):
            response=super().send(cmd,params);records.append({'cmd':cmd,'params':params,'response':response});return response
    client=Client(port=ready['port']);client.runtime_manifest=ready['runtime_manifest'];client.connect()
    class Clock:
        t=100.
        def __call__(self):return self.t
    clock=Clock();ops=OperationController(client,now=clock,panel_menu=True)
    def feed(name,seconds=.6):
        if name:
            value=poses['poses'][name][0];points={int(k):Point(*v) for k,v in value['points'].items()};shape=classify_shape(points,.055,.45)
            assert shape.value==value['shape']
        else:shape,points=Shape.NONE,None
        for _ in range(round(seconds/.05)):ops.update(shape,points);clock.t+=.05
    def gesture(name):feed(None,1);feed(name);feed(None,1)
    def entry(key):
        keys=[e.key for e in ops.panel_menu.entries];assert key in keys,(key,keys)
        for _ in range((keys.index(key)-ops.panel_menu.index)%len(keys)):gesture('two')
        gesture('three');assert not ops.panel_menu.notice.startswith('拒否'),ops.panel_menu.notice
    def path(*keys):
        for _ in range(5):
            if not ops.panel_menu.opened:break
            gesture('fist')
        gesture('thumb')
        for key in keys:entry(key)
    checks=[]
    try:
        feed('open_palm',2);feed(None,1)
        for plan_id,plan in store.plans.items():
            assert client.send('select_plan',{'plan_id':plan_id})['ok']
            for version in plan.versions:
                path('records','plan_versions',f'choose:plan_versions:{version.version-1}')
                selected=client.send('status')['result'];binding=selected['plan_revision']
                assert binding['plan_id']==plan_id and binding['version']==version.version
                assert binding['hash']==digest(version.items),(binding,version)
                assert selected['choices']['plan_items']==[i.get('event_id') or i.get('item_id') for i in version.items]
                assert client.send('load_plan')['result']['planned']==len(version.items)
                if version.version!=plan.current.version:
                    rejected=client.send('begin_plan_revision',{'plan_revision':binding})
                    assert not rejected['ok'] and 'read-only' in rejected['reason']
                    assert client.send('select_mode',{'mode':'aim'})['ok']
                    rejected=client.send('stamp');assert not rejected['ok'] and 'read-only' in rejected['reason']
                checks.append({'plan_id':plan_id,'version':version.version,'items':len(version.items),
                               'saved_hash_matches':True,'historical_read_only':version.version!=plan.current.version})
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};assert before==after
        result={'passed':True,'versions':checks,'original_ledgers_unchanged':True,'pid':ready['pid']}
    except Exception:result={'passed':False,'error':traceback.format_exc(),'versions':checks}
    finally:
        try:client.send('disarm')
        finally:client.close()
    result.update(records=records,real_hand_verified=False,input='reclassified image-derived hand menu; real restarted Slicer; setup API only selects plan ID')
    with (out/'plan-version-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return {k:v for k,v in result.items() if k!='records'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    result=run(args.out);print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
