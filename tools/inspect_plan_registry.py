"""Report structural AND integrity/history diagnosis without changing the source."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'prototypes/slicer-cstamp'))
from cstamp.plan_diagnostics import inspect_records
from cstamp.ledger import EventLedger
from cstamp.plan_revision import PlanStore


def inspect(path):
    original=path.read_bytes()
    report={'source_sha256':hashlib.sha256(original).hexdigest(),'integrity_verified':False,'recoverable':False}
    try:
        rows=[json.loads(line) for line in original.decode('utf-8-sig').splitlines() if line.strip()]
        report.update(inspect_records(rows))
        ledger=EventLedger(path)
        report['integrity_verified']=True
        store=PlanStore();store.restore(ledger.events())
        report['recoverable']=True;report['plans']=list(store.plans)
    except (ValueError,KeyError,TypeError) as error:
        report['error']=str(error)
    report['source_unchanged']=path.read_bytes()==original
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('path',type=Path)
    args=parser.parse_args();print(json.dumps(inspect(args.path),ensure_ascii=False,indent=2))
