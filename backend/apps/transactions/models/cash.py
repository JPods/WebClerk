from django.db import models
from django.utils.timezone import now as django_now

from common.models import BaseModel
from apps.transactions.choices import CASH_GATEWAY_CHOICES, CASH_STATUS_CHOICES


def default_refs() -> dict:
    """Default refs structure for cash lineage tracking."""
    return {
        "invoice_ids": [],   # AR: invoice IDs this cash applies to
        "receipt_ids": [],   # AP: receipt IDs this cash applies to
        "order_ids": [],     # Related order IDs for tracking
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




class Cash(BaseModel):
    """Cash — cash in (AR) and cash out (AP).

    cash_in: customer pays us → applied to Invoice via a Pending application record.
    cash_out: we pay vendor → applied to Receipt via the same pending path.
    """

    CASH_TYPE_CHOICES = [
        ('cash_in', 'Cash In'),        # money in (+) — AR
        ('cash_out', 'Cash Out'),      # money out (-) — AP
    ]

    type = models.CharField(
        max_length=20,
        choices=CASH_TYPE_CHOICES,
        default='cash_out',
        db_index=True,
        help_text="Required. cash_in=money in (AR), cash_out=money out (AP). Category tells the rest."
    )

    # Where this cash was created — polymorphic parent
    parent_id = models.BigIntegerField(
        blank=True, null=True, db_index=True,
        help_text="ID of the document where this cash was entered (order, invoice, customer)"
    )
    parent_model = models.CharField(
        max_length=20, blank=True, default='',
        db_index=True,
        help_text="Model of the parent document: order, invoice, customer, purchase"
    )

    # Parent transaction references
    invoice = models.ForeignKey(
        'transactions.Invoice',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cash_entries',
        db_column='invoice_id',
        help_text="Invoice this cash applies to (AR — received)"
    )
    purchase = models.ForeignKey(
        'transactions.Purchase',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cash_entries',
        db_column='purchase_id',
        help_text="Purchase order this cash relates to"
    )
    receipt = models.ForeignKey(
        'transactions.Receipt',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cash_entries',
        db_column='receipt_id',
        help_text="Receipt this cash applies to (AP — cash_out)"
    )
    contact_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        help_text="Contact id (value, not FK — cash survives contact deletion)"
    )
    customer = models.ForeignKey(
        'orgs.OrgBase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_entries_as_customer',
        db_column='customer_id',
        help_text="Customer org — cash received"
    )
    vendor = models.ForeignKey(
        'orgs.OrgBase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_entries_as_vendor',
        db_column='vendor_id',
        help_text="Vendor org — cash paid out"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Positive=cash in, negative=cash out. SUM(amount) = net cash position.")
    available = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount remaining to apply. Starts = amount, decremented as applied to invoices.")
    tendered = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount physically tendered (cash scenarios). May exceed amount.")
    change = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Change returned. tendered - amount when tendered > amount.")
    dt_cash = models.DateTimeField(null=True, blank=True, default=django_now, help_text="Date the cash moved")
    method = models.CharField(
        max_length=100,
        blank=True,
        help_text="How they paid: visa_3425, check-WellsFargo, cash, etc. Freehand or select list."
    )
    term = models.ForeignKey(
        'accounts.Term',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_entries',
        db_column='term_id',
        help_text="Term applied"
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Expense bucket (e.g. Office Supplies, Travel). Maps to GL via select_list in Setting."
    )
    reference_number = models.CharField(max_length=100, blank=True, help_text="Check number, transaction ID, etc.")

    # Cash gateway integration fields
    gateway = models.CharField(
        max_length=20,
        choices=CASH_GATEWAY_CHOICES,
        default='manual',
        help_text="Cash gateway used"
    )
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Transaction ID from the cash gateway"
    )
    gateway_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Payment intent ID from Stripe or equivalent"
    )
    # status — inherited from CoreModel
    gateway_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw response from cash gateway"
    )
    dt_processed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the cash was processed by gateway"
    )
    reconciled = models.BooleanField(
        default=False,
        help_text="Whether this cash has been reconciled"
    )
    dt_reconciliation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the cash was reconciled"
    )
    fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Processing fee charged by gateway"
    )

    # Counterparty snapshot
    company = models.JSONField(default=dict, blank=True,
        help_text="Counterparty snapshot: {id, ida, name, is_individual, attention, email, phone, domain, notes}")

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
        # This class carried TWO `class Meta` blocks. The second silently
        # replaced the first, so its `db_table = "cash_entries"` never took effect
        # and the table is the Django default, transactions_cash — which is what
        # the database actually holds. The false declaration is dropped rather
        # than honoured: honouring it would be a table rename nobody asked for.
        constraints = [
            # Webhook dedup: prevent duplicate cash from the same gateway event
            models.UniqueConstraint(
                fields=['gateway_payment_intent_id'],
                condition=~models.Q(gateway_payment_intent_id=''),
                name='uniq_cash_gateway_intent',
            ),
        ]

    def __str__(self):
        if self.invoice_id:
            parent = f"Invoice #{self.invoice_id}"
        elif self.receipt_id:
            parent = f"Receipt #{self.receipt_id}"
        elif self.purchase_id:
            parent = f"Purchase #{self.purchase_id}"
        else:
            parent = "unlinked"
        return f"Cash #{self.id} - {self.amount:+.2f} ({self.status}) for {parent}"

    def mark_as_completed(self):
        """Mark cash as completed"""
        self.status = 'completed'
        self.dt_processed = models.functions.Now()
        self.save()

    def mark_as_failed(self, reason=None):
        """Mark cash as failed"""
        self.status = 'failed'
        self.save()
        if reason:
            self.add_comment('process', f"Failure reason: {reason}", use_linkage=False)

    def reconcile(self):
        """Mark cash as reconciled"""
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

    def add_receipt_ref(self, receipt_id: int):
        """Add a receipt reference to the refs field"""
        if not self.refs:
            self.refs = default_refs()
        if receipt_id not in self.refs.get('receipt_ids', []):
            if 'receipt_ids' not in self.refs:
                self.refs['receipt_ids'] = []
            self.refs['receipt_ids'].append(receipt_id)
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
        'refunded', 'transaction_id', 'order_id', 'cash_id',
        'intent_id', 'capture_id', 'refund_id', 'fee', 'net',
        'cash_method_type', 'brand', 'last4', 'exp_month', 'exp_year',
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

    def _populate_company_snapshot(self):
        """Copy company snapshot from the linked customer or vendor OrgBase + contact."""
        org = None
        if self.customer_id:
            try:
                org = self.customer
            except Exception:
                pass
        if not org and self.vendor_id:
            try:
                org = self.vendor
            except Exception:
                pass
        if not org:
            return
        # Resolve contact from the cash's contact_id if present
        contact = None
        if self.contact_id:
            from apps.core.models import Contact as ContactModel
            contact = ContactModel.objects.filter(pk=self.contact_id).first()
        current = self.company if isinstance(self.company, dict) else {}
        current_contact_id = current.get('contact_id')
        if (current.get('id') == org.id
                and current.get('name')
                and current_contact_id == (contact.pk if contact else None)):
            return
        self.company = org.build_company_snapshot(contact=contact)

    def save(self, *args, **kwargs):
        self._populate_company_snapshot()
        # Checkbook convention: the sign is the truth. Money in is cash_in, money out
        # cash_out (Bite 2 #10: receipts saved without a type were stored as cash_out).
        if self.amount:
            self.type = 'cash_in' if self.amount > 0 else 'cash_out'
            update_fields = kwargs.get('update_fields')
            if update_fields is not None and 'type' not in update_fields:
                kwargs['update_fields'] = list(update_fields) + ['type']
        if not self.pk:
            # New cash: available starts equal to amount
            if not self.available:
                self.available = self.amount
            # New cash: tendered defaults to amount if not set
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


__all__ = ["Cash"]