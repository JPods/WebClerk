from django.db import models
from .base_line_model import BaseSellLineModel


class OrderLine(BaseSellLineModel):
    order = models.ForeignKey(
        "transactions.Order",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"OrderLine {self.id} on order {self.order_id}"

    class Meta:
        db_table = "order_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.order

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.order_id


__all__ = ["OrderLine"]