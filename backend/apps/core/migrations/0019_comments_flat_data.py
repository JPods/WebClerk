"""One comments standard (Bill, 2026-09-25): flatten nested comments and rename the leaves.

Records: ``comments.general.<channel>`` entries move to ``comments.<channel>``, and
``comments.records['model/id'].<channel>`` entries move there too, prefixed with the record
they were about. Each old entry {text, by, ts, source} becomes {user, user_id, mgs, time,
source}. The empty ``general``/``records`` scaffolding is dropped.

Settings: access lists and layouts named leaves of the old schema. They are renamed to the
flat schema's: comments.general.<ch>.text → comments.<ch>.mgs, .by → .user (+ .user_id),
.ts → .time, .source stays, comments.general.<ch> → comments.<ch>; comments.records[...] is
gone. Line leaves carry a prefix (lines.comments.general...). Without this the leaf prune would strip every role's comment access.
"""
import re

from django.db import migrations

_LEAF = re.compile(r'^((?:[a-z_]+\.)*)comments\.general\.(public|process|foreign)(?:\.(text|by|ts|source))?$')
_RECORDS = re.compile(r'^(?:[a-z_]+\.)*comments\.records(?:\..*)?$')
# Every renamed entry leaf also grants ``key``: a role that sees and saves a channel must carry
# the idempotency keys through, or its save drops them and a system write repeats (Fable).
_SUB = {'text': ['mgs', 'key'], 'by': ['user', 'user_id', 'key'], 'ts': ['time', 'key'],
        'source': ['source', 'key']}


def _entry(old, about=None):
    if old is None:
        return None
    old = old if isinstance(old, dict) else {'text': str(old)}
    by = str(old.get('by') or '')
    mgs = str(old.get('text') or old.get('mgs') or '')
    new = {'user': old.get('user') or by or 'system',
           'user_id': old.get('user_id') if old.get('user_id') is not None
           else (int(by) if by.isdigit() else None),
           'mgs': f"[{about}] {mgs}" if about else mgs,
           'time': str(old.get('time') or old.get('ts') or '')}
    if old.get('source'):
        new['source'] = str(old['source'])
    return new


def _flatten(comments):
    if not isinstance(comments, dict) or not ({'general', 'records'} & set(comments)):
        return None
    flat = {k: list(v) for k, v in comments.items()
            if k not in ('general', 'records') and isinstance(v, list)}
    for ch, entries in (comments.get('general') or {}).items():
        for e in entries or []:
            flat.setdefault(ch, []).append(_entry(e))
    for about, chans in (comments.get('records') or {}).items():
        for ch, entries in (chans or {}).items() if isinstance(chans, dict) else ():
            for e in entries or []:
                flat.setdefault(ch, []).append(_entry(e, about))
    return {k: [e for e in v if e is not None] for k, v in flat.items() if v}


def _old_entries(comments):
    """Flat channels whose entries still carry the old fields (text/by/ts): written by
    seed_gl_accounts before this change. Converted in place; new-shape entries untouched."""
    if not isinstance(comments, dict):
        return None
    changed, out = False, {}
    for ch, entries in comments.items():
        if not isinstance(entries, list):
            out[ch] = entries
            continue
        new = []
        for e in entries:
            if isinstance(e, dict) and 'mgs' not in e and ({'text', 'by', 'ts'} & set(e)):
                n = _entry(e)
                if e.get('kind'):
                    n['key'] = str(e['kind'])        # seed_gl_accounts: kind=account_use
                new.append(n); changed = True
            elif e is not None:
                new.append(e)
            else:
                changed = True
        out[ch] = new
    return out if changed else None


def _rename(value):
    if isinstance(value, dict):
        return {k: _rename(v) for k, v in value.items()}
    if isinstance(value, list):
        out = []
        for v in value:
            for n in (_rename_leaf(v) if isinstance(v, str) else [_rename(v)]):
                if n is not None and n not in out:
                    out.append(n)
        return out
    if isinstance(value, str):
        renamed = _rename_leaf(value)
        return renamed[0] if renamed else value
    return value


def _rename_leaf(s):
    if _RECORDS.match(s):
        return []                                     # the scope is gone
    m = _LEAF.match(s)
    if not m:
        return [s]
    prefix, ch, sub = m.groups()                      # lines.comments... on documents
    return ([f'{prefix}comments.{ch}'] if not sub
            else [f'{prefix}comments.{ch}.{x}' for x in _SUB[sub]])


def forward(apps, schema_editor):
    for model in apps.get_models():
        if not any(f.name == 'comments' for f in model._meta.fields):
            continue
        for pk, comments in model.objects.exclude(comments={}).values_list('pk', 'comments').iterator():
            flat = _flatten(comments)
            flat = _old_entries(flat if flat is not None else comments) or flat
            if flat is not None:
                model.objects.filter(pk=pk).update(comments=flat)

    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.all().only('pk', 'config').iterator():
        text = str(s.config)
        if 'comments.general' not in text and 'comments.records' not in text:
            continue
        Setting.objects.filter(pk=s.pk).update(config=_rename(s.config))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_comments_flat_default'),
        ('accounts', '0015_comments_flat_default'),
        ('ai_assistant', '0009_comments_flat_default'),
        ('communications', '0010_comments_flat_default'),
        ('docs', '0006_comments_flat_default'),
        ('orgs', '0009_comments_flat_default'),
        ('products', '0016_comments_flat_default'),
        ('sync', '0008_comments_flat_default'),
        ('transactions', '0044_comments_flat_default'),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
