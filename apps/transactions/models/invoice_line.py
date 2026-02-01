from django.db import models
from .base_line_model import BaseSellLineModel


class InvoiceLine(BaseSellLineModel):
    invoice = models.ForeignKey(
        "transactions.Invoice",
        related_name="lines",
        on_delete=models.CASCADE,
        db_column="invoice_id",  # Keep existing column name
    )

    class Meta:
        db_table = "invoice_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.invoice

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.invoice_id


__all__ = ["InvoiceLine"]