from django.db import models
from .base_line_model import BaseExecLineModel


class WorkOrderLine(BaseExecLineModel):
    workorder = models.ForeignKey(
        "transactions.WorkOrder",
        related_name="lines",
        on_delete=models.CASCADE,
        db_column="workorder_id",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"WorkOrderLine {self.id} on workorder {self.workorder_id}"

    class Meta:
        db_table = "work_order_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.workorder

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.workorder_id


__all__ = ["WorkOrderLine"]