from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict

def _d(x: Any, places: int = 2) -> Decimal:
    try:
        d = Decimal(str(x))
        return d.quantize(Decimal(10) ** -places) if places >= 0 else d
    except Exception:
        return Decimal(0)

def compute_sales_order_sell_cost_totals(sales_order) -> Dict[str, Dict[str, float]]:
    """Aggregate sell and cost from sales order lines."""
    sell_goods = Decimal(0)
    sell_discount = Decimal(0)

    cost_goods = Decimal(0)
    cost_tax = Decimal(0)
    cost_shipping = Decimal(0)
    cost_handling = Decimal(0)
    cost_freight = Decimal(0)
    cost_commissions = Decimal(0)

    for ln in sales_order.lines.all():
        p = ln.price or {}
        c = ln.cost or {}

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

    totals = {
        "total": float(total_amt),
        "cost": float(total_cost),
        "margin": float(margin),
        "margin_pc": float(margin_pc) if margin_pc is not None else None,
        "received": None,
        "balance": None,
    }

    return {"sell": sell, "cost": cost, "totals": totals}