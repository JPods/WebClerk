from decimal import Decimal
from django.db import models
from .base_transaction_model import TransactionBaseModel

class PurchaseOrder(TransactionBaseModel):
    # Identifier for POs
    po_no = models.CharField(max_length=64, default="", db_index=True)
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

__all__ = ["PurchaseOrder"]
