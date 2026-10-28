"""Observe real Pixel/normal UI metadata only. No TCP, image storage or control."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from ui_bridge import MemoryChannel


def run(out,duration):
    out=out.resolve()
    if not out.is_relative_to(ROOT/'work'):raise ValueError('project work output required')
    out.mkdir(parents=True,exist_ok=False)
    channel=MemoryChannel('state');records=[];started=time.monotonic();next_progress=started
    try:
        while time.monotonic()-started<duration:
            value=channel.read();initial_read_missing=value is None;retries=0
            # A seqlock reader can meet an in-progress write. Preserve that fact,
            # then acquire a new validated snapshot; never reuse an old state.
            while value is None and retries<3:
                time.sleep(.001);retries+=1;value=channel.read()
            readable=value is not None
            value=value or {};age=time.time()-value.get('ts',0)
            # Whitelist excludes preview bytes and arbitrary payloads.
            records.append({'elapsed_s':time.monotonic()-started,'fresh':0<=age<2,
                'published_ts':value.get('ts'),'observed_ts':time.time(),'age_s':age,
                'initial_read_missing':initial_read_missing,'read_retries':retries,'readable':readable,
                'connected':value.get('connected') is True,'armed':value.get('armed') is True,
                'shape':value.get('shape'),'mode':value.get('mode'),
                'generation':value.get('input',{}).get('generation'),
                'transport_drops':value.get('input',{}).get('transport_drops'),
                'roundtrip_ms':value.get('input',{}).get('roundtrip_ms'),
                'capture_ms':value.get('input',{}).get('capture_ms'),
                'inference_ms':value.get('input',{}).get('inference_ms'),'fps':value.get('input',{}).get('fps')})
            if time.monotonic()>=next_progress:
                (out/'progress.json').write_text(json.dumps({'elapsed_s':time.monotonic()-started,'required_s':duration,'samples':len(records)}),encoding='utf-8')
                next_progress=time.monotonic()+5
            time.sleep(.2)
    finally:channel.close()
    stopped=all(not row['armed'] for row in records)
    result={'connection_passed':bool(records) and all(r['fresh'] and r['connected'] for r in records),
            'stopped_condition_maintained':stopped,'duration_s':time.monotonic()-started,
            'required_duration_s':duration,'records':records,
            'scope':'real camera/normal application connection observation; no instructed hand trials or operator intent labels',
            'real_hand_acceptance_verified':False,'camera_image_saved':False,'second_tcp_session_opened':False}
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:v for k,v in result.items() if k!='records'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);parser.add_argument('--duration',type=float,default=600)
    args=parser.parse_args();result=run(args.out,args.duration);print(json.dumps(result));sys.exit(0 if result['connection_passed'] else 1)
