from django.db import models

from common.models import BaseModel
from apps.transactions.choices import PAYMENT_GATEWAY_CHOICES, PAYMENT_STATUS_CHOICES


def default_refs() -> dict:
    """Default refs structure for payment lineage tracking."""
    return {
        "invoice_ids": [],  # List of invoice IDs this payment applies to
        "order_ids": [],    # Related order IDs for tracking
        "source": {"type": "", "id": 0}  # Source transaction reference
    }


def default_metadata() -> dict:
    """Default metadata structure for reconciliation and additional data."""
    return {
        "reconciliation": {
            "batch_id": None,
            "statement_date": None,
            "notes": ""
        },
        "gateway_metadata": {},
        "processing_fees": [],
        "audit_trail": []
    }


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

    PAYMENT_TYPE_CHOICES = [
        ('received', 'Received'),      # AR — money in (customer pays us)
        ('disbursed', 'Disbursed'),     # AP — money out (we pay vendor/employee)
    ]

    type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='received',
        db_index=True,
        help_text="Direction: received (AR, money in) or disbursed (AP, money out)"
    )

    # Parent transaction references
    invoice = models.ForeignKey(
        'transactions.Invoice',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        db_column='invoice_id',
        help_text="Invoice this payment applies to (AR — received)"
    )
    purchase = models.ForeignKey(
        'transactions.Purchase',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        db_column='purchase_id',
        help_text="Purchase this payment applies to (AP — disbursed)"
    )
    contact = models.ForeignKey(
        'core.Contact',
        on_delete=models.CASCADE,
        related_name='payments',
        db_column='contact_id',
        help_text="Contact who made or received the payment"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Payment amount")
    dt_payment = models.DateTimeField(help_text="Date the payment was made")
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        db_column='paymentmethod_id',
        help_text="Method of payment"
    )
    payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        db_column='paymentterm_id',
        help_text="Payment term applied"
    )
    reference_number = models.CharField(max_length=100, blank=True, help_text="Check number, transaction ID, etc.")
    notes = models.TextField(blank=True, help_text="Additional notes about the payment")

    # Payment gateway integration fields
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

    # JSONB fields for lineage tracking and metadata
    refs = models.JSONField(
        default=default_refs,
        blank=True,
        null=True,
        help_text="References to related transactions (invoices, orders, etc.)"
    )
    metadata = models.JSONField(
        default=default_metadata,
        blank=True,
        null=True,
        help_text="Additional metadata for reconciliation, gateway data, and audit trail"
    )

    class Meta:
        constraints = [
            # Webhook dedup: prevent duplicate payments from the same gateway event
            models.UniqueConstraint(
                fields=['id_gateway_payment_intent'],
                condition=~models.Q(id_gateway_payment_intent=''),
                name='uniq_payment_gateway_intent',
            ),
        ]

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

    def add_invoice_ref(self, invoice_id: int):
        """Add an invoice reference to the refs field"""
        if not self.refs:
            self.refs = default_refs()
        if invoice_id not in self.refs.get('invoice_ids', []):
            self.refs['invoice_ids'].append(invoice_id)
            self.save(update_fields=['refs'])

    def add_order_ref(self, order_id: int):
        """Add an order reference to the refs field"""
        if not self.refs:
            self.refs = default_refs()
        if order_id not in self.refs.get('order_ids', []):
            self.refs['order_ids'].append(order_id)
            self.save(update_fields=['refs'])

    def set_source_ref(self, ref_type: str, ref_id: int):
        """Set the source reference"""
        if not self.refs:
            self.refs = default_refs()
        self.refs['source'] = {'type': ref_type, 'id': ref_id}
        self.save(update_fields=['refs'])

    def add_reconciliation_note(self, note: str):
        """Add a note to reconciliation metadata"""
        if not self.metadata:
            self.metadata = default_metadata()
        reconciliation = self.metadata.get('reconciliation', {})
        reconciliation['notes'] = note
        self.metadata['reconciliation'] = reconciliation
        self.save(update_fields=['metadata'])

    def add_audit_entry(self, action: str, details: dict = None):
        """Add an entry to the audit trail"""
        if not self.metadata:
            self.metadata = default_metadata()
        audit_trail = self.metadata.get('audit_trail', [])
        entry = {
            'timestamp': models.functions.Now(),
            'action': action,
            'details': details or {}
        }
        audit_trail.append(entry)
        self.metadata['audit_trail'] = audit_trail
        self.save(update_fields=['metadata'])


__all__ = ["Payment", "PaymentMethod", "PaymentTerm"]