"""Actual storage subprocess exits around atomic replace. Synthetic events only."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/slicer-cstamp'))
from cstamp.ledger import EventLedger


def run(out):
    out=out.resolve()
    if not out.is_relative_to(ROOT/'work'):raise ValueError('isolated output required')
    out.mkdir(parents=True,exist_ok=False)
    results=[]
    for phase,code in [('before',77),('after',78)]:
        path=out/(phase+'.jsonl');ledger=EventLedger(path)
        ledger.append({'event_id':'old','fixture':'synthetic storage process crash'})
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        child=out/(phase+'.py')
        child.write_text("""import os,sys
from pathlib import Path
sys.path.insert(0,%r)
from cstamp.ledger import EventLedger
import cstamp.ledger as module
original=module.os.replace
def interrupted(source,target):
    if %r=='after':original(source,target)
    os._exit(%d)
module.os.replace=interrupted
EventLedger(Path(%r)).append({'event_id':'new','fixture':'synthetic storage process crash',
                            'request_receipt':{'req':'crash-'+%r}})
"""%(str(ROOT/'prototypes/slicer-cstamp'),phase,code,str(path),phase),encoding='utf-8')
        completed=subprocess.run([sys.executable,str(child)],timeout=10,capture_output=True)
        restored=EventLedger(path);events=restored.events()
        assert completed.returncode==code,(phase,completed.stderr)
        assert len(events)==(1 if phase=='before' else 2)
        assert all(restored.verify_integrity(event) for event in events)
        assert (restored.request_result('crash-'+phase) is not None)==(phase=='after')
        if phase=='before':assert hashlib.sha256(path.read_bytes()).hexdigest()==before
        results.append({'phase':phase,'exit_code':code,'restored_events':len(events),'integrity_verified':True})
    result={'passed':True,'kind':'self-verification; actual storage subprocess/NTFS; not Slicer process crash','results':results}
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args();print(json.dumps(run(args.out)))
