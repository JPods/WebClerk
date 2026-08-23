from django.db import models
from .base_transaction_model import TransactionBaseModel


class WorkOrder(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    class Meta:
        db_table = "work_orders"

    def update_cost_totals(self) -> dict:
        """Alias for backward compatibility."""
        return self.update_sell_cost_totals(persist=True)

    def __str__(self) -> str:
        return f"WorkOrder #{self.id} ({self.ida or ''})"

__all__ = ["WorkOrder"]