from django.db import models
from common.models import BaseModel


class PaymentApplication(BaseModel):
    """Links payments to invoices with applied amounts."""

    class Meta:
        db_table = "payment_applications"
        unique_together = ['payment', 'invoice']  # One application per payment-invoice pair

    payment = models.ForeignKey(
        'transactions.Payment',
        on_delete=models.CASCADE,
        related_name='applications',
        db_column='payment_id',
        help_text="The payment being applied"
    )
    invoice = models.ForeignKey(
        'transactions.Invoice',
        on_delete=models.CASCADE,
        related_name='payment_applications',
        db_column='invoice_id',
        help_text="The invoice receiving the payment"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Amount of this payment applied to this invoice"
    )
    applied_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this application was created"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this application"
    )

    def __str__(self):
        return f"PaymentApplication: {self.payment_id} -> {self.invoice_id} (${self.amount})"

    def clean(self):
        """Validate that applied amount doesn't exceed payment or invoice balance."""
        from django.core.exceptions import ValidationError

        if self.amount <= 0:
            raise ValidationError("Applied amount must be positive")

        # Check payment has sufficient remaining amount
        total_applied = sum(
            app.amount for app in self.payment.applications.all()
            if app.pk != self.pk  # Exclude self if updating
        )
        remaining = self.payment.amount - total_applied
        if self.amount > remaining:
            raise ValidationError(
                f"Applied amount (${self.amount}) exceeds payment remaining (${remaining})"
            )

        # Check invoice has sufficient balance
        invoice_totals = self.invoice.totals or {}
        total_due = invoice_totals.get('total', 0)
        already_paid = invoice_totals.get('received', 0)
        balance = total_due - already_paid
        if self.amount > balance:
            raise ValidationError(
                f"Applied amount (${self.amount}) exceeds invoice balance (${balance})"
            )


__all__ = ["PaymentApplication"]