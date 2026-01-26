from __future__ import annotations
from django.db import models
from .base_line_model import BaseExecLineModel


class PurchaseLine(BaseExecLineModel):
    purchase = models.ForeignKey(
        "transactions.Purchase",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "purchase_lines"

    @property
    def purchase_ref_id(self):
        # Mirror FK id for test helpers
        return self.purchase_id

    @purchase_ref_id.setter
    def purchase_ref_id(self, value):
        self.purchase_id = value


__all__ = ["PurchaseLine"]