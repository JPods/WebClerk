"""close_transaction — the one door a commitment leaves through.

Bill, 2026-09-19: *"We should make a close transaction function that clears its
commitments. We can have Alice ask users each week to close out transactions more than
x old."*

A quote, order, purchase or workorder commits quantity when its lines are written
(on_qt, on_so, on_po, on_wo). Until now nothing took that quantity back unless someone
deleted the lines one at a time, so abandoned and quietly-finished documents held
inventory forever. Cancel, complete, close and soft-delete all come through here; none
of them writes buckets itself.

What is released is each line's **remaining**, never its active: remaining is what has
not moved downstream, and releasing active double-releases every line that was partly
converted.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from django.apps import apps as dj_apps
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from apps.transactions.models.base_line_model import quantity_bucket_deltas

logger = logging.getLogger(__name__)

#: the documents that hold a commitment, and the pending type that named it
COMMITMENT_TYPE: Dict[str, str] = {
    'quote': 'QT',
    'order': 'SO',
    'purchase': 'PO',
    'workorder': 'WO',
}

#: an invoice or a receipt records a movement that already happened; closing one
#: settles its status and releases nothing.
NO_COMMITMENT = ('invoice', 'receipt', 'cash')

CLOSED_STATUSES = ('complete', 'canceled')


def _item_id(line) -> Optional[int]:
    item = line.item if isinstance(getattr(line, 'item', None), dict) else {}
    for key in ('item_id', 'id_num', 'id'):
        raw = item.get(key)
        if raw:
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    return getattr(line, 'item_fk_id', None)


def _warn_if_negative(item_id: int, bucket: str, delta: float, model_name: str, header) -> None:
    """A release that drives a bucket below zero means the bucket never held what the
    document committed. Say so — never clamp (Axiom 6: no silent degradation)."""
    Item = dj_apps.get_model('products', 'Item')
    item = Item.objects.filter(pk=item_id).only('quantity').first()
    if item is None:
        return
    current = float((item.quantity or {}).get(bucket) or 0)
    if current + delta < -0.000001:
        logger.warning(
            "[close] %s %s: releasing %.4f from item %s %s would take it to %.4f — the bucket "
            "never held what this document committed; reconcile rather than clamp",
            model_name, getattr(header, 'ida', None) or header.pk, delta, item_id, bucket,
            current + delta,
        )


def close_transaction(model_name: str, pk: int, *, reason: str, acted_by: str,
                      status: str = 'complete') -> Dict[str, Any]:
    """Close a document and release whatever it still commits.

    Returns {'closed': bool, 'status', 'released': {bucket: qty}, 'lines': n,
    'already_closed': bool}. Re-closing is a no-op that returns the recorded close.
    """
    model_name = (model_name or '').lower()
    if status not in CLOSED_STATUSES:
        raise ValidationError({'status': f"close status must be one of {CLOSED_STATUSES}"})
    if not reason or not acted_by:
        raise ValidationError({'reason': 'reason and acted_by are required — a close records who and why'})

    try:
        Model = dj_apps.get_model('transactions', model_name)
    except LookupError as exc:
        raise ValidationError({'model_name': f'unknown transaction model {model_name}'}) from exc

    Pending = dj_apps.get_model('core', 'Pending')
    released: Dict[str, float] = {}
    line_count = 0

    with db_transaction.atomic():
        header = Model.objects.select_for_update().filter(pk=pk).first()
        if header is None:
            raise ValidationError({'id': f'{model_name} #{pk} not found'})

        meta = header.metadata if isinstance(header.metadata, dict) else {}
        if meta.get('closed'):
            return {'closed': True, 'already_closed': True, 'status': header.status,
                    'released': meta['closed'].get('released', {}), 'lines': 0}

        pending_type = COMMITMENT_TYPE.get(model_name)
        if getattr(header, 'kind', '') == 'count':
            pending_type = None          # a count committed nothing to release
        if pending_type and hasattr(header, 'lines'):
            for line in header.lines.filter(is_deleted=False):
                quantity = line.quantity if isinstance(line.quantity, dict) else {}
                remaining = float(quantity.get('remaining') or 0)
                if not remaining:
                    continue
                item_id = _item_id(line)
                if not item_id:
                    logger.warning("[close] %s #%s line %s has no item — nothing to release",
                                   model_name, pk, line.pk)
                    continue

                deltas = quantity_bucket_deltas(pending_type, -remaining, header)
                Pending.objects.create(
                    model_name='item',
                    record_id=str(item_id),
                    purpose='inventory_qty_change',
                    name=f"close {model_name} {header.ida or pk} - line {line.line_number or line.pk}",
                    changes={k: v for k, v in deltas.items() if v},
                    config={'item_id': item_id, 'source_type': f'{model_name}_close',
                            'source_id': pk, 'source_line_id': line.pk,
                            'reason': reason, 'closed_by': acted_by},
                )
                for bucket, value in deltas.items():
                    if value:
                        released[bucket] = round(released.get(bucket, 0) + value, 6)
                        _warn_if_negative(item_id, bucket, value, model_name, header)

                # is_complete makes remaining 0 through the one writer, so a line can
                # never release twice.
                quantity['is_complete'] = True
                line.quantity = quantity
                line.save(update_fields=['quantity', 'dt_modified', 'version'])
                line_count += 1

        header.status = status
        header.metadata = {**meta, 'closed': {
            'dt': datetime.now(timezone.utc).isoformat(),
            'by': acted_by,
            'reason': reason,
            'status': status,
            'released': released,
        }}
        header.save(update_fields=['status', 'metadata', 'dt_modified', 'version'])

    logger.info("[close] %s #%s closed by %s (%s); released %s across %s line(s)",
                model_name, pk, acted_by, reason, released or '{}', line_count)
    return {'closed': True, 'already_closed': False, 'status': status,
            'released': released, 'lines': line_count}


def stale_commitments(days: int = 30, now_ms: Optional[int] = None) -> list[dict]:
    """Documents older than `days` that still hold a commitment — Alice's weekly list.

    She raises it and asks; she never closes on her own.
    """
    import time
    now_ms = now_ms or int(time.time() * 1000)
    cutoff = now_ms - days * 86_400_000
    out = []
    for model_name, pending_type in COMMITMENT_TYPE.items():
        Model = dj_apps.get_model('transactions', model_name)
        rows = (Model.objects.filter(is_deleted=False, dt_created__lt=cutoff)
                .exclude(status__in=CLOSED_STATUSES))
        if model_name == 'workorder':
            rows = rows.exclude(kind='count')       # a count holds no commitment
        for header in rows:
            holding = 0.0
            for line in header.lines.filter(is_deleted=False):
                quantity = line.quantity if isinstance(line.quantity, dict) else {}
                holding += float(quantity.get('remaining') or 0)
            if holding:
                out.append({
                    'model': model_name, 'id': header.pk, 'ida': header.ida,
                    'status': header.status, 'dt_created': header.dt_created,
                    'age_days': int((now_ms - (header.dt_created or now_ms)) / 86_400_000),
                    'bucket': f"on_{pending_type.lower()}", 'holding': round(holding, 4),
                })
    return sorted(out, key=lambda r: -r['age_days'])


__all__ = ['close_transaction', 'stale_commitments', 'COMMITMENT_TYPE']
