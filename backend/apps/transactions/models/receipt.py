from django.db import models
from common.models import BaseModel


class Receipt(BaseModel):
    """Receipt header representing a receiving transaction.
    
    A receipt is created when:
    - Purchase order lines are received (from vendor)
    - Work order lines are completed (manufacturing)
    - Inventory adjustments are made (cycle count, shrinkage, etc.)
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
    notes = models.TextField(blank=True, help_text="Overall notes for this receipt")

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

    # Journalizing lock — 0 means editable, non-zero epoch ms means locked (GL has this data)
    dt_journaled = models.BigIntegerField(default=0, db_index=True,
        help_text="UTC epoch ms when journalized to GL. 0=editable, non-zero=locked.")

    class Meta:
        db_table = "receipt"
        indexes = [
            models.Index(fields=['source_type', 'dt_received']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"R:{self.ida}" if self.ida else f"R:{self.pk}"


__all__ = ["Receipt"]