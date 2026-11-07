"""The sweep: existing records get the defaults they were born without (readme 106 rule 4;
Bill, 2026-11-07: "loop through them and fix them").

A document the lock covers is never filled (the lead's review): locked, journalized, released
or terminal (complete, canceled, paid, voided) — setting terms on an invoice after the books
took it moves its due date and its aging, the money effect the lock exists to stop. They are
reported as kept, with why; Alice may coach them. An open document gets dt_created + days.

A record is filled at the moment it is named (core/services/defaults.fill_defaults); a record
made before that rule, or outside the door, has blanks. The sweep finds, per model and field,
the records whose default field is blank and the records whose value is off the field's list.
Blanks are repaired (``apply``): the model's default, a dt_ field as the record's dt_created
plus the days. A value off its list is never rewritten — it is reported for a person (Alice's
check coaches the owner; watch_defaults). Training rows (zz/qq idas) are never touched.

Also the company profile's prefs.currency: code, locale and symbol there are read by nothing
since the stored formatting (config.defaults.formatting on each definition) took over; the
sweep drops those three keys and keeps the per-field precisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DAY_MS = 86_400_000
#: The profile prefs.currency keys nothing reads since the stored formatting (9c48a00).
UNREAD_CURRENCY_KEYS = ('code', 'locale', 'symbol')


#: Documents past the point the sweep may touch: the lock (status locked, metadata.health.lock),
#: the journal (dt_journaled), release and the terminal statuses.
KEPT_STATUSES = ('locked', 'released', 'complete', 'canceled', 'paid', 'voided')


@dataclass
class Finding:
    model: str
    field: str
    kind: str                       # blank | kept | unlisted | profile
    count: int
    value: Any = None               # the default that would be written (blank), or the off-list value
    ids: List[int] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {'model': self.model, 'field': self.field, 'kind': self.kind, 'count': self.count,
                'value': self.value, 'ids': list(self.ids)}


def _model(model_key: str):
    from apps.core.utils import registry
    resolved = registry.resolve(model_key)
    if resolved is None:
        return None
    return resolved if hasattr(resolved, '_meta') else resolved.import_model()


def _blank(model, name):
    """The filter for a blank field: null, and for text the empty string too."""
    from django.db.models import CharField, Q, TextField
    field = model._meta.get_field(name)
    q = Q(**{f'{name}__isnull': True})
    return q | Q(**{name: ''}) if isinstance(field, (CharField, TextField)) else q


def _kept(model):
    """The filter for records the sweep never writes: a lockable document that is locked,
    journalized, released or terminal. None for a model the lock does not cover."""
    from django.db.models import Q
    from apps.transactions.services.document_lock import LOCKABLE_MODELS
    key = model._meta.model_name
    if key not in LOCKABLE_MODELS and key != 'workorder':
        return None
    names = {f.name for f in model._meta.concrete_fields}
    q = Q(status__in=KEPT_STATUSES) if 'status' in names else Q(pk__in=[])
    if 'dt_journaled' in names:
        q |= Q(dt_journaled__isnull=False) & ~Q(dt_journaled=0)
    if 'metadata' in names:
        q |= Q(metadata__health__has_key='lock')
    return q


def _models_with_defaults() -> Dict[str, Dict[str, Any]]:
    """{model_key: fields block} for every definition that holds one."""
    from apps.core.models import Setting
    from apps.core.services.defaults import model_defaults
    out = {}
    for key in Setting.objects.filter(purpose='wc:model').values_list('parent_model', flat=True):
        block = model_defaults(key) if key else {}
        if block:
            out[key] = block
    return out


def find_blanks(limit_ids: int = 20) -> List[Finding]:
    """Per model and default field: the tallied records whose field is blank."""
    from apps.core.services.defaults import resolve
    from apps.core.services.tally import tallied
    findings: List[Finding] = []
    for key, block in _models_with_defaults().items():
        model = _model(key)
        if model is None:
            continue
        names = {f.name for f in model._meta.concrete_fields}
        for raw, value in block.items():
            name, _ = resolve(raw, value)
            if name not in names:
                continue
            blank = tallied(model.objects.all()).filter(_blank(model, name))
            kept_q = _kept(model)
            # Exclude by pk, not by the negated Q: a null metadata.health makes the JSON test
            # NULL, and NOT (… OR NULL) drops the open rows from both sides.
            open_qs = blank.exclude(pk__in=blank.filter(kept_q).values('pk')) if kept_q is not None else blank
            shown = raw if raw.endswith('_days') else value
            count = open_qs.count()
            if count:
                findings.append(Finding(key, name, 'blank', count, shown,
                                        list(open_qs.order_by('pk').values_list('pk', flat=True)[:limit_ids])))
            if kept_q is not None:
                kept_qs = blank.filter(kept_q)
                kept = kept_qs.count()
                if kept:
                    findings.append(Finding(key, name, 'kept', kept, shown,
                                            list(kept_qs.order_by('pk').values_list('pk', flat=True)[:limit_ids])))
    return findings


def find_unlisted(limit_ids: int = 20) -> List[Finding]:
    """Per model and default field with a list: the stored values that are not on it."""
    from django.db.models import Count
    from apps.core.services import select_lists
    from apps.core.services.tally import tallied
    findings: List[Finding] = []
    for key, block in _models_with_defaults().items():
        model = _model(key)
        if model is None:
            continue
        names = {f.name for f in model._meta.concrete_fields}
        lists = select_lists.lists(key)
        for name in block:
            listed = lists.get(name)
            if name not in names or not listed:
                continue
            allowed = {str(v).lower() for v in listed}
            rows = (tallied(model.objects.all()).exclude(**{f'{name}__isnull': True}).exclude(**{name: ''})
                    .values(name).annotate(n=Count('pk')).order_by('-n'))
            for row in rows:
                value = row[name]
                if str(value).lower() in allowed:
                    continue
                ids = list(tallied(model.objects.all()).filter(**{name: value}).order_by('pk').values_list('pk', flat=True)[:limit_ids])
                findings.append(Finding(key, name, 'unlisted', row['n'], value, ids))
    return findings


def find_profile_currency() -> List[Finding]:
    from apps.core.models import Setting
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    currency = (company.prefs or {}).get('currency') if company and isinstance(company.prefs, dict) else None
    if not isinstance(currency, dict):
        return []
    stale = [k for k in UNREAD_CURRENCY_KEYS if k in currency]
    return [Finding('setting', 'prefs.currency', 'profile', 1, stale, [company.pk])] if stale else []


def find_all() -> List[Finding]:
    return find_blanks() + find_unlisted() + find_profile_currency()


def apply(findings: List[Finding]) -> Dict[str, int]:
    """Repair the open blanks and the profile; kept documents and unlisted values are left for
    a person. Every write bumps version and dt_modified, so a form open on a swept record meets
    the version check instead of saving over the fill. Returns {'<model>.<field>': rows written}."""
    import time
    from django.db.models import F
    from apps.core.models import Setting
    from apps.core.services.defaults import model_defaults, named_term
    from apps.core.services.tally import tallied
    written: Dict[str, int] = {}
    now_ms = int(time.time() * 1000)
    for finding in findings:
        if finding.kind == 'blank':
            model = _model(finding.model)
            block = model_defaults(finding.model)
            raw = finding.value if isinstance(finding.value, str) and finding.value.endswith('_days') else finding.field
            value = block.get(raw)
            if model is None or value in (None, ''):
                continue
            qs = tallied(model.objects.all()).filter(_blank(model, finding.field))
            kept_q = _kept(model)
            if kept_q is not None:
                qs = qs.exclude(pk__in=qs.filter(kept_q).values('pk'))
            stamp = {'version': F('version') + 1, 'dt_modified': now_ms}
            if raw.endswith('_days'):
                # Born + days, from the record's own birth; a record with no dt_created is left.
                n = qs.exclude(dt_created__isnull=True).update(**{finding.field: F('dt_created') + int(float(value)) * DAY_MS}, **stamp)
            else:
                n = qs.update(**{finding.field: named_term(value) if finding.field == 'terms' else value}, **stamp)
            written[f'{finding.model}.{finding.field}'] = written.get(f'{finding.model}.{finding.field}', 0) + n
        elif finding.kind == 'profile':
            company = Setting.objects.filter(pk=finding.ids[0]).first()
            if company is None or not isinstance(company.prefs, dict):
                continue
            currency = {k: v for k, v in (company.prefs.get('currency') or {}).items() if k not in UNREAD_CURRENCY_KEYS}
            company.prefs = {**company.prefs, 'currency': currency}
            company._setting_create_authorized = True
            company.save()
            written['setting.prefs.currency'] = 1
    return written
