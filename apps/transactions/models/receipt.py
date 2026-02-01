from django.db import models
from common.models import BaseModel
from .base_line_model import BaseExecLineModel


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


class ReceiptLine(BaseExecLineModel):
    """Receipt line representing a single item received.
    
    Inherits from BaseExecLineModel to get:
    - item (JSONField): Item details including item_id, description, etc.
    - quantity (JSONField): Quantities including placed/received
    - cost (JSONField): Cost information including unit cost
    - tax, physical, metadata, refs, prefs (JSONFields)
    
    Additional fields track:
    - Source line (purchase_line or workorder_line)
    - Warehouse where inventory was received
    - Lot/serial tracking
    """
    receipt = models.ForeignKey(
        Receipt,
        related_name="lines",
        on_delete=models.CASCADE,
    )
    
    # Source line references (one will be set based on receipt.source_type)
    purchase_line = models.ForeignKey(
        "transactions.PurchaseLine",
        related_name="receipt_lines",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Source purchase line (if receipt from PO)"
    )
    workorder_line = models.ForeignKey(
        "transactions.WorkOrderLine",
        related_name="receipt_lines",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Source workorder line (if receipt from WO)"
    )
    
    # Warehouse where inventory was received
    warehouse = models.ForeignKey(
        "products.Warehouse",
        related_name="receipt_lines",
        on_delete=models.PROTECT,
        help_text="Warehouse where inventory was received"
    )
    
    # Inventory layer created for this receipt (FIFO/LIFO tracking)
    inventory_layer = models.ForeignKey(
        "products.InventoryLayer",
        related_name="receipt_lines",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Inventory layer/stack created for this receipt"
    )
    
    # Lot/serial tracking
    lot = models.CharField(max_length=100, blank=True, help_text="Lot number")
    serial_batch = models.CharField(max_length=100, blank=True, help_text="Serial or batch number")
    
    # Adjustment-specific field
    adjustment_reason = models.CharField(
        max_length=50,
        blank=True,
        help_text="Reason for adjustment (cycle_count, damage, shrinkage, found, etc.)"
    )

    class Meta:
        db_table = "receipt_line"
        indexes = [
            models.Index(fields=['receipt', 'warehouse']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        item_desc = ''
        if self.item and isinstance(self.item, dict):
            item_desc = self.item.get('description', '') or self.item.get('item_id', '')
        return f"RL:{self.pk} - {item_desc}"
    
    @property
    def qty_received(self) -> float:
        """Get the received quantity from the quantity JSON."""
        if self.quantity and isinstance(self.quantity, dict):
            return float(self.quantity.get('placed', 0) or self.quantity.get('received', 0) or 0)
        return 0.0
    
    @property
    def unit_cost(self) -> float:
        """Get the unit cost from the cost JSON."""
        if self.cost and isinstance(self.cost, dict):
            return float(self.cost.get('unit', 0) or 0)
        return 0.0


__all__ = ["Receipt", "ReceiptLine"]