from __future__ import annotations

from typing import Dict, TYPE_CHECKING
from django.db import models

from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.purchase_totals import compute_purchase_sell_cost_totals


class Purchase(TransactionBaseModel):
    class Meta:
        db_table = "purchases"

    def update_sell_cost_totals(self, persist: bool = False) -> Dict[str, Dict[str, float]]:
        """Compute sell/cost/totals from lines. For Purchase, sell is empty, cost is aggregated."""
        computed = compute_purchase_sell_cost_totals(self)

        if persist:
            update_fields: list[str] = []
            if hasattr(self, "sell"):
                self.sell = computed["sell"]  # type: ignore[assignment]
                update_fields.append("sell")
            if hasattr(self, "cost"):
                self.cost = computed["cost"]  # type: ignore[assignment]
                update_fields.append("cost")
            if hasattr(self, "totals"):
                self.totals = computed["totals"]  # type: ignore[assignment]
                update_fields.append("totals")
            if update_fields:
                update_fields += ["dt_modified", "version"]
                self.save(update_fields=update_fields)

        return computed

    def __str__(self) -> str:
        return f"Purchase #{self.id} ({getattr(self, 'ida', '') or ''})"


if TYPE_CHECKING:  # pragma: no cover
    from .purchase_line import PurchaseLine

__all__ = ["Purchase"]
