"""Self-tests for a consistent release whose startup contract is nevertheless wrong."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'completion_release_verifier', Path(__file__).resolve().parents[1] / 'verify_completion_release.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_release(root, contract=None, extra_source=False):
    """Use the existing manifest format; SBOM and every declared byte are valid."""
    payload = root / 'payload'
    source = payload / 'slicer-cstamp'
    (source / 'cstamp').mkdir(parents=True)
    (source / 'CStampModule.py').write_text('baseline_diameter = 5\n', encoding='utf-8')
    (source / 'cstamp' / 'storage_selection.py').write_text('schema_version = 1\n', encoding='utf-8')
    files = [{'path': p.relative_to(source).as_posix(), 'sha256': digest(p)}
             for p in sorted(source.rglob('*.py'))]
    expected = {row['path']: row['sha256'] for row in files}
    if extra_source:
        extra = source / 'unsigned_extra.py'
        extra.write_text('unexpected = True\n', encoding='utf-8')
        expected['unsigned_extra.py'] = digest(extra)
    if contract is not None:
        expected = contract(expected)
    configuration = payload / 'config' / 'runtime.json'
    configuration.parent.mkdir()
    configuration.write_text(json.dumps({'slicer_software_sha256': expected}), encoding='utf-8')
    components = {'slicer-cstamp': {'files': files}}
    sbom = root / 'sbom.json'
    sbom.write_text(json.dumps({'components': components}), encoding='utf-8')
    manifest = root / 'manifest.json'
    manifest.write_text(json.dumps({
        'components': components, 'runtime_dependencies': {'files': []},
        'deployment_configuration': [{'payload_path': 'config/runtime.json', 'sha256': digest(configuration)}],
        'external_executables': [], 'sbom_sha256': digest(sbom),
    }), encoding='utf-8')
    return manifest


def test_existing_manifest_format_with_matching_runtime_remains_valid(tmp_path):
    result = module.verify(prepare_release(tmp_path))
    assert result['inventory_passed'] and result['runtime_source_passed']
    assert result['runtime_source_files_checked'] == 2
    assert not result['trusted_signature_verified'] and not result['activated']


def test_byte_consistent_release_with_obsolete_runtime_is_rejected(tmp_path):
    def obsolete(expected):
        expected['CStampModule.py'] = hashlib.sha256(b'baseline_diameter = 10\n').hexdigest()
        return expected
    result = module.verify(prepare_release(tmp_path, obsolete))
    assert not result['inventory_passed'] and not result['runtime_source_passed']
    assert result['errors'] == [{
        'path': 'config/runtime.json', 'reason': 'runtime Slicer source inventory differs from payload',
        'source_paths': ['CStampModule.py'],
    }]


@pytest.mark.parametrize('change', ['missing_new_file', 'removed_file'])
def test_runtime_source_set_must_cover_exact_loaded_modules(tmp_path, change):
    def wrong_set(expected):
        if change == 'missing_new_file':
            expected.pop('cstamp/storage_selection.py')
        else:
            expected['obsolete.py'] = 'a' * 64
        return expected
    result = module.verify(prepare_release(tmp_path, wrong_set))
    assert not result['runtime_source_passed']
    assert result['errors'][0]['reason'] == 'runtime Slicer source inventory differs from payload'


def test_matching_runtime_cannot_bless_source_absent_from_manifest(tmp_path):
    result = module.verify(prepare_release(tmp_path, extra_source=True))
    assert not result['inventory_passed'] and not result['runtime_source_passed']
    assert result['errors'][0]['reason'] == 'loaded source files differ from manifest inventory'
    assert result['errors'][0]['source_paths'] == ['unsigned_extra.py']


@pytest.mark.parametrize('contract', [None, {}, 'invalid', {'CStampModule.py': 'invalid'}])
def test_missing_or_invalid_runtime_inventory_cannot_pass(tmp_path, contract):
    result = module.verify(prepare_release(tmp_path, lambda _: contract))
    assert not result['inventory_passed'] and not result['runtime_source_passed']
    assert result['errors'][0]['reason'].startswith('invalid runtime source contract:')


def test_discovery_matches_slicer_excluded_test_and_cache_directories(tmp_path):
    manifest = prepare_release(tmp_path)
    source = tmp_path / 'payload' / 'slicer-cstamp'
    for excluded in ['tests', '__pycache__']:
        (source / excluded).mkdir()
        (source / excluded / 'not_loaded.py').write_text('irrelevant = True\n', encoding='utf-8')
    result = module.verify(manifest)
    assert result['inventory_passed'] and result['runtime_source_files_checked'] == 2


def test_runtime_file_must_be_bound_by_deployment_inventory(tmp_path):
    manifest = prepare_release(tmp_path)
    data = json.loads(manifest.read_text(encoding='utf-8'))
    data['deployment_configuration'] = []
    manifest.write_text(json.dumps(data), encoding='utf-8')
    result = module.verify(manifest)
    assert not result['inventory_passed'] and not result['runtime_source_passed']
    assert result['errors'][0]['reason'] == 'runtime configuration must be declared exactly once'
