"""Preparation-registered non-clinical targets; observation never grants permission."""
import copy
import json
from pathlib import Path
from .contracts import digest


class TargetRegistry:
    FIELDS = ('target_id', 'scene_id', 'model_name', 'model_sha256',
              'transform_sha256', 'registration_reference')

    def __init__(self, document):
        if not isinstance(document, dict) or type(document.get('schema_version')) is not int or document.get('schema_version') != 1:
            raise ValueError('unsupported target registry schema')
        targets = document.get('targets')
        if not isinstance(targets, list):
            raise ValueError('target registry must contain a targets list')
        seen = set()
        for row in targets:
            if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip() for k in self.FIELDS):
                raise ValueError('target registration is incomplete')
            if row['target_id'] in seen:
                raise ValueError('duplicate registered target ID')
            seen.add(row['target_id'])
            for key in ('model_sha256', 'transform_sha256'):
                if len(row[key]) != 64 or any(c not in '0123456789abcdef' for c in row[key]):
                    raise ValueError('invalid target digest')
            if row.get('scene_sha256') is not None:
                value = row['scene_sha256']
                if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                    raise ValueError('invalid scene digest')
        self.document = copy.deepcopy(document)
        self.sha256 = digest(self.document)

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8-sig')))

    def match(self, observation):
        keys = ('scene_id', 'model_name', 'model_sha256', 'transform_sha256')
        matches = [r for r in self.document['targets']
                   if all(r[k] == observation.get(k) for k in keys)
                   and (r.get('scene_sha256') is None or r['scene_sha256'] == observation.get('scene_sha256'))]
        if len(matches) != 1:
            raise ValueError('target is unregistered, ambiguous, or changed')
        # MRML node IDs vary across restarts and are deliberately not persisted.
        return {'target_id': matches[0]['target_id'], 'registry_sha256': self.sha256,
                **{k: copy.deepcopy(observation[k]) for k in keys},
                'scene_sha256': observation.get('scene_sha256'),
                'transform': copy.deepcopy(observation.get('transform'))}
