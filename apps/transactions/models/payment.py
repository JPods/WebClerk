from django.db import models
from django.utils.timezone import now as django_now

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
        ('received', 'Received'),      # money in (+)
        ('expense', 'Expense'),        # money out (-)
    ]

    type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='expense',
        db_index=True,
        help_text="Required. Received=money in, Expense=money out. Category tells the rest."
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
        null=True,
        blank=True,
        related_name='payments',
        db_column='contact_id',
        help_text="Contact who made or received the payment"
    )
    customer = models.ForeignKey(
        'orgs.OrgBase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments_as_customer',
        db_column='customer_id',
        help_text="Customer org — received payments"
    )
    vendor = models.ForeignKey(
        'orgs.OrgBase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments_as_vendor',
        db_column='vendor_id',
        help_text="Vendor org — expense payments"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Positive=money in (received), negative=money out (disbursed). SUM(amount) = net cash position.")
    available = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount remaining to apply. Starts = amount, decremented as applied to invoices.")
    tendered = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount physically tendered (cash scenarios). May exceed amount.")
    change = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Change returned. tendered - amount when tendered > amount.")
    dt_payment = models.DateTimeField(null=True, blank=True, default=django_now, help_text="Date the payment was made")
    method = models.CharField(
        max_length=100,
        blank=True,
        help_text="How they paid: visa_3425, check-WellsFargo, cash, etc. Freehand or select list."
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
    category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Expense bucket (e.g. Office Supplies, Travel). Maps to GL via select_list in Setting."
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
        parent = f"Invoice #{self.invoice_id}" if self.invoice_id else f"Purchase #{self.purchase_id}" if self.purchase_id else "unlinked"
        return f"Payment #{self.id} - {self.amount:+.2f} ({self.status}) for {parent}"

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

    GATEWAY_SAFE_KEYS = frozenset({
        'id', 'status', 'amount', 'currency', 'created', 'captured',
        'refunded', 'transaction_id', 'order_id', 'payment_id',
        'intent_id', 'capture_id', 'refund_id', 'fee', 'net',
        'payment_method_type', 'brand', 'last4', 'exp_month', 'exp_year',
        'receipt_url', 'failure_code', 'failure_message', 'outcome',
    })

    @classmethod
    def sanitize_gateway_response(cls, raw: dict) -> dict:
        """Strip PII and card data from gateway response before storage.

        Keeps only safe keys: transaction IDs, status, amounts, timestamps,
        last4/brand (non-sensitive card identifiers), failure info.
        """
        if not raw or not isinstance(raw, dict):
            return raw or {}
        sanitized = {}
        for key, value in raw.items():
            k = key.lower().replace('-', '_')
            if k in cls.GATEWAY_SAFE_KEYS:
                sanitized[key] = value
            elif isinstance(value, dict):
                nested = cls.sanitize_gateway_response(value)
                if nested:
                    sanitized[key] = nested
        return sanitized

    def save(self, *args, **kwargs):
        if not self.pk:
            # New payment: available starts equal to amount
            if not self.available:
                self.available = self.amount
            # New payment: tendered defaults to amount if not set
            if not self.tendered:
                self.tendered = self.amount
        # Compute change whenever tendered exceeds amount
        if self.tendered > abs(self.amount):
            self.change = self.tendered - abs(self.amount)
        if self.gateway_response and self.gateway != 'manual':
            self.gateway_response = self.sanitize_gateway_response(self.gateway_response)
        super().save(*args, **kwargs)

    def add_audit_entry(self, action: str, details: dict = None):
        """Add an entry to the audit trail"""
        if not self.metadata:
            self.metadata = default_metadata()
        audit_trail = self.metadata.get('audit_trail', [])
        entry = {
            'timestamp': django_now().isoformat(),
            'action': action,
            'details': details or {}
        }
        audit_trail.append(entry)
        self.metadata['audit_trail'] = audit_trail
        self.save(update_fields=['metadata'])


__all__ = ["Payment", "PaymentMethod", "PaymentTerm"]