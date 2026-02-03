from django.db import models
from .base_line_model import BaseExecLineModel


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
        "transactions.Receipt",
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
        null=True,
        blank=True,
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
        db_table = "receipt_line"  # Singular to match existing table
        indexes = [
            models.Index(fields=['receipt', 'warehouse']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        item_desc = ''
        if self.item and isinstance(self.item, dict):
            item_desc = self.item.get('description', '') or self.item.get('item_id', '')
        return f"RL:{self.pk} - {item_desc}"
    
    @property
    def parent(self):
        """Alias for the FK to parent transaction (uniform across all line types)."""
        return self.receipt

    @property
    def parent_id_value(self):
        """Raw FK id value for serialization."""
        return self.receipt_id

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


__all__ = ["ReceiptLine"]
