from __future__ import annotations

from typing import TYPE_CHECKING
from django.db import models

from .base_transaction_model import TransactionBaseModel


class Purchase(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    class Meta:
        db_table = "purchases"

    def __str__(self) -> str:
        return f"Purchase #{self.id} ({getattr(self, 'ida', '') or ''})"


if TYPE_CHECKING:  # pragma: no cover
    from .purchase_line import PurchaseLine

__all__ = ["Purchase"]
