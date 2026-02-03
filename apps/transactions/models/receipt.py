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

    class Meta:
        db_table = "receipt"
        indexes = [
            models.Index(fields=['source_type', 'dt_received']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"R:{self.ida}" if self.ida else f"R:{self.pk}"


__all__ = ["Receipt"]