from django.db import models
from common.models import BaseModel


def default_receipt_totals() -> dict:
    """Default totals for Receipt — AP mirror of Invoice totals.

    total = vendor_invoice_amount (what we owe).
    paid  = sum of cash_out payments applied (mirrors Invoice totals.received).
    balance = total - paid.
    """
    return {
        "total": 0,       # vendor invoice amount — what we owe
        "freight": 0,     # vendor invoice freight
        "duty": 0,        # duties/tariffs
        "handling": 0,    # handling/insurance/non-product
        "vat": 0,         # VAT
        "paid": 0,        # payments applied (AP mirror of AR 'received')
        "balance": 0,     # total - paid
    }


class Receipt(BaseModel):
    """Receipt header representing a receiving transaction.

    A receipt is created when:
    - Purchase order lines are received (from vendor)
    - Work order lines are completed (manufacturing)
    - Inventory adjustments are made (cycle count, shrinkage, etc.)

    AP payment flow: Payment (cash_out) applies to Receipt the same way
    Payment (cash_in) applies to Invoice. totals.paid / totals.balance
    mirror Invoice's totals.received / totals.balance.
    """
    # Source type for this receipt
    SOURCE_PURCHASE = 'purchase_receipt'
    SOURCE_WORKORDER = 'workorder_completion'
    SOURCE_ADJUSTMENT = 'inventory_adjustment'
    SOURCE_CHOICES = [
        (SOURCE_PURCHASE, 'Purchase Receipt'),
        (SOURCE_WORKORDER, 'WorkOrder Completion'),
        (SOURCE_ADJUSTMENT, 'Inventory Adjustment'),
    ]
    
    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default=SOURCE_PURCHASE,
        db_index=True,
        help_text="Type of receiving transaction"
    )
    dt_received = models.DateTimeField(auto_now_add=True)

    # ── Landed cost fields (receipt-header-level, allocated to lines) ──
    # These are the total costs for the entire inshipment. The allocation
    # service spreads them across ReceiptLines → InventoryLayers.
    vendor_invoice_freight = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total freight on vendor invoice for this inshipment"
    )
    duty = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total duties/tariffs for this inshipment"
    )
    handling = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total handling/insurance/non-product costs"
    )
    vat = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total VAT for this inshipment"
    )
    vendor_invoice_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total vendor invoice amount"
    )
    ALLOCATION_CHOICES = [
        ('value', 'By Value (cost-proportional)'),
        ('weight', 'By Weight'),
        ('quantity', 'By Quantity'),
    ]
    allocation_method = models.CharField(
        max_length=20, choices=ALLOCATION_CHOICES, default='value',
        help_text="How to spread header costs across receipt lines"
    )
    
    # Optional FK to source transaction header
    purchase = models.ForeignKey(
        "transactions.Purchase",
        related_name="receipts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Source purchase order (if source_type=purchase_receipt)"
    )
    workorder = models.ForeignKey(
        "transactions.WorkOrder",
        related_name="receipts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Source work order (if source_type=workorder_completion)"
    )

    # Counterparty snapshot
    company = models.JSONField(default=dict, blank=True,
        help_text="Counterparty snapshot: {id, ida, name, is_individual, attention, email, phone, domain, notes}")

    # Header-level totals — AP mirror of Invoice totals (PJPV source of truth)
    totals = models.JSONField(default=default_receipt_totals, blank=True, null=True,
        help_text="AP totals: total, freight, duty, handling, vat, paid, balance")

    # Journalizing lock — 0 means editable, non-zero epoch ms means locked (GL has this data)
    dt_journaled = models.BigIntegerField(default=0, db_index=True,
        help_text="UTC epoch ms when journalized to GL. 0=editable, non-zero=locked.")

    class Meta:
        db_table = "receipt"
        indexes = [
            models.Index(fields=['source_type', 'dt_received']),
        ]

    def _populate_company_snapshot(self):
        """Copy company snapshot from the linked purchase's vendor + contact."""
        org = None
        if self.purchase_id:
            try:
                org = self.purchase.vendor
            except Exception:
                pass
        if not org:
            return
        # Use purchase's contact if available
        contact = None
        if self.purchase_id:
            try:
                contact = self.purchase.contact
            except Exception:
                pass
        current = self.company if isinstance(self.company, dict) else {}
        current_contact_id = current.get('contact_id')
        if (current.get('id') == org.id
                and current.get('name')
                and current_contact_id == (contact.pk if contact else None)):
            return
        self.company = org.build_company_snapshot(contact=contact)

    def _sync_totals_from_scalars(self):
        """Keep totals envelope in sync with scalar landed-cost fields.

        vendor_invoice_amount is the source of truth for totals.total.
        Scalar fields remain for backward compat and direct queries;
        totals envelope is the PJPV source of truth for payment tracking.
        """
        t = self.totals if isinstance(self.totals, dict) else default_receipt_totals()
        t['total'] = float(self.vendor_invoice_amount)
        t['freight'] = float(self.vendor_invoice_freight)
        t['duty'] = float(self.duty)
        t['handling'] = float(self.handling)
        t['vat'] = float(self.vat)
        t['balance'] = float(self.vendor_invoice_amount) - float(t.get('paid', 0))
        self.totals = t

    def save(self, *args, **kwargs):
        self._populate_company_snapshot()
        self._sync_totals_from_scalars()
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"R:{self.ida}" if self.ida else f"R:{self.pk}"


__all__ = ["Receipt"]