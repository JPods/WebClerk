"""Calculated fields — defined in data, worked out by the server (Bill, 2026-11-01: users insert
values they want calculated in rows; "sum.cost by sub.components").

A model's wc:model Setting holds them in config.calculated, by name:

    {"lines_amount": {"calc": "sum", "of": "totals.amount", "over": "lines"}}

  calc  sum | count | min | max | average
  over  a relation to many rows of another model: its accessor (an order's "lines", an item's
        "bom_parent" — the BOM lines it is the parent of)
  of    the field on those rows; a dot path reads into a JSON field (totals.amount)

A list names a calculated field like any other column. The list read works the values out for
the page it returns, in one grouped query — never per row, never in the browser. A value through
several levels (a BOM's cost down to its parts) is a tree's rollup (tree_calc), not this.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from django.db import models
from django.db.models import Avg, Count, DecimalField, F, Max, Min, Sum
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast

from apps.core.services import definition

CALCS = {'sum': Sum, 'count': Count, 'min': Min, 'max': Max, 'average': Avg}
NAME = re.compile(r'^[a-z][a-z0-9_]{0,62}$')
NUMERIC = (models.DecimalField, models.FloatField, models.IntegerField, models.BigIntegerField,
           models.PositiveIntegerField, models.SmallIntegerField, models.PositiveSmallIntegerField)


def relations(ModelCls) -> dict[str, Any]:
    """The relations to many rows a calculated field may sum over, by accessor."""
    return {r.get_accessor_name(): r for r in ModelCls._meta.related_objects if r.one_to_many}


def problem(ModelCls, name: str, spec: Any) -> Optional[str]:
    """Why a definition cannot be worked out, or None when it can."""
    if not isinstance(name, str) or not NAME.match(name):
        return f'{name!r}: a name is lowercase letters, digits and _'
    if any(f.name == name or f.attname == name for f in ModelCls._meta.concrete_fields):
        return f'{name}: already a field of {ModelCls._meta.model_name}'
    if not isinstance(spec, dict):
        return f'{name}: a definition is {{calc, of, over}}'
    if spec.get('calc') not in CALCS:
        return f"{name}: calc is one of {', '.join(CALCS)}"
    rel = relations(ModelCls).get(spec.get('over'))
    if rel is None:
        return f"{name}: over is one of {', '.join(sorted(relations(ModelCls)))}"
    of = spec.get('of')
    if spec['calc'] == 'count' and not of:
        return None
    if not isinstance(of, str) or not of:
        return f'{name}: of names a field of {rel.related_model._meta.model_name}'
    head = of.split('.')[0]
    try:
        field = rel.related_model._meta.get_field(head)
    except Exception:  # noqa: BLE001 - FieldDoesNotExist
        return f'{name}: {rel.related_model._meta.model_name} has no field {head}'
    if '.' in of:
        if not isinstance(field, models.JSONField):
            return f'{name}: {head} is not a JSON field, so {of} has no parts'
    elif spec['calc'] != 'count' and not isinstance(field, NUMERIC):
        return f'{name}: {of} is not a number'
    return None


def _expression(ModelCls, spec: dict):
    rel = relations(ModelCls)[spec['over']]
    of = spec.get('of')
    if spec['calc'] == 'count' and not of:
        return Count(rel.name)
    head, *keys = of.split('.')
    if not keys:
        return CALCS[spec['calc']](f'{rel.name}__{head}')
    # Into a JSON column of the related rows: the column across the relation, then its keys.
    expr = F(f'{rel.name}__{head}')
    for k in keys[:-1]:
        expr = KeyTransform(k, expr)
    return CALCS[spec['calc']](Cast(KeyTextTransform(keys[-1], expr), DecimalField(max_digits=20, decimal_places=6)))


def _defined(raw) -> dict:
    return raw if isinstance(raw, dict) else {}


def defined(model_key: str) -> dict:
    """config.calculated of a model, as stored."""
    from apps.core.services.access import model_key as key_of
    return definition.part(key_of(model_key) or model_key, ('calculated',), _defined)


def _may_see(actor, ModelCls, spec: dict) -> bool:
    """A calculated value shows only to a role that may see what it is made of: the rows' field
    (a sum of line costs is cost)."""
    from apps.core.services.field_projection import filter_response_data
    from apps.core.constants.model_registry import to_model_name
    rel = relations(ModelCls)[spec['over']]
    parts = (spec.get('of') or 'id').split('.')
    probe: Any = 0
    for k in reversed(parts):            # op_data.run_time → {'op_data': {'run_time': 0}}
        probe = {k: probe}
    related = to_model_name(rel.related_model) or rel.related_model._meta.model_name
    seen: Any = filter_response_data(actor, related, probe) or {}
    for k in parts:                      # every leaf of the path must survive the role's filter
        if not isinstance(seen, dict) or k not in seen:
            return False
        seen = seen[k]
    return True


def values(model_key: str, ModelCls, ids: list, actor=None) -> dict[Any, dict]:
    """{pk: {name: value}} for these rows: one grouped query for every definition that can be
    worked out and this actor may see (one that cannot is skipped — the editor says why)."""
    specs = {n: s for n, s in defined(model_key).items()
             if problem(ModelCls, n, s) is None and (actor is None or _may_see(actor, ModelCls, s))}
    if not specs or not ids:
        return {}
    rows = (ModelCls._base_manager.filter(pk__in=ids).order_by()
            .values('pk').annotate(**{n: _expression(ModelCls, s) for n, s in specs.items()}))
    return {r.pop('pk'): {n: (float(v) if v is not None and not isinstance(v, int) else v) for n, v in r.items()}
            for r in rows}


def offer(ModelCls) -> list[dict]:
    """What a calculated field can be made of: each relation to many rows, with the number fields
    and JSON fields on those rows (a JSON field takes a dot path: totals.amount)."""
    out = []
    for accessor, rel in sorted(relations(ModelCls).items()):
        fields = [f.name for f in rel.related_model._meta.concrete_fields
                  if isinstance(f, NUMERIC) and not f.primary_key and not f.is_relation]
        json = [f.name for f in rel.related_model._meta.concrete_fields if isinstance(f, models.JSONField)]
        out.append({'over': accessor, 'model': rel.related_model._meta.model_name,
                    'numbers': fields, 'json': json})
    return out


def change(model_key: str, name: str, spec: Optional[dict], *, actor) -> dict:
    """Define (spec) or remove (None) one calculated field on the model's definition. Staff only,
    as a definition's lists and layouts are; a definition that cannot be worked out is refused."""
    from django.db import transaction

    from apps.core.models import Setting
    from apps.core.services.access import model_key as key_of
    from apps.core.services.door import Refused
    from apps.core.constants.model_registry import import_model
    key = key_of(model_key) or model_key
    if not definition.may_change(actor):
        raise Refused(403, 'calculated_edit_forbidden', 'Only staff define a calculated field.', {'model_name': key})
    ModelCls = import_model(key)
    if spec is not None:
        why = problem(ModelCls, name, spec)
        if why:
            raise Refused(400, 'calculated_invalid', why, {'model_name': key, 'name': name})
        spec = {k: spec[k] for k in ('calc', 'of', 'over') if spec.get(k)}
    with transaction.atomic():
        row = (Setting.objects.select_for_update()
               .filter(purpose='wc:model', parent_model=key).order_by('id').first())
        if row is None:
            raise Refused(404, 'no_definition', f'{key} has no model definition.', {'model_name': key})
        config = dict(row.config or {})
        calc = dict(config.get('calculated') or {})
        if spec is None:
            calc.pop(name, None)
        else:
            calc[name] = spec
        config['calculated'] = calc
        Setting.objects.filter(pk=row.pk).update(config=config)
    definition.clear(key)
    return calc


