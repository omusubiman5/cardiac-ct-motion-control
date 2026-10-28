"""Build a candidate from explicitly provided registration and observed metadata.

Does not register/approve a target, copy patient data, or replace active configuration.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'prototypes/slicer-cstamp'))
from cstamp.target_registry import TargetRegistry
from cstamp.runtime_contract import RuntimePolicy


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--targets',type=Path,required=True)
    parser.add_argument('--observed-recognizer',type=Path,required=True)
    parser.add_argument('--slicer-version',required=True)
    parser.add_argument('--observed-slicer',type=Path,required=True,help='metadata exported by the loaded Slicer module')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    targets=TargetRegistry.load(args.targets)
    document={'schema_version':1,'recognizer':json.loads(args.observed_recognizer.read_text(encoding='utf-8-sig')),
              'slicer_version':args.slicer_version,'target_registry_sha256':targets.sha256}
    slicer_metadata=json.loads(args.observed_slicer.read_text(encoding='utf-8-sig'))
    if slicer_metadata['slicer_version'] != args.slicer_version:
        raise ValueError('observed Slicer version does not match')
    document['slicer_software_sha256']=slicer_metadata['software_sha256']
    policy=RuntimePolicy(document)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(policy.document,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({'candidate':str(args.output),'runtime_sha256':policy.sha256,'activated':False}))
