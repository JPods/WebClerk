"""A discount on a whole document becomes discounts on its lines (Bill, 2026-09-19).

"All taxes and discounts should be based on their line": line amount =
qty.active × unit − line discount, and line tax = line amount × line rate.
A document discount therefore has no math of its own. It is spread into the
product lines' price.discount_amount, in proportion to each line's amount; the
last line takes the remainder so the shares add up to exactly the discount.
A line with a percent discount is converted to its dollar amount first, so
the two discounts add.

Entry points:
    apply_document_discount(header, amount=…, percent=…) — the action
    spread_discount_line(line) — a discount line saved on a sell document is
        applied this way and left as a zero-amount record of what was applied.
Settlement (cash) discounts, purpose='cash_discount', are not spread.
"""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CENT = Decimal('0.01')
SELL_HEADERS = ('quote', 'order', 'invoice')


def _r2(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def _dec(v: Any) -> Decimal:
    return Decimal(str(v or 0))


def _line_amount(line) -> Decimal:
    q = _dec((line.quantity or {}).get('active'))
    p = line.price or {}
    gross = _r2(q * _dec(p.get('unit')))
    pct = _dec(p.get('discount_percent'))
    disc = _r2(gross * pct / 100) if pct else _dec(p.get('discount_amount'))
    return gross - disc


def apply_document_discount(header, amount: Optional[Any] = None,
                            percent: Optional[Any] = None,
                            exclude_pk: Optional[int] = None) -> Dict[str, Any]:
    """Spread a document discount into the product lines' own discounts."""
    if header._meta.model_name not in SELL_HEADERS:
        raise ValueError(f"A document discount applies to quotes, orders and invoices, not {header._meta.model_name}")
    lines: List[Any] = [
        l for l in header.lines.all().order_by('line_number', 'pk')
        if (l.line_type or 'product') == 'product' and l.pk != exclude_pk
    ]
    amounts = [_line_amount(l) for l in lines]
    base = sum(amounts, Decimal(0))
    if base <= 0:
        raise ValueError("There are no product lines with an amount to discount")
    if percent not in (None, '', 0):
        discount = _r2(base * _dec(percent) / 100)
    else:
        discount = _r2(abs(_dec(amount)))
    if discount <= 0:
        return {'discount': 0.0, 'shares': []}
    if discount > base:
        raise ValueError(f"A discount of {discount} is more than the lines' amount {base}")

    shares: List[Dict[str, Any]] = []
    given = Decimal(0)
    for i, (line, line_amt) in enumerate(zip(lines, amounts)):
        share = discount - given if i == len(lines) - 1 else _r2(discount * line_amt / base)
        given += share
        price = dict(line.price or {})
        gross = _r2(_dec((line.quantity or {}).get('active')) * _dec(price.get('unit')))
        own = gross - line_amt                       # the line's own discount, in dollars
        price['discount_percent'] = 0
        price['discount_amount'] = float(own + share)
        price['amount'] = float(line_amt - share)   # what the save will compute; keeps the AI audit quiet
        line.price = price
        line.save()
        shares.append({'line_id': line.pk, 'line_amount': float(line_amt), 'share': float(share)})

    logger.info("[DocumentDiscount] %s #%s: %s spread over %d lines",
                header._meta.model_name, header.pk, discount, len(shares))
    return {'discount': float(discount), 'base': float(base), 'shares': shares}


def spread_discount_line(line) -> Optional[Dict[str, Any]]:
    """Apply a discount line as line discounts; keep it as a zero-amount record."""
    if (line.line_type or '') != 'discount' or getattr(line, 'purpose', '') == 'cash_discount':
        return None
    header = line.parent
    if header is None or header._meta.model_name not in SELL_HEADERS:
        return None
    price = dict(line.price or {})
    q = _dec((line.quantity or {}).get('active') or 1)
    amount = abs(_r2(q * _dec(price.get('unit'))))
    if amount <= 0:
        return None
    result = apply_document_discount(header, amount=amount, exclude_pk=line.pk)
    price.update({'unit': 0, 'discount_amount': 0, 'discount_percent': 0, 'amount': 0})
    meta = dict(line.metadata or {}) if isinstance(line.metadata, dict) else {}
    meta['document_discount'] = {'applied': float(amount), 'shares': result.get('shares', [])}
    line.price = price
    line.metadata = meta
    line.save(update_fields=['price', 'metadata'])
    return result
