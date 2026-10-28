"""Stage immutable payload and hash-bound signing catalog; never fabricate a trusted signature."""
import argparse
import hashlib
import json
import shutil
import time
import sys
from pathlib import Path
from generate_sbom import ROOT, COMPONENTS, iter_files, frozen_dependencies, runtime_file_inventory


def prepare(slicer_executable):
    destination = ROOT/'artifacts'/'releases'/time.strftime('%Y%m%d-%H%M%S')
    destination.mkdir(parents=True,exist_ok=False)
    manifest={'scope':'non-clinical prototype','components':{},'python_dependencies':frozen_dependencies(),
              'runtime_dependencies':{'delivery':'external verified installed virtual environment','files':runtime_file_inventory()}}
    manifest['runtime_dependencies']['delivery']='bundled immutable per-release virtual environment; Python base and Slicer remain external'
    venv=(ROOT/'prototypes/cmos-motion-poc/.venv').resolve()
    known={row['path'] for row in manifest['runtime_dependencies']['files']}
    for relative in ('Scripts/python.exe','pyvenv.cfg'):
        if relative not in known:
            source=venv/relative
            manifest['runtime_dependencies']['files'].append({'distribution':'venv-bootstrap','path':relative,
                'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':source.stat().st_size})
    for row in manifest['runtime_dependencies']['files']:
        source=(venv/row['path']).resolve()
        if not source.is_relative_to(venv):raise ValueError('runtime path escape')
        target=destination/'payload/recognizer-runtime'/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    slicer_executable=slicer_executable.resolve()
    external=[('slicer_launcher',slicer_executable),('slicer_runtime',slicer_executable.parent/'bin/SlicerApp-real.exe'),
              ('python_runtime',Path(sys.base_prefix)/'python.exe'),
              ('python_runtime_dll',Path(sys.base_prefix)/f'python{sys.version_info.major}{sys.version_info.minor}.dll')]
    manifest['external_executables']=[{'role':role,'path':str(path.resolve()),
                                      'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for role,path in external]
    manifest['deployment_configuration']=[]
    for relative in ('artifacts/cstamp/targets.json','artifacts/cstamp/runtime.json'):
        source=ROOT/relative
        if not source.is_file():raise FileNotFoundError('prepare validated deployment configuration first: '+relative)
        payload_relative='config/'+source.name
        target=destination/'payload'/payload_relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        manifest['deployment_configuration'].append({'path':relative,'payload_path':payload_relative,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    sbom=ROOT/'artifacts/sbom'/('sbom-'+time.strftime('%Y%m%d')+'.json')
    if not sbom.is_file():raise FileNotFoundError('generate the current source SBOM before staging')
    shutil.copy2(sbom,destination/'sbom.json')
    manifest['sbom_sha256']=hashlib.sha256((destination/'sbom.json').read_bytes()).hexdigest()
    manifest['signature_contract']={'payload_and_sbom':'trusted detached manifest.json.ps1 catalog binds exact digests',
                                    'entry_points':'activate_completion_release.ps1 and start_completion_release.ps1 own Authenticode signatures',
                                    'signing_order':['freeze payload and external configuration','generate SBOM and manifest',
                                                     'sign outer entry points and detached catalog','verify existing certificate trust',
                                                     'stop tools, activate, launch and observe loaded source']}
    for component in COMPONENTS:
        rows=[]
        for relative,source in iter_files(component):
            target=destination/'payload'/component.name/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
            rows.append({'path':relative.as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size})
        manifest['components'][component.name]={'files':rows,'file_count':len(rows)}
    path=destination/'manifest.json'
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    catalog=path.with_suffix('.json.ps1')
    catalog.write_text('# manifest-sha256: '+hashlib.sha256(path.read_bytes()).hexdigest()+'\n# Sign with the approved trusted distribution certificate.\n',encoding='utf-8')
    shutil.copy2(ROOT/'tools'/'activate_completion_release.ps1',destination/'activate_completion_release.ps1')
    shutil.copy2(ROOT/'tools'/'start_completion_release.ps1',destination/'start_completion_release.ps1')
    print(json.dumps({'staged':str(destination),'trusted_signature':'NOT PROVIDED','activated':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--slicer-executable',type=Path,required=True)
    prepare(parser.parse_args().slicer_executable)
