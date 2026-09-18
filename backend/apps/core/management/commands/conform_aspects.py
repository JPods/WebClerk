"""Bring stored JSON aspects and the Settings that name them into their schemas.

Each step moves data written in an older shape to the one its schema declares,
and renames Setting paths that pointed at the older shape. Dry run by default.

    python manage.py conform_aspects                  # report every step
    python manage.py conform_aspects --step shipping  # one step
    python manage.py conform_aspects --apply

Steps
  shipping  TransactionShipping on order/invoice/proposal/purchase/workorder:
            ship_to {address1, city_state_zip, …} → ShipToSnapshot,
            dt_shipped / dt_delivered '' → None, validated through the schema;
            wc:model Settings: flat leaf paths → the nested ones.
  action    action / description: plain strings → {en}; agent-proposal keys
            written into action (source_agent, sprint_week, …) → metadata, where
            allie-reflect.py reads them; languages {} → []; user stamps with a
            non-numeric id keep their email and lose the id.
  records   project objective / tasks / logistics stored as plain text → the
            schema (text kept in summary / notes; goal and success_criteria →
            summary and success.definition); document.path wc2_note / ask_bill →
            description; org metrics periods {key: {...}} → [{period: key, ...}].
"""
from __future__ import annotations

import json
import re

from django.core.management.base import BaseCommand
from django.db import transaction

SHIPPING_MODELS = ('order', 'invoice', 'proposal', 'purchase', 'workorder')

# Flat shipping leaves the layouts used → the leaves the data actually has.
SHIPPING_PATH_RENAMES = {
    'shipping.freight': 'shipping.costs.freight',
    'shipping.fuel_surcharge': 'shipping.costs.fuel_surcharge',
    'shipping.insurance': 'shipping.costs.insurance',
    'shipping.handling': 'shipping.costs.handling',
    'shipping.estimated': 'shipping.costs.estimated',
    'shipping.actual': 'shipping.costs.actual',
    'shipping.customer_charge': 'shipping.costs.customer',
    'shipping.gross_weight': 'shipping.weight.gross',
    'shipping.weight_unit': 'shipping.weight.unit',
}


def _ship_to_snapshot(old: dict) -> dict:
    if not old or 'full_address' in old:
        return old or {}
    lines = [old.get('address1', ''), old.get('address2', ''), old.get('city_state_zip', '')]
    return {
        'company': old.get('company', ''),
        'attention': old.get('attention', ''),
        'full_address': '\n'.join(x for x in lines if x),
        'phone': old.get('phone', ''),
    }


def _epoch_or_none(v):
    return None if v in ('', None) else v


def rename_paths_in_settings(renames: dict, stdout, apply: bool) -> int:
    """Rename exact quoted path strings anywhere in Setting configs."""
    from apps.core.models.setting import Setting
    pattern = re.compile('"(' + '|'.join(re.escape(k) for k in renames) + ')"')
    changed = 0
    for s in Setting.objects.all().only('id', 'ida', 'config'):
        text = json.dumps(s.config or {})
        new_text, n = pattern.subn(lambda m: f'"{renames[m.group(1)]}"', text)
        if n:
            changed += 1
            stdout.write(f'  setting {s.id} {s.ida}: {n} path(s) renamed')
            if apply:
                s.config = json.loads(new_text)
                s.save(update_fields=['config'])
    return changed