# ── Commands on a model's definition: POST /wcapi/setting/<id>/calculated[_offer]/ ──────────

def _definition_model(ctx):
    from apps.core.services.door import Refused
    from apps.core.constants.model_registry import import_model
    if ctx.obj is None or getattr(ctx.obj, 'purpose', None) != 'wc:model':
        raise Refused(400, 'not_a_definition', 'Calculated fields belong to a model definition (a wc:model Setting).')
    key = ctx.obj.parent_model
    return key, import_model(key)


def _state(key: str, ModelCls) -> dict:
    stored = defined(key)
    problems = {n: problem(ModelCls, n, s) for n, s in stored.items()}
    return {'model': key, 'defined': stored, 'problems': {n: p for n, p in problems.items() if p}}


def calculated_offer(ctx) -> dict:
    """The model's calculated fields, which cannot be worked out and why, and what one can be
    made of. Writes nothing."""
    key, ModelCls = _definition_model(ctx)
    return {**_state(key, ModelCls), 'offer': offer(ModelCls)}


def calculated_command(ctx) -> dict:
    """{name, spec}: define the field; spec null removes it."""
    from apps.core.services.door import Refused
    key, ModelCls = _definition_model(ctx)
    spec = ctx.data.get('spec')
    if spec is not None and not isinstance(spec, dict):
        raise Refused(400, 'calculated_invalid', 'spec is {calc, of, over}, or null to remove.')
    change(key, str(ctx.data.get('name') or ''), spec, actor=ctx.actor)
    return _state(key, ModelCls)


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('setting', 'calculated', calculated_command)
    register_command('setting', 'calculated_offer', calculated_offer)
