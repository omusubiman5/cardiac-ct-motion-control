"""Shared finite canonical configuration contract, independent of Qt and camera."""
import copy
import hashlib
import json
from pathlib import Path


def canonical_hash(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


class RuntimePolicy:
    def __init__(self, document):
        if not isinstance(document, dict) or type(document.get('schema_version')) is not int or document.get('schema_version') != 1:
            raise ValueError('unsupported runtime configuration schema')
        for key in ('recognizer', 'slicer_version', 'target_registry_sha256'):
            if key not in document:
                raise ValueError('runtime configuration is missing '+key)
        recognition = document['recognizer']
        if not isinstance(recognition, dict) or any(k not in recognition for k in ('settings','camera','model_sha256','software_sha256','python_version','windows_version')):
            raise ValueError('recognizer configuration is incomplete')
        camera=recognition['camera']
        if not isinstance(camera,dict) or any(type(camera.get(k)) is not int or camera[k]<1 for k in ('width','height')) or type(camera.get('index')) is not int or camera['index']<0:
            raise ValueError('actual camera configuration is incomplete')
        if not isinstance(recognition['settings'],dict) or not isinstance(recognition['software_sha256'],dict):
            raise ValueError('settings and software inventory must be objects')
        for value in [document['target_registry_sha256'], recognition['model_sha256'], camera.get('device_path_sha256'), *recognition['software_sha256'].values()]:
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('invalid runtime digest')
        if any(not isinstance(v,str) or not v for v in (document['slicer_version'], recognition['python_version'], recognition['windows_version'],camera.get('backend'))):
            raise ValueError('runtime versions and camera backend are required')
        self.document = copy.deepcopy(document)
        self.sha256 = canonical_hash(self.document)

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8-sig')))

    def verify(self, actual_recognizer, slicer_version, target_registry_hash):
        if actual_recognizer != self.document['recognizer']:
            raise ValueError('recognizer actual configuration differs from prepared configuration')
        self.verify_local(slicer_version, target_registry_hash)
        canonical_hash(actual_recognizer)
        return self.sha256

    def verify_local(self, slicer_version, target_registry_hash):
        if slicer_version != self.document['slicer_version']:
            raise ValueError('Slicer version differs from prepared configuration')
        if target_registry_hash != self.document['target_registry_sha256']:
            raise ValueError('target registration differs from prepared configuration')
