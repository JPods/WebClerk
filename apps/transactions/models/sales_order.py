from decimal import Decimal
from django.db import models
from .base_transaction_model import TransactionBaseModel

class SalesOrder(TransactionBaseModel):
    # Add any SalesOrder-specific fields or methods here
  class Meta:
        db_table = "sales_orders"

    def __str__(self) -> str:  # pragma: no cover
        return f"SO:{self.order_no}" if self.order_no else f"SO:{self.pk}"


__all__ = ["SalesOrder"]