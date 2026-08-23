from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, cast

# Do NOT import models at module scope to avoid cycles with model files.
if TYPE_CHECKING:  # pragma: no cover
    from apps.transactions.models.purchase import Purchase

def compute_purchase_cost_totals(po: "Purchase") -> Dict[str, Any]:
    """Aggregate per-line cost fields into Purchase header cost envelope.

    Returns a *flat* cost dict (not the three-envelope sell/cost/totals shape).
    This is the cost-only variant — see purchase_totals.py for the full
    three-envelope version used by update_sell_cost_totals().

    Keys returned:
      line_sum_goods     Σ line.cost.extended
      line_sum_tax       Σ line.cost.tax
      line_sum_shipping  Σ line.cost.shipping
      line_sum_handling  Σ line.cost.handling
      freight            Σ line.cost.freight
      commissions        Σ line.cost.commissions
      tax                alias of line_sum_tax (header-level convenience)
      tax_rate           None (not meaningful as an aggregate)
      total              goods + tax + shipping + handling + freight + commissions

    See: readmes/topics/transactions/transactions-totals.md §3
    """
    sums = {
        "line_sum_goods": Decimal(0),
        "line_sum_tax": Decimal(0),
        "line_sum_shipping": Decimal(0),
        "line_sum_handling": Decimal(0),
        "freight": Decimal(0),
        "commissions": Decimal(0),
    }

    for ln in cast(Any, po).lines.all():
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