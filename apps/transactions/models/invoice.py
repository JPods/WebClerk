from django.db import models
from .base_transaction_model import TransactionBaseModel


class Invoice(TransactionBaseModel):
    invoice_no = models.CharField(max_length=64, default="", db_index=True)
    class Meta:
        db_table = "invoices"


__all__ = ["Invoice"]