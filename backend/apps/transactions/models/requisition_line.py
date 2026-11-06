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

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types). Missing
        until 2026-11-06: no requisition line could be saved — the delete guard read it."""
        return self.requisition

    @property
    def parent_id_value(self):
        return self.requisition_id

    def __str__(self):
        return f"RequisitionLine {self.id} on requisition {self.requisition_id}"

    class Meta:
        db_table = "requisition_lines"