"""Dashboard card figures, computed by the server over every row the asker may see.

A dd_card (seed_dd_cards, the wc:dd_card Setting) names a model, filters, metrics and an optional
distribution. The browser used to fetch 500 rows and add them up itself, reading r['total'] on a
record that carries totals.total, so every card said $0.00 (FAULT 20261103T221823). The server is
the source of truth (Bill, 2026-11-04); the browser only formats what comes back.

A metric field is a concrete field ('amount') or a path into a JSON field ('totals.total').
A name the model lacks is refused with the path it probably meant.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Avg, Count, F, FloatField, JSONField, Q, Sum
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

from apps.core.constants.model_registry import get_model_meta
from apps.core.services import access
from apps.core.services.door import Refused, as_actor
from apps.core.services.role_filter import inject_role_filters


def _number(value) -> float | int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def _expression(model, model_key: str, path: str):
    """The ORM expression for a metric field: the column, or the JSON key cast to a number."""
    root, _, rest = path.partition('.')
    try:
        field = model._meta.get_field(root)
    except Exception:
        field = None
    if field is None or not getattr(field, 'concrete', False):
        hint = ''
        if 'totals' in {f.name for f in model._meta.concrete_fields} and '.' not in path:
            hint = f" A transaction's figures are in totals: 'totals.{path}'."
        raise Refused(400, 'unknown_field', f"{model_key} has no field '{path}'.{hint}",
                      {'model_name': model_key, 'field': path})
    if not rest:
        return F(root)
    if not isinstance(field, JSONField):
        raise Refused(400, 'unknown_field', f"{model_key}.{root} is not JSON; '{path}' has no keys.",
                      {'model_name': model_key, 'field': path})
    expr = root
    for key in rest.split('.'):
        expr = KeyTextTransform(key, expr)
    return Cast(expr, FloatField())


def _sum(qs, expr) -> float:
    return _number(qs.annotate(_v=expr).aggregate(s=Sum('_v'))['s'])


def _metric(qs, model, model_key, m: dict) -> dict:
    agg = m.get('agg')
    if m.get('filters'):
        qs = qs.filter(**m['filters'])
    if agg == 'count':
        value: float | int = qs.count()
    elif agg == 'sum':
        value = _sum(qs, _expression(model, model_key, m['field']))
    elif agg == 'avg':
        value = _number(qs.annotate(_v=_expression(model, model_key, m['field'])).aggregate(a=Avg('_v'))['a'])
    elif agg in ('margin_pct', 'pct'):
        first, second = (m.get('fields') or [None, None])[:2]
        a = _sum(qs, _expression(model, model_key, first))
        b = _sum(qs, _expression(model, model_key, second))
        if agg == 'margin_pct':
            value = (a - b) / a * 100 if a > 0 else 0
        else:
            value = a / b * 100 if b > 0 else 0
            if m.get('invert'):
                value = 100 - value
    else:
        raise Refused(400, 'unknown_agg', f"A card metric is count, sum, avg, margin_pct or pct, not '{agg}'.",
                      {'model_name': model_key, 'agg': agg})
    out = {'label': m.get('label', ''), 'value': value}
    if m.get('format'):
        out['format'] = m['format']
    return out


def _distribution(qs, model, model_key, dist: dict) -> list[dict]:
    field = dist.get('field') or ''
    labels = list(dist.get('labels') or [])
    if dist.get('type') == 'category':
        _expression(model, model_key, field)
        return [{'label': label, 'count': qs.filter(**{field.replace('.', '__'): label}).count()} for label in labels]
    buckets = list(dist.get('buckets') or [])
    qs = qs.annotate(_v=_expression(model, model_key, field))
    edges = [None] + buckets + [None]
    out = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        q = Q()
        if lo is not None:
            q &= Q(_v__gte=lo)
        if hi is not None:
            q &= Q(_v__lt=hi)
        out.append({'label': labels[i] if i < len(labels) else f'{lo}-{hi}',
                    'count': qs.filter(q).count()})
    return out


def card_metrics(params: dict, actor) -> dict[str, Any]:
    """{'metrics': [{label, value, format?}], 'distribution': [{label, count}]} for one card."""
    actor = as_actor(actor)
    model_key = access.model_key(params.get('model') or '')
    meta = get_model_meta(model_key) if model_key else None
    if meta is None:
        raise Refused(404, 'unknown_model', f"No model '{params.get('model')}' for a card.",
                      {'model_name': params.get('model')})
    model = meta.import_model()
    filters = dict(params.get('filters') or {})
    qs = model.objects.filter(inject_role_filters(actor, model_key, Q(**filters)))
    metrics = [_metric(qs, model, model_key, m) for m in (params.get('metrics') or [])]
    distribution = _distribution(qs, model, model_key, params['distribution']) if params.get('distribution') else []
    return {'metrics': metrics, 'distribution': distribution}
