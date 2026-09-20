"""Parent-child line quantities — the one place a child reaches its parent line.

Definitions: readmes/transactions/line-quantity.md

Parent-child exists for two pairs only:
    quote_line -> order_line
    order_line    -> invoice_line

The child stores parent_line_id; the child's model names the parent table.
The parent's remaining is always recomputed from its children, never decremented:

    parent.remaining = parent.active − Σ child.active

Every other conversion (order -> purchase, clone, cross-type, split) is history in
refs.source only and never touches a source line's quantity or status.
"""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional, Tuple

from django.apps import apps
from django.db import transaction
from django.db.models import Count, DecimalField, Sum
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

logger = logging.getLogger(__name__)

#: child line model -> (parent line model, refs.source key naming the parent line)
PARENT_OF: Dict[str, Tuple[str, str]] = {
    'orderline': ('QuoteLine', 'quote_line_id'),
    'invoiceline': ('OrderLine', 'order_line_id'),
    # The buy chain works like the sell chain (Bill, 2026-09-19): receiving a purchase
    # line reduces its remaining through the one writer, never through a 'received' hint.
    'receiptline': ('PurchaseLine', 'purchase_line_id'),
}

#: parent line model -> child line model
CHILD_OF: Dict[str, str] = {
    'quoteline': 'OrderLine',
    'orderline': 'InvoiceLine',
    'purchaseline': 'ReceiptLine',
}

TRANSFERRED = 'transferred'


def _model(name: str):
    return apps.get_model('transactions', name)


def parent_line_id_from_refs(line: Any) -> Optional[int]:
    """The parent line id named in refs.source for this child model, or None."""
    spec = PARENT_OF.get(line._meta.model_name)
    if spec is None:
        return None
    refs = line.refs if isinstance(line.refs, dict) else {}
    source = refs.get('source') if isinstance(refs.get('source'), dict) else {}
    raw = source.get(spec[1])
    try:
        return int(raw) if raw not in (None, '', 0, '0') else None
    except (TypeError, ValueError):
        return None


def _aggregate_children(parent_model_name: str, parent_pk: int) -> Tuple[float, int]:
    Child = _model(CHILD_OF[parent_model_name])
    # A deleted child consumes nothing: deleting an invoice or receipt line gives the
    # parent line its remaining back (found 2026-09-19, latent — no such rows in wc_demo yet).
    agg = Child.objects.filter(parent_line_id=parent_pk, is_deleted=False).aggregate(
        total=Sum(Cast(KeyTextTransform('active', 'quantity'),
                       DecimalField(max_digits=20, decimal_places=6))),
        count=Count('pk'),
    )
    return float(agg['total'] or 0), int(agg['count'] or 0)


def children_active_sum(line: Any) -> Optional[float]:
    """Σ child.active for a parent-type line; None for a line model that has no children.

    Also records line._child_count for apply_transferred_status().
    """
    name = line._meta.model_name
    if name not in CHILD_OF:
        return None
    if line.pk is None:
        line._child_count = 0
        return 0.0
    total, count = _aggregate_children(name, line.pk)
    line._child_count = count
    return total


def _transferred_status(line: Any) -> Optional[str]:
    """The status this parent line should carry, or None to leave it alone.

    transferred  — it has children and active − Σ children.active == 0
    reopened ('') — it was transferred but its children no longer consume it all
    Lines without children keep their status unless a child was just removed.
    """
    if line._meta.model_name not in CHILD_OF:
        return None
    q = line.quantity if isinstance(line.quantity, dict) else {}
    precision = int(q.get('precision', 2) or 2)
    active = float(q.get('active', 0) or 0)
    unconsumed = round(active - float(getattr(line, '_children_sum', 0) or 0), precision)
    has_children = getattr(line, '_child_count', 0) > 0

    if has_children and unconsumed == 0:
        return TRANSFERRED
    if line.status == TRANSFERRED and (has_children or getattr(line, '_children_changed', False)):
        return ''
    return None


def apply_transferred_status(line: Any) -> bool:
    """Set status from the computed quantities. Returns True when status changed."""
    target = _transferred_status(line)
    if target is None or (line.status or '') == target:
        return False
    line.status = target
    return True


