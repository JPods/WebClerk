from django.db import models
from .base_line_model import BaseSellLineModel


class SalesOrderLine(BaseSellLineModel):
    parent = models.ForeignKey(
        "transactions.SalesOrder",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "sales_order_lines"