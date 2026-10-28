"""Read-only structural diagnosis. Never synthesize missing plan history."""
from .contracts import digest


def inspect_records(records):
    issues=[]
    for line,row in enumerate(records,1):
        if not isinstance(row,dict):
            issues.append({'line':line,'missing':['object']}); continue
        kind=row.get('record_type')
        if kind not in {'plan_created','plan_revision','planned_item_commit'}:continue
        fields=['plan_id','version','created_ts','creator','approval']
        item_key='working_items' if kind=='planned_item_commit' else 'items'
        fields.append(item_key)
        missing=[k for k in fields if k not in row]
        if missing:
            issues.append({'line':line,'plan_id':row.get('plan_id'),'version':row.get('version'),'missing':missing})
            continue
        items=row[item_key]
        if not isinstance(items,list) or any(not isinstance(i,dict) for i in items):
            issues.append({'line':line,'invalid':item_key});continue
        ids=[i.get('event_id') or i.get('item_id') for i in items]
        if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
            issues.append({'line':line,'invalid':'item identity'})
        if not isinstance(row['version'],int) or isinstance(row['version'],bool) or row['version']<1:
            issues.append({'line':line,'invalid':'version'})
    return {'structurally_recoverable':not issues,'issues':issues,'record_count':len(records),
            'records_sha256':digest(records)}


def require_history(records):
    diagnosis=inspect_records(records)
    if diagnosis['issues']:
        issue=diagnosis['issues'][0]
        raise ValueError('計画履歴の行%sに%s。欠落履歴は補完しません。準備画面で新規計画台帳を選択してください。' %
                         (issue['line'], '欠落：'+','.join(issue['missing']) if 'missing' in issue else '不正：'+issue['invalid']))
    return diagnosis
