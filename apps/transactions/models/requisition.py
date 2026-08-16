from decimal import Decimal
from django.db import models
from .base_transaction_model import TransactionBaseModel
from common import models as common_models

class Requisition(common_models.BaseModel):
    """Lightweight standardized requisition model (v2 pattern).

    Intent: simple BaseModel with a few searchable fields and full universal envelopes.
    Used by views.requisition.* and tests expecting Requisition endpoints.
    """

    name = models.CharField(max_length=128, default="", db_index=True)
    status = models.CharField(max_length=50, default="draft", blank=True, db_index=True)

    def __str__(self):
        return self.name or f"Requisition {self.id}"

    class Meta:
        db_table = 'requisitions'


# Backward-compatible alias expected by dynamic model loader/imports
__all__ = ["Requisition"]

# --- IGNORE ---