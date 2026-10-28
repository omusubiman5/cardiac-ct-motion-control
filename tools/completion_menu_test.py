"""Classify previously generated synthetic landmarks, then navigate real hand menus.

Real Slicer TCP and renderer; NOT physical camera, live neural inference, or real hand acceptance.
"""
import argparse
import json
import sys
import traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient
from op_controller import OperationController
from gesture_fsm import Shape,classify_shape
from motion_engine import Point


def run(out):
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'))
    assert ready['port']!=18944
    poses=json.loads((ROOT/'work/illustrated-gesture-replay-input.json').read_text(encoding='utf-8'))
    records=[];phase=['setup']
    class Client(SlicerSessionClient):
        def send(self,cmd,params=None):
            response=super().send(cmd,params)
            records.append({'phase':phase[0],'cmd':cmd,'response':response})
            return response
    client=Client(port=ready['port'],timeout=3);client.runtime_manifest=ready['runtime_manifest'];client.connect()
    class Clock:
        t=100.0
        def __call__(self):return self.t
    clock=Clock();ops=OperationController(client,now=clock,panel_menu=True)
    def feed(name,seconds=.6):
        if name is None:
            shape,lm=Shape.NONE,None
        else:
            source=poses['poses'][name][0]
            lm={int(k):Point(*v) for k,v in source['points'].items()}
            shape=classify_shape(lm,.055,.45)
            assert shape.value==source['shape'],(name,shape)
        for _ in range(round(seconds/.05)):
            ops.update(shape,lm);clock.t+=.05
    def gesture(name):feed(None,1);feed(name);feed(None,1)
    def entry(key):
        keys=[e.key for e in ops.panel_menu.entries]
        assert key in keys,(key,keys)
        index=keys.index(key)
        for _ in range((index-ops.panel_menu.index)%len(keys)):gesture('two')
        gesture('three')
        assert not ops.panel_menu.notice.startswith('拒否'),ops.panel_menu.notice
    def path(*keys):
        for _ in range(5):
            if not ops.panel_menu.opened:break
            gesture('fist')
        gesture('thumb')
        assert ops.panel_menu.opened,'thumb did not open the real controller menu'
        if ops.panel_menu.page=='edit' and keys[0]=='records':entry('main')
        for key in keys:entry(key)
    def api(cmd,params=None):
        if cmd in {'add_plan_item','begin_plan_revision'}:
            params={**(params or {}),'plan_revision':client.send('status')['result']['plan_revision']}
        response=client.send(cmd,params);assert response.get('ok'),(cmd,response)
        return response
    def stamp():
        api('select_mode',{'mode':'aim'});api('aim',{'nx':.5,'ny':.5});api('stamp')
        for _ in range(40):
            response=ops._send('status')
            if response.get('result',{}).get('displayed'):return
            __import__('time').sleep(.05)
        raise AssertionError('renderer ACK missing')
    visited=[]
    try:
        if client.last_state.get('draft'):api('arm');api('cancel')
        api('disarm');phase[0]='synthetic hand start';feed('open_palm',2);feed(None,1)
        assert ops.armed and not ops.preparing
        phase[0]='setup';stamp()
        for key in ('reverse','reset_dir'):
            phase[0]=key;path(key);visited.append(key)
        phase[0]='setup';api('cancel');api('select_mode',{'mode':'view'});api('create_plan')
        phase[0]='add_plan_item';path('records','add_plan_item');visited.append('add_plan_item')
        phase[0]='setup';api('aim',{'nx':.5,'ny':.5});api('stamp')
        for _ in range(40):
            if ops._send('status').get('result',{}).get('displayed'):break
            __import__('time').sleep(.05)
        phase[0]='hand confirm';path('confirm','commit')
        # A second working item makes movement observable, rather than testing a no-op.
        phase[0]='setup';api('add_plan_item');stamp()
        path('confirm','commit')
        path('records','reasons','reason:operator')
        path('records','save_plan_revision');path('records','load_plan')
        api('begin_plan_revision',{'plan_revision':ops._send('status')['result']['plan_revision']})
        phase[0]='select_plan_item';path('records','plan_items','choose:plan_items:0');visited.append('select_plan_item')
        phase[0]='edit_plan_item';path('records','edit_plan_item');visited.append('edit_plan_item')
        phase[0]='setup';api('select_mode',{'mode':'rotate'});api('rotate_opening',{'delta_deg':15})
        for _ in range(40):
            if ops._send('status').get('result',{}).get('displayed'):break
            __import__('time').sleep(.05)
        path('confirm','commit')
        path('records','plan_items','choose:plan_items:0')
        path('records','reasons','reason:operator')
        phase[0]='move_plan_item';path('records','move_plan_item');visited.append('move_plan_item')
        phase[0]='setup';path('records','reasons','reason:plan_superseded')
        phase[0]='delete_plan_item';path('records','delete_plan_item');visited.append('delete_plan_item')
        phase[0]='setup';path('records','confirm_audit')
        phase[0]='setup';path('records','reasons','reason:operator')
        phase[0]='save_plan_revision';path('records','save_plan_revision')
        phase[0]='setup';path('records','load_plan')
        # Reorder requires an existing next item; prepare it through the actual plan APIs.
        api('begin_plan_revision',{'plan_revision':ops._send('status')['result']['plan_revision']})
        api('add_plan_item');stamp()
        proof=ops.status_details['displayed'];api('commit',{k:proof[k] for k in ('draft_id','rev','hash')})
        path('records','reasons','reason:operator');path('records','save_plan_revision');path('records','load_plan')
        path('records','plan_items','choose:plan_items:0');path('records','reasons','reason:operator')
        phase[0]='reorder_plan';path('records','reorder_plan');visited.append('reorder_plan')
        phase[0]='save_session';path('records','save_session');visited.append('save_session')
        phase[0]='query_result';path('records','query_result');visited.append('query_result')
        result={'passed':True}
    except Exception:
        result={'passed':False,'error':traceback.format_exc(),'page':ops.panel_menu.page,'notice':ops.panel_menu.notice}
    finally:
        client.send('disarm');client.close()
    result.update(visited=visited,records=records,real_hand_verified=False,
                  input='historical generated-image-derived landmarks reclassified; controller menu navigation; camera gates excluded')
    with (out/'menu-results.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    return {k:v for k,v in result.items() if k!='records'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);args=p.parse_args()
    result=run(args.out);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['passed'] else 1)
