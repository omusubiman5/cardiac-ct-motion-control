"""600s timed landmark replay through real controller/TCP. Excludes physical camera gates."""
import argparse,json,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from gesture_fsm import Shape,classify_shape
from motion_engine import Point
from op_controller import OperationController
from session_client import SlicerSessionClient


def run(out,duration):
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'));assert ready['port']!=18944
    poses=json.loads((ROOT/'work/illustrated-gesture-replay-input.json').read_text(encoding='utf-8'))
    records=[];frames=0;started=time.monotonic();phase=['setup']
    class Client(SlicerSessionClient):
        def send(self,cmd,params=None):
            value=super().send(cmd,params)
            expected=cmd in {'status','arm','disarm','select_mode','view_pan','view_rotate','zoom'}
            records.append({'phase':phase[0],'cmd':cmd,'expected_ok':True if expected else None,
                            'response':value,'latency_ms':self.last_roundtrip_ms,'trace':self.last_trace})
            if not expected or not value.get('ok'):raise RuntimeError('unexpected command/rejection: '+str((cmd,value)))
            return value
    client=Client(port=ready['port']);client.runtime_manifest=ready['runtime_manifest']
    ops=OperationController(client,panel_menu=True)
    next_progress=started
    def feed(name,seconds):
        nonlocal frames,next_progress
        deadline=min(started+duration,time.monotonic()+seconds)
        while time.monotonic()<deadline:
            acquired=time.perf_counter_ns()
            if name:
                points=poses['poses'][name][0]['points'];lm={int(k):Point(*v) for k,v in points.items()}
                shape=classify_shape(lm,.055,.45)
                if shape.value!=poses['poses'][name][0]['shape']:raise RuntimeError('fixture classification changed')
            else:shape,lm=Shape.NONE,None
            recognized=time.perf_counter_ns();frames+=1
            client.trace_context={'frame_id':frames,'acquired_ns':acquired,'recognized_ns':recognized,'gate_ns':time.perf_counter_ns()}
            ops.update(shape,lm)
            if time.monotonic()>=next_progress:
                (out/'soak-progress.json').write_text(json.dumps({'elapsed_s':time.monotonic()-started,'required_s':duration,'frames':frames,'phase':phase[0]}))
                next_progress=time.monotonic()+5
            time.sleep(.05)
    try:
        while time.monotonic()-started<duration:
            phase[0]='explicit stopped cycle';ops._send('disarm');feed(None,1)
            for name,seconds in [('open_palm',2),(None,1),('thumb',1),(None,1),('three',1),(None,1),
                                 ('point',1),(None,1),('two',1),(None,1),('fist',1),(None,1)]:
                phase[0]=name or 'release';feed(name,seconds)
            phase[0]='poll';ops._send('status')
        result={'passed':True}
    except (Exception,KeyboardInterrupt):result={'passed':False,'error':traceback.format_exc()}
    finally:
        try:phase[0]='cleanup';client.send('disarm')
        finally:client.close()
    result.update(duration_s=time.monotonic()-started,required_duration_s=duration,frames=frames,records=records,
                  real_hand_verified=False,input='timed generated-image-derived landmark replay; physical camera gates excluded')
    with (out/'soak-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return {k:v for k,v in result.items() if k!='records'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);parser.add_argument('--duration',type=float,default=600)
    args=parser.parse_args();result=run(args.out,args.duration);print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['passed'] else 1)
