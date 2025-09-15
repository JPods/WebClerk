from decimal import Decimal
from django.db import models
from .base_line_model import BaseLineModel
from .purchase_order import PurchaseOrder

class PurchaseOrderLine(BaseLineModel):
    parent = models.ForeignKey(PurchaseOrder, related_name="lines", on_delete=models.CASCADE)
    # Add any PurchaseOrderLine-specific fields or methods here
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

    quantity_received = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)

    class Meta:
        db_table = "purchase_order_lines"
