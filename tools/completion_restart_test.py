"""Read back the fault trial after a separate actual Slicer process restart."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient


def run(out):
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'));previous=json.loads((out/'fault-results.json').read_text(encoding='utf-8'))
    assert ready['port']!=18944 and previous['passed']
    ledger=out/'events.jsonl';before=hashlib.sha256(ledger.read_bytes()).hexdigest()
    client=SlicerSessionClient(port=ready['port']);client.runtime_manifest=ready['runtime_manifest']
    try:
        result=client.send('query_result',{'req':previous['saved_req']})
        assert result['result']['response']['event_id']==previous['event_id'],result
        assert result['state']['armed'] is False
        assert client.send('arm')['ok']
        loaded=client.send('load_session');assert loaded['ok'],loaded
        assert hashlib.sha256(ledger.read_bytes()).hexdigest()==before
        result={'passed':True,'pid':ready['pid'],'saved_event':previous['event_id'],
                'ledger_unchanged':True,'load_response':loaded,'real_hand_verified':False}
    finally:client.send('disarm');client.close()
    with (out/'restart-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    print(json.dumps(run(args.out),ensure_ascii=False))
