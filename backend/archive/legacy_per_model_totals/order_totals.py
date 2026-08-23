from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict

def _d(x: Any, places: int = 2) -> Decimal:
    try:
        d = Decimal(str(x))
        return d.quantize(Decimal(10) ** -places) if places >= 0 else d
    except Exception:
        return Decimal(0)

def compute_order_sell_cost_totals(order) -> Dict[str, Dict[str, float]]:
    """Aggregate sell and cost totals from all order lines.

    Iterates order.lines.all() and sums:
      sell: Σ line.price.extended, Σ line.price.discount_amount
      cost: Σ line.cost.extended + tax + shipping + handling + freight + commissions

    Returns dict with three envelopes:
      sell:   { line_sum_goods, discount, tax, shipping, handling, other, total }
      cost:   { line_sum_goods, line_sum_tax, ..., total }
      totals: { total (=sell), cost, margin, margin_pc, received, balance }

    Margin formula:
      margin    = sell.total − cost.total
      margin_pc = (margin / sell.total) × 100

    Called by Order.update_sell_cost_totals(persist=True) to write back
    to the header's sell/cost/totals JSON fields.

    See: readmes/topics/transactions/transactions-totals.md §3
    """
    sell_goods = Decimal(0)
    sell_discount = Decimal(0)

    cost_goods = Decimal(0)
    cost_tax = Decimal(0)
    cost_shipping = Decimal(0)
    cost_handling = Decimal(0)
    cost_freight = Decimal(0)
    cost_commissions = Decimal(0)

    # --- Iterate all lines and accumulate sell + cost components ---
    for ln in order.lines.all():
        p = ln.price or {}    # sell-side envelope (BaseSellLineModel)
        c = ln.cost or {}     # cost envelope (BaseLineCore)

        # Sell aggregation: sum of extended prices and discounts
        sell_goods += _d(p.get("extended", 0))
        sell_discount += _d(p.get("discount_amount", 0))

        # Cost aggregation: sum of extended costs plus surcharges
        cost_goods += _d(c.get("extended", 0))
        cost_tax += _d(c.get("tax", 0))
        cost_shipping += _d(c.get("shipping", 0))
        cost_handling += _d(c.get("handling", 0))
        cost_freight += _d(c.get("freight", 0))
        cost_commissions += _d(c.get("commissions", 0))

    sell = {
        "line_sum_goods": float(sell_goods),
        "discount": float(sell_discount),
        "tax": 0.0,
        "shipping": 0.0,
        "handling": 0.0,
        "other": 0.0,
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

    total_amt = sell_goods
    total_cost = Decimal(str(cost["total"]))
    margin = total_amt - total_cost
    margin_pc = (margin / total_amt * Decimal(100)) if total_amt > 0 else None

    # Build the full default_totals() structure so every key is present.
    totals = {
        "subtotal": float(sell_goods),
        "discount": float(sell_discount),
        "taxable": float(sell_goods - sell_discount),
        "tax": 0.0,
        "shipping": 0.0,
        "other": 0.0,
        "total": float(total_amt),
        "cost": float(total_cost),
        "margin": float(margin),
        "margin_pc": float(margin_pc) if margin_pc is not None else None,
        "received": None,
        "balance": None,
    }

    return {"sell": sell, "cost": cost, "totals": totals}
