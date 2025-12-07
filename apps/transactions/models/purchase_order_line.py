from __future__ import annotations
from django.db import models
from .base_line_model import BaseSellLineModel

class PurchaseOrderLine(BaseSellLineModel):
    # Legacy table doesn't have 'price'; drop inherited field so ORM won't write it.
    price = None

    purchaseorder_id = models.ForeignKey(
        "transactions.PurchaseOrder",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "purchase_order_lines"

    @property
    def purchaseorder_ref_id(self):
        # Mirror FK id for test helpers
        return getattr(self, "purchaseorder_id_id", None)

    @purchaseorder_ref_id.setter
    def purchaseorder_ref_id(self, value):
        self.purchaseorder_id_id = value