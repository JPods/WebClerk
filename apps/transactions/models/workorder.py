from decimal import Decimal
from typing import Dict, Any
from django.db import models
from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.wo_totals import compute_work_order_cost_totals


class WorkOrder(TransactionBaseModel):
    # Identifier for WOs is BaseModel's 'id' field

    class Meta:
        db_table = "work_orders"

    def update_cost_totals(self) -> Dict[str, Any]:
        """Compute and optionally persist header cost totals from lines."""
        totals = compute_work_order_cost_totals(self)
        # If this model has a header-level 'cost' or 'totals' JSON, set it here.
        # Example (uncomment if you store header cost under 'cost'):
        # self.cost = totals
        # self.save(update_fields=["cost", "dt_modified", "version"])
        return totals

    def __str__(self) -> str:
        return f"WorkOrder #{self.id} ({self.ida or ''})"

__all__ = ["WorkOrder"]