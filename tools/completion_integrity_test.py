"""Corrupt only an isolated fixture ledger, call the actual Slicer loader, restore exact bytes."""
import argparse,hashlib,json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
from session_client import SlicerSessionClient

def run(out):
    out=out.resolve()
    if not out.is_relative_to(ROOT/'work'):raise ValueError('isolated project fixture required')
    ready=json.loads((out/'ready.json').read_text(encoding='utf-8'))
    if ready['port']==18944:raise ValueError('normal endpoint forbidden')
    path=out/'events.jsonl';original=path.read_bytes();rows=original.decode('utf-8').splitlines()
    if not rows:raise ValueError('a committed isolated event is required')
    event=json.loads(rows[0]);event['placement']['anchor'][0]+=100
    cases={'anchor-tamper-original-integrity':(json.dumps(event)+'\n'+'\n'.join(rows[1:])+'\n').encode(),
           'partial-last-line':original+b'{"partial":',
           'duplicate-event':original+rows[0].encode()+b'\n',
           'invalid-integrity':original.replace(json.loads(rows[0])['integrity'].encode(),b'0'*64,1)}
    client=SlicerSessionClient(port=ready['port']);client.runtime_manifest=ready['runtime_manifest'];records=[]
    try:
        assert client.send('arm')['ok']
        for name,data in cases.items():
            path.write_bytes(data)
            response=client.send('load_session')
            assert response.get('ok') is False,(name,response)
            assert path.read_bytes()==data,'loader rewrote a rejected ledger'
            records.append({'case':name,'response':response,'rejected_file_unchanged':True})
            path.write_bytes(original)
        response=client.send('load_session');assert response['ok'],response
        assert path.read_bytes()==original
        result={'passed':True,'records':records,'restored_original_sha256':hashlib.sha256(original).hexdigest(),
                'real_hand_verified':False,'kind':'self-verification; actual isolated Slicer loader; synthetic ledger corruption'}
    except Exception:result={'passed':False,'error':traceback.format_exc(),'records':records,'real_hand_verified':False}
    finally:
        path.write_bytes(original)
        try:client.send('disarm')
        finally:client.close()
    with (out/'integrity-results.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return {k:v for k,v in result.items() if k!='records'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    result=run(args.out);print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
