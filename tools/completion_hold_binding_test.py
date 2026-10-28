"""Actual Slicer + staged hand hold, with an edit injected mid-confirmation."""
import argparse,json,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient
from op_controller import OperationController
from gesture_fsm import Shape,classify_shape
from motion_engine import Point


def run(out):
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'));assert ready['port']!=18944
    poses=json.loads((ROOT/'work/illustrated-gesture-replay-input.json').read_text(encoding='utf-8'))
    client=SlicerSessionClient(port=ready['port']);client.runtime_manifest=ready['runtime_manifest'];client.connect()
    class Clock:
        t=100.
        def __call__(self):return self.t
    clock=Clock();ops=OperationController(client,now=clock,panel_menu=True)
    def api(cmd,params=None):
        result=client.send(cmd,params);assert result.get('ok'),(cmd,result);return result
    def count():
        path=out/'events.jsonl';return len(path.read_text(encoding='utf-8').splitlines()) if path.exists() else 0
    def feed(name,seconds):
        if name:
            points=poses['poses'][name][0]['points'];lm={int(k):Point(*v) for k,v in points.items()};shape=classify_shape(lm,.055,.45)
        else:shape,lm=Shape.NONE,None
        for _ in range(round(seconds/.05)):ops.update(shape,lm);clock.t+=.05
    def gesture(name):feed(None,1);feed(name,.6)
    def confirmation():
        if not ops.panel_menu.opened:gesture('thumb')
        keys=[entry.key for entry in ops.panel_menu.entries]
        assert 'confirm' in keys,(ops.panel_menu.page,keys)
        for _ in range((keys.index('confirm')-ops.panel_menu.index)%len(keys)):gesture('two')
        gesture('three');assert ops.panel_menu.page=='confirm'
    initial=count()
    try:
        if client.last_state.get('draft'):
            api('arm');api('cancel')
        api('disarm');feed('open_palm',2);feed(None,1)
        api('select_mode',{'mode':'aim'});api('aim',{'nx':.5,'ny':.5});api('stamp')
        for _ in range(40):
            if ops._send('status')['result'].get('displayed'):break
            time.sleep(.05)
        confirmation();feed('three',2)
        assert count()==initial,'same hold committed after opening confirmation'
        feed(None,1);feed('three',.15)
        api('select_mode',{'mode':'rotate'});api('rotate_opening',{'delta_deg':15});ops._send('status')
        feed('three',1)
        assert count()==initial,'mid-hold revision change committed'
        assert ops.panel_menu.notice,'stale confirmation did not explain rejection'
        for _ in range(40):
            if ops._send('status')['result'].get('displayed'):break
            time.sleep(.05)
        else:raise AssertionError('new revision renderer ACK did not arrive')
        gesture('fist');confirmation();gesture('three')
        assert count()==initial+1,'fresh independent confirmation did not save exactly once'
        result={'passed':True,'same_hold_saved':0,'mid_hold_changed_revision_saved':0,'fresh_confirmation_saved':1}
    except Exception:result={'passed':False,'error':traceback.format_exc(),'notice':ops.panel_menu.notice}
    finally:client.send('disarm');client.close()
    result.update(real_hand_verified=False,input='reclassified synthetic landmarks; real TCP/renderer; edit injected through setup API')
    with (out/'hold-binding-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    result=run(args.out);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['passed'] else 1)
