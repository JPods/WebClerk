"""
conform_envelopes — make every record's JSON envelopes match its schema.

The Pydantic schemas in code are the truth (common.schemas.defaults.schema_classes).
Two passes per record:

  1. relocate — values that live code wrote into the wrong place move to where they
     belong (a scalar column, refs.keywords, refs.demo_source). Only fills an empty
     destination; never overwrites.
  2. conform  — whatever the schema still rejects is removed: a key the schema does
     not declare is dropped; a value of the wrong type is dropped so its default applies.

Dry run by default: reports what would change, per model and per key. That report is
also the drift check — a clean run prints nothing to fix.

    python manage.py conform_envelopes                 # report only
    python manage.py conform_envelopes --model item    # one model
    python manage.py conform_envelopes --apply         # write
"""
from __future__ import annotations

import collections
import copy

from django.core.management.base import BaseCommand
from django.db import transaction
from pydantic import ValidationError

from apps.core.constants.model_registry import MODEL_REGISTRY
from common.schemas.defaults import _schema_key, schema_classes

MAX_PASSES = 10


def _fits(obj, field, value) -> bool:
    """Only move a value its destination column can hold; anything else is left to be dropped."""
    internal = obj._meta.get_field(field).get_internal_type()
    if internal in ('IntegerField', 'BigIntegerField', 'PositiveIntegerField'):
        return isinstance(value, int) and not isinstance(value, bool)
    if internal == 'JSONField':
        return isinstance(value, dict)
    return isinstance(value, str)


def _set_if_empty(obj, field, value, changes, label):
    if value in (None, '', [], {}) or not _fits(obj, field, value):
        return
    if getattr(obj, field, None) in (None, '', 0):
        setattr(obj, field, value)
        changes[f'{label} → {field}'] += 1


def _relocate(key, obj, env, changes):
    """Move misplaced values into their proper home. Mutates env (dict of envelopes)."""
    config = env.get('config') if isinstance(env.get('config'), dict) else None
    refs = env.get('refs') if isinstance(env.get('refs'), dict) else None

    if refs is not None and isinstance(refs.get('source'), str):
        tag = refs.pop('source')
        if tag == 'demo-baseline' and not refs.get('demo_source'):
            refs['demo_source'] = tag
            changes['refs.source "demo-baseline" → refs.demo_source'] += 1

    if config is None:
        return
    if key == 'document':
        for ck, field in (('purpose', 'purpose'), ('doc_system', 'purpose'), ('role', 'purpose'),
                          ('parent_model', 'model_name'), ('mime_type', 'mime_type'),
                          ('size_bytes', 'size_bytes'), ('path', 'path')):
            if ck in config:
                _set_if_empty(obj, field, config.pop(ck), changes, f'config.{ck}')
        if 'parent_id' in config:
            pid = config.pop('parent_id')
            _set_if_empty(obj, 'record_id', int(pid) if str(pid or '').isdigit() else None,
                          changes, 'config.parent_id')
        if isinstance(config.get('keywords'), list) and refs is not None:
            kws = config.pop('keywords')
            merged = list(dict.fromkeys((refs.get('keywords') or []) + [str(k) for k in kws]))
            if merged != (refs.get('keywords') or []):
                refs['keywords'] = merged
                changes['config.keywords → refs.keywords'] += 1
        if obj.purpose == 'hook_review' and config.get('status') in ('awaiting_signoff', 'auto_cleared', 'cleared', 'denied'):
            state = config.pop('status')
            obj.status = 'in_review' if state == 'awaiting_signoff' else 'archived'
            if state != 'awaiting_signoff':
                config['decision'] = state
            changes['hook review config.status → status/decision'] += 1
    elif key == 'report':
        for ck in ('editor_type', 'description'):
            if ck in config:
                _set_if_empty(obj, ck, config.pop(ck), changes, f'config.{ck}')
    elif key == 'setting':
        layout = config.get('layout') if isinstance(config.get('layout'), dict) else {}
        if isinstance(layout.get('list'), list):   # pre-2026-08-18 format: a bare column list
            layout['list'] = {'default': {'columns': layout['list']}}
            changes['config.layout.list column list → list.default.columns'] += 1
    elif key == 'pending':
        if 'reason' in config:
            _set_if_empty(obj, 'purpose', config.pop('reason'), changes, 'config.reason')


