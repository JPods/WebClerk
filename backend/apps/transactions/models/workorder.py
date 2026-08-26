from django.db import models
from .base_transaction_model import TransactionBaseModel


class WorkOrder(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    class Meta:
        db_table = "work_orders"

    def __str__(self) -> str:
        return f"WorkOrder #{self.id} ({self.ida or ''})"

__all__ = ["WorkOrder"]