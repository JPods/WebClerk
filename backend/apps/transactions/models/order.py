from django.db import models
from .base_transaction_model import TransactionBaseModel


class Order(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    class Meta:
        db_table = "orders"

    def __str__(self) -> str:
        return str(getattr(self, "ida", "")) or f"Order({self.pk})"


__all__ = ["Order"]