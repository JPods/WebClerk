from decimal import Decimal
from django.db import models
from .base_line_model import BaseExecLineModel

class RequisitionLine(BaseExecLineModel):
    requisition_id = models.ForeignKey(
        "transactions.Requisition",  # string ref avoids circular import
        on_delete=models.CASCADE,
        related_name="lines",
    )

    class Meta:
        db_table = "requisition_lines"