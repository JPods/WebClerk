from __future__ import annotations
from django.db import models
from .base_line_model import BaseExecLineModel


class PurchaseLine(BaseExecLineModel):
    purchase = models.ForeignKey(
        "transactions.Purchase",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"PurchaseLine {self.id} on purchase {self.purchase_id}"

    class Meta:
        db_table = "purchase_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.purchase

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.purchase_id


__all__ = ["PurchaseLine"]