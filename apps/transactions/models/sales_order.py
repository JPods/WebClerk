from django.db import models
from .base_transaction_model import TransactionBaseModel


class SalesOrder(TransactionBaseModel):
    # Identifier (DB has NOT NULL constraint in some environments)
    order_no = models.CharField(max_length=64, default="", db_index=True)
    class Meta:
        db_table = "sales_orders"

    def __str__(self) -> str:  # pragma: no cover
        return f"SO:{self.order_no or self.pk}"


__all__ = ["SalesOrder"]