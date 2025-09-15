from django.db import models
from .base_transaction_model import TransactionBaseModel


class Invoice(TransactionBaseModel):
    class Meta:
        db_table = "invoices"


__all__ = ["Invoice"]