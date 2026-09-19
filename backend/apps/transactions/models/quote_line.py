from django.db import models
from .base_line_model import BaseSellLineModel


class QuoteLine(BaseSellLineModel):
    quote = models.ForeignKey(
        "transactions.Quote",
        related_name="lines",
        on_delete=models.CASCADE,
        db_column="quote_id",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"QuoteLine {self.id} on quote {self.quote_id}"

    class Meta:
        db_table = "quote_lines"

    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.quote

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.quote_id


__all__ = ["QuoteLine"]