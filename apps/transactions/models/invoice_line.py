from decimal import Decimal
from typing import TYPE_CHECKING
from django.db import models
from .base_line_model import BaseLineModel

if TYPE_CHECKING:
    from .invoice import Invoice


class InvoiceLine(BaseLineModel):
    parent = models.ForeignKey("transactions.Invoice", related_name="lines", on_delete=models.CASCADE)

    BASE_INT_DEFAULT = Decimal("0")
    quantity_packed = models.DecimalField(max_digits=12, decimal_places=0, default=BASE_INT_DEFAULT)

    class Meta:
        db_table = "invoice_lines"