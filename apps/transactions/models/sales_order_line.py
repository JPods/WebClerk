from django.db import models
from .base_line_model import BaseLineModel
from .sales_order import SalesOrder


class SalesOrderLine(BaseLineModel):
    parent = models.ForeignKey(SalesOrder, related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "sales_order_lines"