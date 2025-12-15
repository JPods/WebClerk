from django.db import models
from .base_line_model import BaseSellLineModel


class InvoiceLine(BaseSellLineModel):
    invoice_id = models.ForeignKey(
        "transactions.Invoice",
        related_name="lines",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "invoice_lines"