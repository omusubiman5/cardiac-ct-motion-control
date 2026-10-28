"""Persist preparation-side ledger selection; never create or modify ledgers."""
import json
import os
import tempfile
from pathlib import Path
from .ledger import EventLedger
from .plan_revision import PlanStore


def validate_selection(events, plans):
    paths = []
    for value in (events, plans):
        if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
            raise ValueError('台帳には既存ファイルの絶対パスを指定してください')
        path = Path(value).resolve(strict=True)
        if not path.is_file():
            raise ValueError('台帳ファイルが見つかりません')
        paths.append(path)
    if paths[0] == paths[1] or os.path.samefile(*paths):
        raise ValueError('操作記録と計画には別の台帳を指定してください')
    EventLedger(paths[0])
    PlanStore().restore(EventLedger(paths[1]).events())
    return {'schema_version': 1, 'events': str(paths[0]), 'plans': str(paths[1])}


def load_selection(path):
    path = Path(path)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 1:
        raise ValueError('保存先設定の形式が不正です')
    return validate_selection(value.get('events'), value.get('plans'))


def save_selection(path, events, plans):
    value = validate_selection(events, plans)
    path = Path(path)
    # Never allow the settings write to replace either ledger (including aliases).
    for ledger in (Path(value['events']), Path(value['plans'])):
        if path.resolve() == ledger or (path.exists() and os.path.samefile(path, ledger)):
            raise ValueError('設定ファイルと台帳は別の場所に保存してください')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name+'.', suffix='.tmp', delete=False) as stream:
            temporary = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return value
