from django.db import models
from .base_line_model import BaseSellLineModel


class SalesOrderLine(BaseSellLineModel):
    salesorder_id = models.ForeignKey(
        "transactions.SalesOrder",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "sales_order_lines"

    @property
    def salesorder_ref_id(self):
        # Mirror FK id for test helpers
        return getattr(self, "salesorder_id_id", None)

    @salesorder_ref_id.setter
    def salesorder_ref_id(self, value):
        self.salesorder_id_id = value