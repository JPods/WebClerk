from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict

def _d(x: Any, places: int = 2) -> Decimal:
    try:
        d = Decimal(str(x))
        return d.quantize(Decimal(10) ** -places) if places >= 0 else d
    except Exception:
        return Decimal(0)

def compute_invoice_sell_cost_totals(invoice) -> Dict[str, Dict[str, float]]:
    """Aggregate sell and cost totals from all invoice lines.

    Same pattern as compute_order_sell_cost_totals — iterates invoice.lines.all()
    and sums price.extended → sell.total, cost.* → cost.total, then computes
    margin = sell.total − cost.total.

    Called by Invoice.update_sell_cost_totals(persist=True).
    NOTE: No post_save signal is wired for InvoiceLine yet — must be called
    explicitly by the save view or transfer service.

    See: readmes/topics/transactions/transactions-totals.md §3
    """
    sell_goods = Decimal(0); sell_discount = Decimal(0)
    cost_goods = Decimal(0); cost_tax = Decimal(0); cost_shipping = Decimal(0)
    cost_handling = Decimal(0); cost_freight = Decimal(0); cost_commissions = Decimal(0)

    # --- Iterate all lines and accumulate sell + cost components ---
    for ln in invoice.lines.all():
        p = ln.price or {}; c = ln.cost or {}  # sell + cost envelopes
        sell_goods += _d(p.get("extended", 0))
        sell_discount += _d(p.get("discount_amount", 0))
        cost_goods += _d(c.get("extended", 0))
        cost_tax += _d(c.get("tax", 0))
        cost_shipping += _d(c.get("shipping", 0))
        cost_handling += _d(c.get("handling", 0))
        cost_freight += _d(c.get("freight", 0))
        cost_commissions += _d(c.get("commissions", 0))

    sell = {
        "line_sum_goods": float(sell_goods),
        "discount": float(sell_discount),
        "tax": 0.0, "shipping": 0.0, "handling": 0.0, "other": 0.0,
        "total": float(sell_goods),
    }
    cost = {
        "line_sum_goods": float(cost_goods),
        "line_sum_tax": float(cost_tax),
        "line_sum_shipping": float(cost_shipping),
        "line_sum_handling": float(cost_handling),
        "freight": float(cost_freight),
        "commissions": float(cost_commissions),
        "tax_rate": None,
        "tax": float(cost_tax),
        "total": float(cost_goods + cost_tax + cost_shipping + cost_handling + cost_freight + cost_commissions),
    }

    # Preserve existing header-level values that lines don't determine
    existing = invoice.totals or {}
    tax = _d(existing.get("tax", 0))
    shipping = _d(existing.get("shipping", 0))
    other = _d(existing.get("other", 0))
    received = existing.get("received")  # preserve — set by payment_pending
    discount_header = _d(existing.get("discount", 0))

    # Separate product lines from system adjustment lines (SYS-*)
    product_subtotal = Decimal(0)
    adjustment_total = Decimal(0)
    for ln in invoice.lines.all():
        p = ln.price or {}
        item_ida = (ln.item or {}).get('ida', '')
        ext = _d(p.get("extended", 0))
        if item_ida.startswith('SYS-'):
            adjustment_total += ext
        else:
            product_subtotal += ext

    # If no product lines but header has a total, preserve it.
    # The header total is authoritative — lines are detail.
    existing_total = _d(existing.get("total", 0))
    header_total = _d(getattr(invoice, 'total', 0) or 0)
    if product_subtotal == 0 and (existing_total > 0 or header_total > 0):
        subtotal = max(existing_total, header_total)
    else:
        subtotal = product_subtotal if product_subtotal > 0 else sell_goods

    taxable = subtotal - discount_header
    total_amt = subtotal - discount_header + tax + shipping + other + adjustment_total
    total_cost = Decimal(str(cost["total"]))
    margin = total_amt - total_cost
    margin_pc = (margin / total_amt * Decimal(100)) if total_amt > 0 else None

    # Recompute balance from total - received (if received is set)
    if received is not None:
        balance = float(total_amt - _d(received))
    else:
        balance = float(total_amt)

    totals = {
        "subtotal": float(subtotal),
        "discount": float(discount_header),
        "taxable": float(taxable),
        "tax": float(tax),
        "shipping": float(shipping),
        "other": float(other),
        "total": float(total_amt),
        "cost": float(total_cost),
        "margin": float(margin),
        "margin_pc": float(margin_pc) if margin_pc is not None else None,
        "received": received,
        "balance": balance,
    }
    return {"sell": sell, "cost": cost, "totals": totals}