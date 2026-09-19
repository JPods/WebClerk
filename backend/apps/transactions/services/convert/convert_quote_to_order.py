from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django.db import transaction

from apps.transactions.models import (
    Quote,
    QuoteLine,
    Order,
    OrderLine,
)
from .convert_utils import build_line_payload, sum_price_extended

import logging
logger = logging.getLogger(__name__)


class QuoteToOrderTransferError(Exception):
    """Business-rule violation during quote-to-order transfer."""



def validate_quote_for_transfer(
    quote: Optional[Quote],
    line_ids: Optional[List[int]] = None,
) -> Dict:
    """
    Returns:
      {
        'can_transfer': bool,
        'errors': [str],
        'warnings': [str],
        'line_count': int,
        'total': float,
      }
    """
    errors: List[str] = []
    warnings: List[str] = []

    if quote is None:
        return {
            "can_transfer": False,
            "errors": ["Quote not found"],
            "warnings": [],
            "line_count": 0,
            "total": 0.0,
        }

    qs = QuoteLine.objects.filter(quote=quote)

    if line_ids is not None:
        existing = set(qs.filter(id__in=line_ids).values_list("id", flat=True))
        missing = [i for i in line_ids if i not in existing]
        if missing:
            errors.append(f"Line IDs not found: {missing}")

    line_count = qs.count()
    if line_count == 0:
        errors.append("No lines to transfer")

    # Warnings based on statuses
    if getattr(quote, "status", "") == "converted":
        warnings.append("Quote status is converted")

    transferred_cnt = qs.filter(status="transferred").count()
    if transferred_cnt:
        warnings.append("Some lines already transferred" if transferred_cnt > 1 else "Line already transferred")

    total_amount = sum_price_extended(qs)

    can_transfer = len(errors) == 0
    return {
        "can_transfer": can_transfer,
        "errors": errors,
        "warnings": warnings,
        "line_count": line_count,
        "total": total_amount,
    }


def _convert_quantity_from_quote(quote_qty: Optional[Dict]) -> Dict:
    """Convert quote line quantity to order line quantity.

    Sets:
      staged  = source remaining (qty being transferred)
      active  = staged (user input — full transfer amount initially)
      remaining = active (no children yet)
      converted_from_quote = audit trail with original keys

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    q = quote_qty or {}
    # Use remaining from source (what's available for transfer)
    transfer_qty = q.get("remaining", 0) or q.get("staged", 0) or 0

    converted_from_quote = {
        "is_blanket": q.get("is_blanket", False),
        "increment": q.get("increment", 0),
        "original_remaining": q.get("remaining", 0),
        "original_staged": q.get("staged", 0),
    }

    order_qty = {
        "staged": transfer_qty,
        "active": transfer_qty,
        "remaining": transfer_qty,
    }
    if "precision" in q:
        order_qty["precision"] = q["precision"]
    if "is_fixed" in q:
        order_qty["is_fixed"] = q["is_fixed"]

    order_qty["converted_from_quote"] = converted_from_quote
    return order_qty



@transaction.atomic
def transfer_quote_to_order(
    *,
    quote: Quote,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    order_status: str = "confirmed",
    preserve_quote: bool = True,
) -> Dict:
    """Create the Order header from a quote and return its lines for review.

    One converter (recheck 2): this delegates to convert.convert_quote_to_order, so the
    DRF endpoint and the UI get the same rules — line_type and finance carried, a flat
    discount shared across partial children, a document discount carried as a percent.
    Its own copy of those rules, which dropped the discount line type and the tax rate,
    is gone. The result keeps the shape this endpoint's callers expect.

    preserve_quote is accepted for caller compatibility and ignored — the quote
    is never modified here.
    """
    from apps.transactions.services.convert.convert import convert_quote_to_order as convert_one

    if not transfer_all and not line_ids:
        raise QuoteToOrderTransferError("Must specify line_ids when transfer_all is False")

    check = validate_quote_for_transfer(quote, line_ids=None if transfer_all else line_ids)
    if not check.get('can_transfer', True):
        raise QuoteToOrderTransferError('; '.join(check.get('errors') or ['quote cannot be transferred']))
    try:
        result = convert_one(quote.pk, line_ids=None if transfer_all else line_ids)
    except Exception as exc:                       # the converter's refusals are this one's
        raise QuoteToOrderTransferError(str(exc)) from exc

    order_id = result.get('order_id')
    order = Order.objects.get(pk=order_id)
    if order_status:
        order.status = order_status
    # This endpoint's own contract: the order names its quote in refs.source, and a
    # blanket quote's is_fixed follows onto the review quantities.
    refs = dict(order.refs or {})
    refs['source'] = {**(refs.get('source') or {}), 'quote_id': quote.id}
    order.refs = refs
    order.save(update_fields=['status', 'refs', 'dt_modified', 'version'])

    by_line = {ql.pk: ql for ql in QuoteLine.objects.filter(quote=quote)}
    for entry in result.get('lines', []):
        src_id = ((entry.get('refs') or {}).get('source') or {}).get('quote_line_id')
        src = by_line.get(src_id)
        src_qty = (getattr(src, 'quantity', None) or {}) if src else {}
        if 'is_fixed' in src_qty:
            entry['quantity']['is_fixed'] = src_qty['is_fixed']

    return {
        "success": True,
        "order_id": order_id,
        "quote_id": quote.id,
        "lines_for_review": result.get('lines_for_review', 0),
        "lines": result.get('lines', []),
    }