def _drop(container, loc):
    """Remove the value at loc (a pydantic error location) from container. True if removed."""
    node = container
    for part in loc[:-1]:
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and isinstance(part, int) and part < len(node):
            node = node[part]
        else:
            return False
    last = loc[-1]
    if isinstance(node, dict) and last in node:
        del node[last]
        return True
    if isinstance(node, list) and isinstance(last, int) and last < len(node):
        node.pop(last)
        return True
    return False


def _conform(cls, value, envelope, changes):
    """Drop whatever the schema rejects until it validates. Returns the conformed value."""
    for _ in range(MAX_PASSES):
        try:
            cls.model_validate(value)
            return value
        except ValidationError as e:
            removed = False
            # reverse location order: later list indexes go first, so earlier ones stay valid
            for err in sorted(e.errors(), key=lambda er: tuple(str(p).zfill(6) for p in er['loc']), reverse=True):
                loc = tuple(err['loc'])
                if loc and _drop(value, loc):
                    removed = True
                    top = '.'.join(str(p) for p in loc if not isinstance(p, int))
                    verb = 'undeclared' if err['type'] == 'extra_forbidden' else f"bad {err['type']}"
                    changes[f'{envelope}.{top} ({verb})'] += 1
            if not removed:
                raise RuntimeError(f'{cls.__name__}: cannot conform — {e.errors()[0]}')
    raise RuntimeError(f'{cls.__name__}: still invalid after {MAX_PASSES} passes')


class Command(BaseCommand):
    help = "Relocate misplaced envelope values and drop what the schema rejects (dry run by default)."

    def add_arguments(self, parser):
        parser.add_argument('--model', action='append', help='Model key; repeatable. Default: all.')
        parser.add_argument('--apply', action='store_true', help='Write changes (default: report only).')

    def handle(self, *args, **options):
        keys = options['model'] or sorted(k for k in MODEL_REGISTRY if _schema_key(k) == k)
        apply = options['apply']
        total_records = 0
        for key in keys:
            classes = schema_classes(key)
            Model = MODEL_REGISTRY[key].import_model()
            scalar_fields = {'purpose', 'model_name', 'record_id', 'mime_type', 'size_bytes',
                             'path', 'status', 'editor_type', 'description'}
            changes = collections.Counter()
            touched = 0
            with transaction.atomic():
                for obj in Model.objects.all():
                    env = {e: copy.deepcopy(getattr(obj, e)) for e in classes
                           if isinstance(getattr(obj, e, None), dict)}
                    before_scalars = {f: getattr(obj, f) for f in scalar_fields if hasattr(obj, f)}
                    before_env = copy.deepcopy(env)
                    _relocate(key, obj, env, changes)
                    for e, cls in classes.items():
                        if e in env and env[e]:
                            env[e] = _conform(cls, env[e], e, changes)
                    updates = {e: v for e, v in env.items() if v != before_env[e]}
                    updates.update({f: getattr(obj, f) for f, v in before_scalars.items() if getattr(obj, f) != v})
                    if updates:
                        touched += 1
                        if apply:
                            Model.objects.filter(pk=obj.pk).update(**updates)
            if touched:
                total_records += touched
                self.stdout.write(f'{key}: {touched} record(s) {"changed" if apply else "to change"}')
                for what, n in changes.most_common():
                    self.stdout.write(f'    {n:>5}  {what}')
        verb = 'changed' if apply else 'would change'
        self.stdout.write(self.style.SUCCESS(f'{total_records} record(s) {verb}.'))
