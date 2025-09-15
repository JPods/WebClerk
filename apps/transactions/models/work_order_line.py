from decimal import Decimal
from django.db import models
from .base_line_model import BaseLineModel
from .work_order import Workorder


class WorkorderLine(BaseLineModel):
    parent = models.ForeignKey(Workorder, related_name="lines", on_delete=models.CASCADE)

    BASE_INT_DEFAULT = Decimal("0")
    quantity_completed = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)

    class Meta:
        db_table = "work_order_lines"