"""What a document's parent is worth and what is left on it, for the child's screen.

Bill, 2026-11-08: "In the invoice it is ok to have in financials the order value and unfilled
value of the remaining order. But the totals ... details should be just for this specific
invoice." Served on a GET (payload['parent_summary']), never stored and never saved back; every
figure in the child's own ``totals`` stays the child's. The unfilled value is the server's:
Σ remaining × the line's discounted unit (its cost unit on the buy side) over the parent's lines.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from django.apps import apps

_PARENTS = {'quote': 'Quote', 'order': 'Order', 'invoice': 'Invoice', 'purchase': 'Purchase'}


def parent_summary(obj) -> Optional[Dict[str, Any]]:
    parent_model = getattr(obj, 'parent_model', None)
    parent_id = getattr(obj, 'parent_id', None)
    if not parent_model or not parent_id or parent_model not in _PARENTS:
        return None
    parent = apps.get_model('transactions', _PARENTS[parent_model]).objects.filter(pk=parent_id).first()
    if parent is None:
        return None
    totals = parent.totals if isinstance(parent.totals, dict) else {}
    unfilled = Decimal('0')
    for line in parent.lines.all():
        quantity = line.quantity if isinstance(line.quantity, dict) else {}
        remaining = Decimal(str(quantity.get('remaining') or 0))
        if remaining <= 0:
            continue
        line_totals = line.totals if isinstance(getattr(line, 'totals', None), dict) else {}
        unit = line_totals.get('discounted_unit')
        if unit is None:
            envelope = getattr(line, 'price', None) if hasattr(line, 'price') else getattr(line, 'cost', None)
            unit = (envelope or {}).get('unit') if isinstance(envelope, dict) else None
        unfilled += remaining * Decimal(str(unit or 0))
    return {
        'model': parent_model, 'id': parent.pk, 'ida': parent.ida, 'status': parent.status,
        'amount': float(totals.get('amount') or 0), 'total': float(totals.get('total') or 0),
        'unfilled': float(unfilled.quantize(Decimal('0.01'))),
    }