def refresh_parent_line(child_model_name: str, parent_line_id: Optional[int]) -> bool:
    """Recompute one parent line from its children. Saves only when something changed.

    Obtains the parent line under lock — a child is never edited against a parent
    it has not obtained. Returns True when the parent was saved.
    """
    spec = PARENT_OF.get(child_model_name)
    if spec is None or not parent_line_id:
        return False

    from apps.transactions.models.base_line_model import normalize_quantity_map

    Parent = _model(spec[0])
    with transaction.atomic():
        parent = Parent.objects.select_for_update().filter(pk=parent_line_id).first()
        if parent is None:
            logger.warning("[line_parent] %s #%s not found for %s child",
                           spec[0], parent_line_id, child_model_name)
            return False

        stored = parent.quantity if isinstance(parent.quantity, dict) else {}
        total, count = _aggregate_children(parent._meta.model_name, parent.pk)
        parent._children_sum = total
        parent._child_count = count
        parent._children_changed = True

        recomputed = normalize_quantity_map(
            stored, transaction_type=parent._meta.model_name, children_sum=total,
        )
        status_target = _transferred_status(
            _with_quantity(parent, recomputed)
        )
        remaining_changed = stored.get('remaining') != recomputed['remaining']
        status_changed = status_target is not None and (parent.status or '') != status_target
        if not (remaining_changed or status_changed):
            return False

        parent._pending_created = True  # quantity.active did not change; no inventory event
        parent.save(update_fields=['quantity', 'status', 'dt_modified', 'version'])
        return True


def _with_quantity(line: Any, quantity: Dict[str, Any]) -> Any:
    line.quantity = quantity
    return line


def parent_quantities(child: Any) -> Optional[Dict[str, float]]:
    """parent_active / parent_remaining for a child line being edited (edit-open only).

    Never stored on the child. None for a line with no parent line.
    """
    spec = PARENT_OF.get(child._meta.model_name)
    if spec is None or not child.parent_line_id:
        return None
    parent = _model(spec[0]).objects.filter(pk=child.parent_line_id).only('quantity').first()
    if parent is None:
        return None
    q = parent.quantity if isinstance(parent.quantity, dict) else {}
    return {
        'parent_active': float(q.get('active', 0) or 0),
        'parent_remaining': float(q.get('remaining', 0) or 0),
    }


def prorate_flat_discount(child: Any) -> None:
    """A new child line takes its share of the parent line's flat discount.

    A flat discount (discount_amount) belongs to the parent line's whole quantity,
    whether or not the line also carries a percent (the larger of the two applies). Conversion copies the price envelope as is,
    so a partial child would carry the full amount, and every split would
    carry it again. Here, at creation only, the child gets:

        share = flat × child.active / parent.active      (rounded)
        the last child (it takes all that remains) gets flat − Σ earlier shares

    so the children's discounts always add up to the parent's. A child whose
    discount no longer equals the parent's (the user typed one) is left alone.
    """
    spec = PARENT_OF.get(child._meta.model_name)
    if spec is None or not child.parent_line_id:
        return
    cprice = child.price if isinstance(getattr(child, 'price', None), dict) else None
    if not cprice:
        return
    parent = _model(spec[0]).objects.filter(pk=child.parent_line_id).only('price', 'quantity').first()
    if parent is None:
        return
    pprice = parent.price if isinstance(parent.price, dict) else {}
    precision = int(pprice.get('precision', 2) or 2)
    step = Decimal(1).scaleb(-precision)
    flat = Decimal(str(pprice.get('discount_amount') or 0)).quantize(step)
    if flat <= 0 or Decimal(str(cprice.get('discount_amount') or 0)).quantize(step) != flat:
        return
    parent_active = Decimal(str((parent.quantity or {}).get('active') or 0))
    child_active = Decimal(str((child.quantity or {}).get('active') or 0))
    if parent_active <= 0 or child_active >= parent_active:
        return

    carried = Decimal(0)
    converted = Decimal(0)
    Child = _model(CHILD_OF[spec[0].lower()])
    for sib in Child.objects.filter(parent_line_id=parent.pk).only('price', 'quantity'):
        carried += Decimal(str((sib.price or {}).get('discount_amount') or 0))
        converted += Decimal(str((sib.quantity or {}).get('active') or 0))
    left = max(flat - carried, Decimal(0))

    if child_active >= parent_active - converted:
        share = left
    else:
        share = (flat * child_active / parent_active).quantize(step, rounding=ROUND_HALF_UP)
    cprice['discount_amount'] = float(min(share, left))
    child.price = cprice
