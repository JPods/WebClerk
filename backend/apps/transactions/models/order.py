from django.db import models
from .base_transaction_model import TransactionBaseModel


class Order(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    # ── Rep assignment (Bill, 2026-09-20) ────────────────────────────
    # A value, not a ForeignKey: a rep org is a reference, and deleting one must never
    # cascade into the records it was assigned to. rep_id carries the assignment and
    # attention_rep the person at that rep, the way attention names the person at the org.
    rep_id = models.BigIntegerField(null=True, blank=True, db_index=True,
        help_text="Rep org credited with this document")
    attention_rep = models.CharField(max_length=255, blank=True, null=True,
        help_text="The person at the rep")

    class Meta:
        db_table = "orders"

    def __str__(self) -> str:
        return str(getattr(self, "ida", "")) or f"Order({self.pk})"


__all__ = ["Order"]