from django.db import models
from .base_line_model import BaseSellLineModel


class OrderLine(BaseSellLineModel):
    order_id = models.ForeignKey(
        "transactions.Order",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "order_lines"

    @property
    def order_ref_id(self):
        # Mirror FK id for test helpers
        return getattr(self, "order_id_id", None)

    @order_ref_id.setter
    def order_ref_id(self, value):
        self.order_id_id = value


__all__ = ["OrderLine"]