from django.db import models
from common.models import BaseModel


class PaymentTerm(BaseModel):
    """Payment terms for transactions (e.g., Net 30, COD, etc.)"""

    class Meta:
        db_table = "payment_terms"

    name = models.CharField(max_length=100, unique=True, help_text="Name of the payment term")
    description = models.TextField(blank=True, help_text="Description of the payment term")
    days = models.IntegerField(default=0, help_text="Number of days for payment")
    is_active = models.BooleanField(default=True, help_text="Whether this term is active")

    def __str__(self):
        return self.name


class PaymentMethod(BaseModel):
    """Payment methods (e.g., Cash, Check, Credit Card, etc.)"""

    class Meta:
        db_table = "payment_methods"

    name = models.CharField(max_length=100, unique=True, help_text="Name of the payment method")
    description = models.TextField(blank=True, help_text="Description of the payment method")
    is_active = models.BooleanField(default=True, help_text="Whether this method is active")

    def __str__(self):
        return self.name


class Payment(BaseModel):
    """Payments made against invoices"""

    class Meta:
        db_table = "payments"

    # Existing fields
    invoice = models.ForeignKey(
        'transactions.Invoice',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Invoice this payment is for"
    )
    contact = models.ForeignKey(
        'core.Contact',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Contact who made the payment"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Payment amount")
    dt_payment = models.DateTimeField(help_text="Date the payment was made")
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Method of payment"
    )
    payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Payment term applied"
    )
    reference_number = models.CharField(max_length=100, blank=True, help_text="Check number, transaction ID, etc.")
    notes = models.TextField(blank=True, help_text="Additional notes about the payment")

    # Payment gateway integration fields
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    PAYMENT_GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('manual', 'Manual'),
    ]

    gateway = models.CharField(
        max_length=20,
        choices=PAYMENT_GATEWAY_CHOICES,
        default='manual',
        help_text="Payment gateway used"
    )
    id_gateway_transaction = models.CharField(
        max_length=255,
        blank=True,
        help_text="Transaction ID from the payment gateway"
    )
    id_gateway_payment_intent = models.CharField(
        max_length=255,
        blank=True,
        help_text="Payment intent ID from Stripe or equivalent"
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Current payment status"
    )
    gateway_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw response from payment gateway"
    )
    dt_processed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the payment was processed by gateway"
    )
    reconciled = models.BooleanField(
        default=False,
        help_text="Whether this payment has been reconciled"
    )
    dt_reconciliation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the payment was reconciled"
    )
    fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Processing fee charged by gateway"
    )

    def __str__(self):
        return f"Payment #{self.id} - {self.amount} ({self.status}) for Invoice #{self.invoice_id}"

    def mark_as_completed(self):
        """Mark payment as completed"""
        self.status = 'completed'
        self.dt_processed = models.functions.Now()
        self.save()

    def mark_as_failed(self, reason=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if reason:
            self.notes = f"{self.notes}\nFailure reason: {reason}".strip()
        self.save()

    def reconcile(self):
        """Mark payment as reconciled"""
        self.reconciled = True
        self.dt_reconciliation = models.functions.Now()
        self.save()


__all__ = ["Payment", "PaymentMethod", "PaymentTerm"]