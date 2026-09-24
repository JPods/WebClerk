from django.db import models
from .base_transaction_model import TransactionBaseModel


class Invoice(TransactionBaseModel):
    # Totals: inherited from TransactionBaseModel.update_sell_cost_totals()
    # One engine: recalculate_totals(). JSON is source of truth.

    INVOICE_TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('proforma', 'Pro Forma'),
        ('credit_note', 'Credit Note'),
        ('deposit', 'Deposit'),
    ]

    class Meta:
        db_table = "invoices"

    invoice_type = models.CharField(
        max_length=20, choices=INVOICE_TYPE_CHOICES, default='invoice',
        db_index=True, help_text="Invoice / Pro Forma / Credit Note / Deposit")

    refs = models.JSONField(default=dict, blank=True, null=True, help_text="References like order_id")
    # The rep who made the sale, carried from the order (Bill, 2026-09-23) — a value, not a
    # ForeignKey, as on quote and order: deleting a rep org must never cascade into invoices.
    rep_id = models.BigIntegerField(null=True, blank=True, db_index=True,
        help_text="Rep org credited with this sale")
    attention_rep = models.CharField(max_length=255, blank=True, null=True,
        help_text="The person at the rep")
    metadata = models.JSONField(default=dict, blank=True, null=True, help_text="Cash history and balances")

    def __str__(self) -> str:
        return f"Invoice #{self.id} ({self.ida or ''})"


__all__ = ["Invoice"]