class Command(BaseCommand):
    help = 'Conform stored aspects and Setting paths to their schemas (dry run unless --apply)'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--step', choices=['shipping', 'action', 'records'], default=None)

    def handle(self, *args, **opts):
        apply = opts['apply']
        steps = [opts['step']] if opts['step'] else ['shipping', 'action', 'records']
        with transaction.atomic():
            for step in steps:
                getattr(self, f'step_{step}')(apply)
        self.stdout.write(self.style.SUCCESS('Applied.' if apply else 'Dry run — nothing saved.'))

    def step_shipping(self, apply: bool):
        from apps.core.constants.model_registry import MODEL_REGISTRY
        from common.schemas.transaction_envelopes import TransactionShipping

        self.stdout.write('shipping:')
        for key in SHIPPING_MODELS:
            model = MODEL_REGISTRY[key].import_model()
            reshaped = 0
            for pk, old in model.objects.values_list('id', 'shipping').iterator():
                old = old or {}
                new = dict(old)
                new['ship_to'] = _ship_to_snapshot(old.get('ship_to') or {})
                new['dt_shipped'] = _epoch_or_none(old.get('dt_shipped'))
                new['dt_delivered'] = _epoch_or_none(old.get('dt_delivered'))
                new = TransactionShipping.model_validate(new).model_dump()
                if new != old:
                    reshaped += 1
                    if apply:
                        model.objects.filter(pk=pk).update(shipping=new)
            self.stdout.write(f'  {key}: {reshaped} records reshaped')
        n = rename_paths_in_settings(SHIPPING_PATH_RENAMES, self.stdout, apply)
        self.stdout.write(f'  settings: {n} records with flat shipping paths')

    AGENT_KEYS = ('source_agent', 'capacity', 'hypothesis_id', 'confidence',
                  'requires_human', 'requires_claude', 'sprint_week', 'claude_prompt',
                  'claude_response', 'claude_usage', 'claude_error', 'result')
    STAMP_FIELDS = ('created_by', 'updated_by', 'start_by', 'deadline_by',
                    'expected_by', 'completed_by', 'end_by')

    def step_action(self, apply: bool):
        from apps.core.constants.model_registry import MODEL_REGISTRY
        from apps.core.models.action_pydantic import ActionMetadata
        from common.schemas.action_aspects import LocalizedText, UserStamp

        Action = MODEL_REGISTRY['action'].import_model()
        self.stdout.write('action:')
        counts = dict(text=0, agent=0, languages=0, stamps=0)
        from types import SimpleNamespace
        cols = ('id', 'action', 'description', 'languages', 'metadata', *self.STAMP_FIELDS)
        for row in Action.objects.values(*cols).iterator():
            rec = SimpleNamespace(pk=row['id'], **row)
            update = {}
            act = rec.action
            if isinstance(act, dict) and 'title' in act:
                meta = dict(rec.metadata or {})
                meta['agent'] = True
                for k in self.AGENT_KEYS:
                    if k in act:
                        meta[k] = act[k]
                if act.get('completed_at'):
                    from datetime import datetime
                    meta['dt_completed'] = int(datetime.fromisoformat(
                        act['completed_at'].replace('Z', '+00:00')).timestamp() * 1000)
                update['metadata'] = ActionMetadata.model_validate(meta).model_dump()
                update['action'] = LocalizedText(en=act.get('title', '')).model_dump()
                counts['agent'] += 1
            elif isinstance(act, str):
                update['action'] = LocalizedText(en=act).model_dump()
                counts['text'] += 1
            desc = rec.description
            if isinstance(desc, str):
                update['description'] = LocalizedText(en=desc).model_dump()
                counts['text'] += 1
            elif isinstance(desc, dict) and ('summary' in desc or 'proposed_by' in desc):
                update['description'] = LocalizedText(
                    en=desc.get('en') or desc.get('summary', '')).model_dump()
                counts['text'] += 1
            if not isinstance(rec.languages, list):
                update['languages'] = []
                counts['languages'] += 1
            for f in self.STAMP_FIELDS:
                stamps = getattr(rec, f)
                if not isinstance(stamps, list):
                    continue
                fixed = []
                for st in stamps:
                    st = dict(st or {})
                    if st.get('id') is not None and not str(st['id']).isdigit():
                        st['id'] = None
                    fixed.append(UserStamp.model_validate(st).model_dump())
                if fixed != stamps:
                    update[f] = fixed
                    counts['stamps'] += 1
            if update and apply:
                Action.objects.filter(pk=rec.pk).update(**update)
        self.stdout.write('  ' + ', '.join(f'{k}: {v}' for k, v in counts.items()))

    def step_records(self, apply: bool):
        from apps.core.constants.model_registry import MODEL_REGISTRY
        from apps.core.services.field_leaves import ORG_MODELS
        from common.schemas.record_aspects import (
            DocumentPath, PeriodMetrics, ProjectLogistics, ProjectObjective, ProjectTasks)

        self.stdout.write('records:')
        Project = MODEL_REGISTRY['project'].import_model()
        n = 0
        from types import SimpleNamespace
        for row in Project.objects.values('id', 'objective', 'tasks', 'logistics').iterator():
            rec = SimpleNamespace(pk=row['id'], **row)
            update = {}
            obj = rec.objective
            if isinstance(obj, str):
                obj = {'summary': obj}
            if isinstance(obj, dict) and ('goal' in obj or 'success_criteria' in obj):
                obj = dict(obj)
                goal = obj.pop('goal', '')
                crit = obj.pop('success_criteria', '')
                obj['summary'] = obj.get('summary') or goal
                obj.setdefault('success', {})
                obj['success'] = dict(obj['success'])
                obj['success']['definition'] = obj['success'].get('definition') or crit
            if obj != rec.objective:
                update['objective'] = ProjectObjective.model_validate(obj or {}).model_dump(by_alias=True)
            for field, cls in (('tasks', ProjectTasks), ('logistics', ProjectLogistics)):
                val = getattr(rec, field)
                if isinstance(val, str):
                    update[field] = cls(notes=val).model_dump()
            if update:
                n += 1
                if apply:
                    Project.objects.filter(pk=rec.pk).update(**update)
        self.stdout.write(f'  project: {n} records reshaped')

        Document = MODEL_REGISTRY['document'].import_model()
        n = 0
        for pk, p in Document.objects.values_list('id', 'path').iterator():
            if isinstance(p, dict) and ('wc2_note' in p or 'ask_bill' in p):
                p = dict(p)
                extra = [p.pop('wc2_note', ''), p.pop('ask_bill', '')]
                p['description'] = '\n'.join(x for x in [p.get('description', '')] + extra if x)
                n += 1
                if apply:
                    Document.objects.filter(pk=pk).update(
                        path=DocumentPath.model_validate(p).model_dump())
        self.stdout.write(f'  document: {n} records reshaped')

        n = 0
        for key in ORG_MODELS:
            Model = MODEL_REGISTRY[key].import_model()
            for pk, m in Model.objects.values_list('id', 'metrics').iterator():
                original = m
                if not isinstance(m, dict):
                    continue
                periods = m.get('periods')
                if isinstance(periods, dict) or 'counts' not in m:
                    m = dict(m)
                    if isinstance(periods, dict):
                        m['periods'] = [{'period': k, **(v or {})} for k, v in periods.items()]
                    new = PeriodMetrics.model_validate(m).model_dump()
                    if new != original:
                        n += 1
                        if apply:
                            Model.objects.filter(pk=pk).update(metrics=new)
        self.stdout.write(f'  org metrics: {n} records reshaped')
