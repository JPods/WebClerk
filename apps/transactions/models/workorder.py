from decimal import Decimal
from typing import Dict, Any
from django.db import models
from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.wo_totals import compute_work_order_cost_totals


class WorkOrder(TransactionBaseModel):
    # Identifier for WOs is BaseModel's 'id' field

    class Meta:
        db_table = "work_orders"

    def update_sell_cost_totals(self, persist: bool = False) -> Dict[str, Dict[str, Any]]:
        """Compute and optionally persist header totals from lines."""
        computed = compute_work_order_cost_totals(self)

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

    # Keep the old name as an alias for backward compatibility
    def update_cost_totals(self) -> Dict[str, Any]:
        return self.update_sell_cost_totals(persist=True)

    def __str__(self) -> str:
        return f"WorkOrder #{self.id} ({self.ida or ''})"

__all__ = ["WorkOrder"]