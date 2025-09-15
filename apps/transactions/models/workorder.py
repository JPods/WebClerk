from decimal import Decimal
from django.db import models
from .base_transaction_model import TransactionBaseModel

class WorkOrder(TransactionBaseModel):
    # Add any WorkOrder-specific fields or methods here
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

__all__ = ["WorkOrder"]