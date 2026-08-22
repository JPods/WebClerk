from __future__ import annotations
from typing import Dict, Any
from decimal import Decimal

def compute_work_order_cost_totals(wo) -> Dict[str, Any]:
    """Aggregate per-line cost fields into WorkOrder header totals.

    Returns the standard 3-envelope dict { sell, cost, totals } so
    update_sell_cost_totals() on WorkOrder works identically to other
    transaction models.
    """
    cost_goods = Decimal(0)
    cost_tax = Decimal(0)
    cost_shipping = Decimal(0)
    cost_handling = Decimal(0)
    cost_freight = Decimal(0)
    cost_commissions = Decimal(0)

    for ln in wo.lines.all():
        c = ln.cost or {}
        cost_goods += Decimal(str(c.get("extended", 0) or 0))
        cost_tax += Decimal(str(c.get("tax", 0) or 0))
        cost_shipping += Decimal(str(c.get("shipping", 0) or 0))
        cost_handling += Decimal(str(c.get("handling", 0) or 0))
        cost_freight += Decimal(str(c.get("freight", 0) or 0))
        cost_commissions += Decimal(str(c.get("commissions", 0) or 0))

    total_cost = cost_goods + cost_tax + cost_shipping + cost_handling + cost_freight + cost_commissions

    sell = {
        "line_sum_goods": 0.0,
        "discount": 0.0,
        "tax": 0.0, "shipping": 0.0, "handling": 0.0, "other": 0.0,
        "total": 0.0,
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
        "total": float(total_cost),
    }

    # Build the full default_totals() structure.
    totals = {
        "subtotal": 0.0,
        "discount": 0.0,
        "taxable": 0.0,
        "tax": float(cost_tax),
        "shipping": float(cost_shipping),
        "other": 0.0,
        "total": float(total_cost),
        "cost": float(total_cost),
        "margin": 0.0,
        "margin_pc": None,
        "received": None,
        "balance": None,
    }

    return {"sell": sell, "cost": cost, "totals": totals}