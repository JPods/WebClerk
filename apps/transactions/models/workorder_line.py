from django.db import models
from .base_line_model import BaseExecLineModel


class WorkOrderLine(BaseExecLineModel):
    workorder_id = models.ForeignKey(
        "transactions.WorkOrder",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "work_order_lines"