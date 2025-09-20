from __future__ import annotations
from django.db import models
from .base_line_model import BaseSellLineModel

class PurchaseOrderLine(BaseSellLineModel):
    # Legacy table doesn't have 'price'; drop inherited field so ORM won't write it.
    price = None

    parent = models.ForeignKey(
        "transactions.PurchaseOrder",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "purchase_order_lines"
        managed = False  # Skip serialization/migration against legacy schema

    @property
    def parent_ref_id(self):
        # Mirror FK id for test helpers
        return getattr(self, "parent_id", None)

    @parent_ref_id.setter
    def parent_ref_id(self, value):
        self.parent_id = value