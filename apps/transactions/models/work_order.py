from django.db import models
from .base_transaction_model import TransactionBaseModel


class Workorder(TransactionBaseModel):
    class Meta:
        db_table = "work_orders"

__all__ = ["Workorder"]