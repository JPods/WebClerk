from __future__ import annotations
from typing import Dict, Any
from decimal import Decimal

def compute_work_order_cost_totals(wo) -> Dict[str, Any]:
    """Aggregate per-line cost fields into WorkOrder header totals.
    Mirrors PurchaseOrder aggregation.
    """
    sums = {
        "line_sum_goods": Decimal(0),
        "line_sum_tax": Decimal(0),
        "line_sum_shipping": Decimal(0),
        "line_sum_handling": Decimal(0),
        "freight": Decimal(0),
        "commissions": Decimal(0),
    }

    for ln in wo.lines.all():
        c = ln.cost or {}
        sums["line_sum_goods"] += Decimal(str(c.get("extended", 0) or 0))
        sums["line_sum_tax"] += Decimal(str(c.get("tax", 0) or 0))
        sums["line_sum_shipping"] += Decimal(str(c.get("shipping", 0) or 0))
        sums["line_sum_handling"] += Decimal(str(c.get("handling", 0) or 0))
        sums["freight"] += Decimal(str(c.get("freight", 0) or 0))
        sums["commissions"] += Decimal(str(c.get("commissions", 0) or 0))

    total = (
        sums["line_sum_goods"]
        + sums["line_sum_tax"]
        + sums["line_sum_shipping"]
        + sums["line_sum_handling"]
        + sums["freight"]
        + sums["commissions"]
    )

    return {
        "line_sum_goods": float(sums["line_sum_goods"]),
        "line_sum_tax": float(sums["line_sum_tax"]),
        "line_sum_shipping": float(sums["line_sum_shipping"]),
        "line_sum_handling": float(sums["line_sum_handling"]),
        "freight": float(sums["freight"]),
        "commissions": float(sums["commissions"]),
        "tax_rate": None,
        "tax": float(sums["line_sum_tax"]),
        "total": float(total),
    }