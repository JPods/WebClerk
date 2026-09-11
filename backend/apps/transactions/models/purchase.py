from __future__ import annotations

from typing import TYPE_CHECKING
from django.db import models

from .base_transaction_model import TransactionBaseModel


class Purchase(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    # Capital asset tracking — gate + envelope
    is_capital = models.BooleanField(
        default=False, db_index=True,
        help_text="True if this purchase is a capital asset (balance sheet, not expense)")
    capital_asset = models.JSONField(
        null=True, blank=True,
        help_text="Capital asset details: asset_name, useful_life_months, salvage_value, "
                  "depreciation_method, placed_in_service, location, serial_number, notes")

    class Meta:
        db_table = "purchases"

    def __str__(self) -> str:
        return f"Purchase #{self.id} ({getattr(self, 'ida', '') or ''})"


if TYPE_CHECKING:  # pragma: no cover
    from .purchase_line import PurchaseLine

__all__ = ["Purchase"]
