from common.models import CoreModel
from django.db import models


class PendingPaymentApplication(CoreModel):
    """Every payment application creates a pending record first.
    Applied immediately if invoice unlocked, queued if locked.
    One path, one audit trail."""

    STATE_PENDING = "pending"
    STATE_APPLIED = "applied"
    STATE_CANCELED = "canceled"
    STATE_CHOICES = [
        ("pending", "Pending"),
        ("applied", "Applied"),
        ("canceled", "Canceled"),
    ]

    payment = models.ForeignKey(
        'transactions.Payment',
        on_delete=models.CASCADE,
        related_name='pending_applications',
    )
    invoice = models.ForeignKey(
        'transactions.Invoice',
        on_delete=models.CASCADE,
        related_name='pending_payments',
    )
    amount = models.DecimalField(max_digits=14, decimal_places=4)
    state = models.CharField(
        max_length=20, choices=STATE_CHOICES,
        default=STATE_PENDING, db_index=True,
    )
    reason = models.CharField(max_length=80, blank=True)
    request_ref = models.JSONField(default=dict, blank=True)
    dt_applied = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = 'pending_payment_applications'
        indexes = [
            models.Index(fields=("state",), name="pendpay_state_idx"),
            models.Index(fields=("invoice", "state"), name="pendpay_inv_state_idx"),
        ]

    def __str__(self):
        return f"PendingPayment #{self.pk}: {self.payment_id}->{self.invoice_id} ${self.amount} [{self.state}]"
