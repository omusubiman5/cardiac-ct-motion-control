"""Read-only inventory validation. Does not bypass signature gates or activate a release."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def verify_slicer_runtime(data, payload, errors):
    """Bind the startup runtime contract to the exact Python files Slicer loads.

    A byte-consistent SBOM can still contain an obsolete runtime contract. Match
    CStampModule's source discovery, including nested modules and excluding its
    tests/cache directories; never use the current workspace as the expected set.
    """
    runtime_path = 'config/runtime.json'
    declarations = [row for row in data.get('deployment_configuration', [])
                    if row.get('payload_path') == runtime_path]
    if len(declarations) != 1:
        errors.append({'path': runtime_path, 'reason': 'runtime configuration must be declared exactly once'})
        return False, 0
    try:
        runtime = json.loads((payload / runtime_path).read_text(encoding='utf-8-sig'))
        expected = runtime.get('slicer_software_sha256') if isinstance(runtime, dict) else None
        if not isinstance(expected, dict) or not expected or any(
            not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64
            or any(c not in '0123456789abcdef' for c in digest)
            for name, digest in expected.items()
        ):
            raise ValueError('missing or invalid Slicer source inventory')
    except (OSError, ValueError) as exc:
        errors.append({'path': runtime_path, 'reason': 'invalid runtime source contract: ' + str(exc)})
        return False, 0

    base = (payload / 'slicer-cstamp').resolve()
    actual = {}
    initial_error_count = len(errors)
    for path in sorted(base.rglob('*')):
        relative = path.relative_to(base)
        if (not path.is_file() or not path.name.endswith('.py')
                or any(part in {'tests', '__pycache__'} for part in relative.parts)):
            continue
        if not path.resolve().is_relative_to(base):
            errors.append({'path': relative.as_posix(), 'reason': 'runtime source path escape'})
            continue
        actual[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    different = sorted(name for name in expected.keys() | actual.keys()
                       if expected.get(name) != actual.get(name))
    if different:
        errors.append({'path': runtime_path, 'reason': 'runtime Slicer source inventory differs from payload',
                       'source_paths': different})
    declared = {row['path'] for row in data.get('components', {}).get('slicer-cstamp', {}).get('files', [])
                if row['path'].endswith('.py') and not any(
                    part in {'tests', '__pycache__'} for part in Path(row['path']).parts)}
    if declared != actual.keys():
        errors.append({'path': 'slicer-cstamp', 'reason': 'loaded source files differ from manifest inventory',
                       'source_paths': sorted(declared ^ actual.keys())})
    return len(errors) == initial_error_count, len(actual)


def verify(manifest):
    data=json.loads(manifest.read_text(encoding='utf-8'));errors=[];count=0
    def check(base,row):
        nonlocal count
        target=(base/row['path']).resolve();count+=1
        if not target.is_relative_to(base.resolve()):errors.append({'path':row['path'],'reason':'path escape'});return
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=row['sha256']:
            errors.append({'path':row['path'],'reason':'missing or changed bytes'})
    for component,value in data['components'].items():
        if component not in {'slicer-cstamp','cmos-motion-poc','tools'}:raise ValueError('unknown component')
        for row in value['files']:check(manifest.parent/'payload'/component,row)
    for row in data['runtime_dependencies']['files']:check(manifest.parent/'payload/recognizer-runtime',row)
    for row in data['deployment_configuration']:check(manifest.parent/'payload',{'path':row['payload_path'],'sha256':row['sha256']})
    for row in data['external_executables']:
        path=Path(row['path'])
        count+=1
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            errors.append({'path':row['path'],'reason':'external executable changed'})
    if hashlib.sha256((manifest.parent/'sbom.json').read_bytes()).hexdigest()!=data['sbom_sha256']:
        errors.append({'path':'sbom.json','reason':'digest mismatch'})
    sbom=json.loads((manifest.parent/'sbom.json').read_text(encoding='utf-8'))
    for component,value in data['components'].items():
        expected={r['path']:r['sha256'] for r in sbom['components'][component]['files']}
        actual={r['path']:r['sha256'] for r in value['files']}
        if actual!=expected:errors.append({'path':component,'reason':'SBOM payload inventory differs'})
    runtime_source_passed,runtime_source_files_checked=verify_slicer_runtime(data,manifest.parent/'payload',errors)
    return {'inventory_passed':not errors,'files_checked':count,'errors':errors,
            'runtime_source_passed':runtime_source_passed,'runtime_source_files_checked':runtime_source_files_checked,
            'trusted_signature_verified':False,'activated':False,'kind':'read-only byte/inventory self-verification'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('manifest',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=verify(args.manifest)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result));raise SystemExit(0 if result['inventory_passed'] else 1)
