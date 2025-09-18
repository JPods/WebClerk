from decimal import Decimal
from django.db import models
from .base_transaction_model import TransactionBaseModel
from common import models as common_models


class Requisition(TransactionBaseModel):
    # Add any Requisition-specific fields or methods here
    BASE_INT_DEFAULT = Decimal("0")  # Define a default value for quantity


class RequisitionStd(common_models.BaseModel):
    """Lightweight standardized requisition model (v2 pattern).

    Intent: simple BaseModel with a few searchable fields and full universal envelopes.
    Used by views.requisition.* and tests expecting RequisitionStd endpoints.
    """

    name = models.CharField(max_length=128, default="", db_index=True)
    purpose = models.CharField(max_length=128, default="", db_index=True)
    status = models.CharField(max_length=50, default="draft", blank=True, db_index=True)

    class Meta:
        db_table = 'requisitions_std'


__all__ = ["Requisition", "RequisitionStd"]