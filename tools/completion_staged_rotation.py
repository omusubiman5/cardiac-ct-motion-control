"""Timed C opening rotation/restore through reclassified landmarks and real Slicer."""
import argparse,json,math,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient
from op_controller import OperationController
from gesture_fsm import Shape,classify_shape
from motion_engine import Point


def run(out,duration):
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'));assert ready['port']!=18944
    source=json.loads((ROOT/'work/illustrated-gesture-replay-input.json').read_text(encoding='utf-8'))
    records=[];cycles=[];phase=['setup'];frame_id=[0]
    class Client(SlicerSessionClient):
        def send(self,cmd,params=None):
            started=time.perf_counter();response=super().send(cmd,params)
            records.append({'phase':phase[0],'cmd':cmd,'expected_ok':True,'response':response,
                            'latency_ms':(time.perf_counter()-started)*1000,'trace':self.last_trace})
            if not response.get('ok'):raise RuntimeError(str((cmd,response)))
            return response
    client=Client(port=ready['port']);client.runtime_manifest=ready['runtime_manifest'];client.connect()
    ops=OperationController(client,panel_menu=True)
    def frame(item):
        acquired=time.perf_counter_ns();frame_id[0]+=1
        if item:
            landmarks={int(k):Point(*v) for k,v in item['points'].items()};shape=classify_shape(landmarks,.055,.45)
            assert shape.value==item['shape'],shape
        else:shape,landmarks=Shape.NONE,None
        client.trace_context={'frame_id':frame_id[0],'acquired_ns':acquired,
                              'recognized_ns':time.perf_counter_ns(),'gate_ns':time.perf_counter_ns()}
        ops.update(shape,landmarks);time.sleep(.05)
    def pose(name,seconds=.6):
        for _ in range(round(seconds/.05)):frame(source['poses'][name][0] if name else None)
    def gesture(name):pose(None,1);pose(name)
    def shown():
        for _ in range(60):
            value=ops._send('status')['result'].get('displayed')
            if value:return value
            time.sleep(.05)
        raise RuntimeError('renderer ACK missing')
    started=time.monotonic()
    try:
        ops._send('arm');ops._send('select_mode',{'mode':'aim'});ops._send('aim',{'nx':.5,'ny':.5});ops._send('stamp')
        baseline=shown();gesture('thumb');gesture('two');gesture('three')
        assert ops.mode=='rotate' and not ops.panel_menu.opened
        started=time.monotonic()
        while time.monotonic()-started<duration:
            phase[0]='forward opening rotation';pose(None,1)
            for item in source['horizontal_movement']:frame(item)
            forward=shown()
            phase[0]='reverse opening input; observe deadzone residual';pose(None,1)
            for item in reversed(source['horizontal_movement']):frame(item)
            reverse=shown()
            # Reversing a sampled hand path may leave a sub-deadzone residual.
            # Use the actual independent hand-menu reset, rather than loosening tolerance.
            phase[0]='explicit hand-menu direction reset';gesture('thumb')
            keys=[entry.key for entry in ops.panel_menu.entries]
            for _ in range((keys.index('reset_dir')-ops.panel_menu.index)%len(keys)):gesture('two')
            gesture('three')
            restored=shown()
            base=baseline['placement'];current=restored['placement']
            assert baseline['draft_id']==restored['draft_id']
            assert base['anchor']==current['anchor'] and base['plane']==current['plane']
            assert math.isclose(base['in_plane_angle'],current['in_plane_angle'],abs_tol=1e-8)
            assert baseline['template']==restored['template']
            assert not math.isclose(base['in_plane_angle'],forward['placement']['in_plane_angle'],abs_tol=1e-8)
            cycles.append({'elapsed_s':time.monotonic()-started,'angle_restored':True,'center_plane_size_unchanged':True,
                           'forward_angle':forward['placement']['in_plane_angle'],
                           'reverse_residual_angle':reverse['placement']['in_plane_angle'],
                           'restored_angle':current['in_plane_angle'],'restoration':'independent hand-menu reset_dir'})
            (out/'rotation-progress.json').write_text(json.dumps({'elapsed_s':time.monotonic()-started,'required_s':duration,'cycles':len(cycles)}),encoding='utf-8')
        result={'passed':True}
    except (Exception,KeyboardInterrupt):result={'passed':False,'error':traceback.format_exc()}
    finally:
        try:
            phase[0]='cleanup';client.send('disarm')
        except Exception as error:
            result['cleanup_error']=str(error)
        finally:client.close()
    result.update(duration_s=time.monotonic()-started,required_duration_s=duration,cycles=cycles,records=records,
                  real_hand_verified=False,input='generated-image-derived landmark replay; actual Slicer C opening rotation/restore; camera gates excluded')
    with (out/'rotation-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return {k:v for k,v in result.items() if k not in {'records','cycles'}}|{'cycles':len(cycles)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);parser.add_argument('--duration',type=float,default=600)
    args=parser.parse_args();result=run(args.out,args.duration);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['passed'] else 1)
