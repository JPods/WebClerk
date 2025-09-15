from decimal import Decimal
from django.db import models
from .base_line_model import BaseLineModel
from .sales_order import SalesOrder


class SalesOrderLine(BaseLineModel):
    parent = models.ForeignKey(SalesOrder, related_name="lines", on_delete=models.CASCADE)

    BASE_INT_DEFAULT = Decimal("0")
    quantity_invoiced = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)

    class Meta:
        db_table = "sales_order_lines"