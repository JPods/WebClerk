from decimal import Decimal
from django.db import models
from .base_line_model import BaseExecLineModel

class RequisitionLine(BaseExecLineModel):
    requisition = models.ForeignKey(
        "transactions.Requisition",  # string ref avoids circular import
        on_delete=models.CASCADE,
        related_name="lines",
        db_column='requisition_id',
    )

    def __str__(self):
        return f"RequisitionLine {self.id} on requisition {self.requisition_id}"

    class Meta:
        db_table = "requisition_lines"