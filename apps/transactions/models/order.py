from typing import Dict
from django.db import models
from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.order_totals import compute_order_sell_cost_totals


class Order(TransactionBaseModel):
    class Meta:
        db_table = "orders"

    def update_sell_cost_totals(self, persist: bool = False) -> Dict[str, Dict[str, float]]:
        """Compute sell/cost/totals from lines. If persist=True and fields exist, save them."""
        computed = compute_order_sell_cost_totals(self)

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
        return str(getattr(self, "ida", "")) or f"Order({self.pk})"


__all__ = ["Order"]