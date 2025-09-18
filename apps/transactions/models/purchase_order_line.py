from django.db import models
from .base_line_model import BaseExecLineModel

class PurchaseOrderLine(BaseExecLineModel):
    parent = models.ForeignKey(
        "transactions.PurchaseOrder",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "purchase_order_lines"
