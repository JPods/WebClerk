from typing import TYPE_CHECKING
from django.db import models
from .base_line_model import BaseLineModel

if TYPE_CHECKING:
    from .invoice import Invoice


class InvoiceLine(BaseLineModel):
    parent = models.ForeignKey("transactions.Invoice", related_name="lines", on_delete=models.CASCADE)

    class Meta:
        db_table = "invoice_lines"