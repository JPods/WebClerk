from decimal import Decimal
from django.db import models
from .base_transaction_model import TransactionBaseModel

class Proposal(TransactionBaseModel):
    # Human-readable identifier
    name = models.CharField(max_length=128, default="", db_index=True)
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity

__all__ = ["Proposal"]