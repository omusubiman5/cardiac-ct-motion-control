"""Cooperative normal -> isolated trial -> stopped normal supervisor.

Run after reflecting the current app. Never kills an unknown normal process.
The supplied trial command must own and clean up its isolated Slicer fixture.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'prototypes/cmos-motion-poc'))
from input_lease import InputLease


def run(endpoint, output, command, timeout=900):
    endpoint=endpoint.resolve();output=output.resolve()
    if not endpoint.is_relative_to(ROOT/'work/input-switch') or not output.is_relative_to(ROOT/'work'):
        raise ValueError('endpoint/output must be under project work')
    output.mkdir(parents=True,exist_ok=False)
    normal=json.loads(endpoint.read_text(encoding='utf-8'))
    if normal['phase']!='normal' or normal['port']!=18944:
        raise ValueError('an active normal endpoint on port 18944 is required')
    argv=normal['argv']
    if Path(argv[1]).resolve()!=ROOT/'prototypes/cmos-motion-poc/app.py' or '--slicer-connect' not in argv:
        raise ValueError('restore command is not the exact project recognizer')
    switch=InputLease('trial-supervisor');events=[];paused=False;child=None
    switch.acquire()
    def record(phase,**values):
        events.append({'phase':phase,'monotonic_ns':time.perf_counter_ns(),**values})
        (output/'switch-results.json').write_text(json.dumps({'events':events},indent=2),encoding='utf-8')
    try:
        request=endpoint.parent/f"pause-{normal['nonce']}.json"
        with request.open('x',encoding='utf-8') as stream:
            json.dump({'action':'pause','pid':normal['pid'],'nonce':normal['nonce'],'ts':time.time()},stream)
        record('normal-stop-requested')
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            state=json.loads(endpoint.read_text(encoding='utf-8'))
            if state.get('phase')=='paused':paused=True;break
            time.sleep(.1)
        if not paused:raise RuntimeError('normal pause was not acknowledged; trial was not started')
        # Only after explicit cleanup acknowledgement may the trial start.
        for key in (18944,'camera-'+str(normal['camera'])):
            lease=InputLease(key);lease.acquire();lease.release()
        record('normal-leases-released')
        with (output/'trial-output.txt').open('x',encoding='utf-8') as log:
            child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            record('trial-started',pid=child.pid)
            try:code=child.wait(timeout=timeout)
            except (subprocess.TimeoutExpired,KeyboardInterrupt):
                child.terminate();child.wait(timeout=10);raise
        record('trial-stopped',exit_code=code)
        if code:raise RuntimeError('isolated trial failed; normal restoration still runs')
    finally:
        try:
            if paused:
                restoring_after=time.time()
                with (output/'normal-restored.out.txt').open('x',encoding='utf-8') as normal_out, \
                     (output/'normal-restored.err.txt').open('x',encoding='utf-8') as normal_err:
                    process=subprocess.Popen(argv,cwd=normal['cwd'],stdout=normal_out,stderr=normal_err,
                                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                record('normal-restarting-stopped',pid=process.pid,automatic_arm=False)
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    matches=[]
                    for path in endpoint.parent.glob('normal-*.json'):
                        value=json.loads(path.read_text(encoding='utf-8'))
                        if (value.get('created_ts',0)>=restoring_after and value.get('argv')==argv
                                and value.get('phase')=='normal'):matches.append(value)
                    if matches:
                        record('normal-restored',pid=process.pid,armed=False);break
                    if process.poll() is not None:raise RuntimeError('normal restoration process failed')
                    time.sleep(.1)
                else:raise RuntimeError('normal restoration readiness was not observed')
        finally:switch.release()
    return events


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('endpoint',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--timeout',type=float,default=900);parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args();command=args.command
    if command and command[0]=='--':command=command[1:]
    if not command:parser.error('isolated trial command is required')
    run(args.endpoint,args.output,command,args.timeout)
