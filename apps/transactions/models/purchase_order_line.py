from __future__ import annotations
from django.db import models
from .base_line_model import BaseExecLineModel

class PurchaseOrderLine(BaseExecLineModel):  # or your BaseLine class
    parent = models.ForeignKey(
        "transactions.PurchaseOrder",  # string ref avoids circular import
        on_delete=models.CASCADE,
        related_name="lines",
    )
    # ...existing fields/methods...

    class Meta:
        db_table = "purchase_order_lines"