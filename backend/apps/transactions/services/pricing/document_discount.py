"""A discount on a whole document (Bill, 2026-09-19).

"It is at the line level that most actions should be applied. If there is
subsequently a 10% discount applied to the transaction, it should be distributed
over the lines in proportion."

The document discount is an input on the header, ``allocations.discount_percent``
or ``allocations.discount_amount``. The totals engine (compute_totals) spreads it
over the product lines on every recompute, as a reduction of each line's
discounted unit, so lines added later get their share and each line's
totals.discount includes it. A posted (journalized) document is locked, so its
shares freeze.

Entry points:
    apply_document_discount(header, amount=…, percent=…) — the action
    spread_discount_line(line) — a discount line saved on a sell document is moved
        into allocations.discount_amount and kept at zero as the record.
Settlement (cash) discounts, purpose='cash_discount', stay lines.
"""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CENT = Decimal('0.01')
SELL_HEADERS = ('quote', 'order', 'invoice')


def _dec(v: Any) -> Decimal:
    return Decimal(str(v or 0))


def apply_document_discount(header, amount: Optional[Any] = None,
                            percent: Optional[Any] = None) -> Dict[str, Any]:
    """Set the document discount; the totals engine spreads it over the lines."""
    if header._meta.model_name not in SELL_HEADERS:
        raise ValueError(f"A document discount applies to quotes, orders and invoices, not {header._meta.model_name}")
    alloc = dict(header.allocations or {})
    if percent not in (None, '', 0):
        pct = _dec(percent)
        if not (0 < pct <= 100):
            raise ValueError(f"A discount percent must be between 0 and 100, not {pct}")
        alloc['discount_percent'] = float(pct)
        alloc.pop('discount_amount', None)
    else:
        amt = abs(_dec(amount)).quantize(CENT, rounding=ROUND_HALF_UP)
        alloc['discount_amount'] = float(amt)
        alloc.pop('discount_percent', None)
    header.allocations = alloc
    header.save(update_fields=['allocations'])      # the header signal recomputes the totals
    header.refresh_from_db(fields=['totals'])
    logger.info("[DocumentDiscount] %s #%s: allocations=%s", header._meta.model_name, header.pk, alloc)
    return {'allocations': alloc, 'discount': (header.totals or {}).get('discount')}


def spread_discount_line(line) -> Optional[Dict[str, Any]]:
    """Move a document discount line into allocations.discount_amount; keep it at zero."""
    if (line.line_type or '') != 'discount' or getattr(line, 'purpose', '') == 'cash_discount':
        return None
    header = line.parent
    if header is None or header._meta.model_name not in SELL_HEADERS:
        return None
    price = dict(line.price or {})
    q = _dec((line.quantity or {}).get('active') or 1)
    amount = abs((q * _dec(price.get('unit'))).quantize(CENT, rounding=ROUND_HALF_UP))
    if amount <= 0:
        return None
    price.update({'unit': 0, 'discount_amount': 0, 'discount_percent': 0})
    meta = dict(line.metadata or {}) if isinstance(line.metadata, dict) else {}
    meta['document_discount'] = {'applied': float(amount), 'to': 'allocations.discount_amount'}
    line.price = price
    line.metadata = meta
    line.save(update_fields=['price', 'metadata'])
    existing = _dec((header.allocations or {}).get('discount_amount'))
    return apply_document_discount(header, amount=existing + amount)
