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
    metadata = models.JSONField(default=dict, blank=True, null=True, help_text="Payment history and balances")

    def __str__(self) -> str:
        return f"Invoice #{self.id} ({self.ida or ''})"


__all__ = ["Invoice"]