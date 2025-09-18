from __future__ import annotations
from typing import Dict, Any
from decimal import Decimal
from apps.transactions.models import PurchaseOrder

def compute_purchase_order_cost_totals(po: "PurchaseOrder") -> Dict[str, Any]:
    """Aggregate per-line cost fields into PurchaseOrder header totals.
    Returns a dict shaped for header totals (cost-side).
    - line_sum_goods: sum of line.cost.extended
    - line_sum_tax: sum of line.cost.tax
    - line_sum_shipping: sum of line.cost.shipping
    - line_sum_handling: sum of line.cost.handling
    - freight: sum of line.cost.freight
    - commissions: sum of line.cost.commissions
    - tax: alias of line_sum_tax (header-level)
    - total: goods + shipping + handling + freight + tax + commissions
    Note: tax_rate aggregation is not meaningful at header-level; leave None.
    """
    sums = {
        "line_sum_goods": Decimal(0),
        "line_sum_tax": Decimal(0),
        "line_sum_shipping": Decimal(0),
        "line_sum_handling": Decimal(0),
        "freight": Decimal(0),
        "commissions": Decimal(0),
    }

    for ln in po.lines.all():
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

    # Cast to floats for JSON storage
    return {
        "line_sum_goods": float(sums["line_sum_goods"]),
        "line_sum_tax": float(sums["line_sum_tax"]),
        "line_sum_shipping": float(sums["line_sum_shipping"]),
        "line_sum_handling": float(sums["line_sum_handling"]),
        "freight": float(sums["freight"]),
        "commissions": float(sums["commissions"]),
        "tax_rate": None,  # undefined at header level
        "tax": float(sums["line_sum_tax"]),
        "total": float(total),
    }