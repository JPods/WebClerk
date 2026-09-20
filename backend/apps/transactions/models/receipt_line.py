from django.db import models
from .base_line_model import BaseExecLineModel


class ReceiptLine(BaseExecLineModel):
    """Receipt line representing a single item received.

    Inherits from BaseExecLineModel to get item / quantity / cost / tax / physical /
    metadata / refs / prefs, and — like every other child line — ``parent_line_id``,
    which names the purchase or workorder line this receipt line received against.
    The parent line's ``remaining`` is recomputed from its children by the one writer
    (services/line_parent.py), so the document moves when the goods do.

    What only a receipt line has: where it landed and what it landed as.
    """
    receipt = models.ForeignKey(
        "transactions.Receipt",
        related_name="lines",
        on_delete=models.CASCADE,
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
            return float(self.quantity.get('active', 0) or 0)
        return 0.0
    
    @property
    def unit_cost(self) -> float:
        """Get the unit cost from the cost JSON."""
        if self.cost and isinstance(self.cost, dict):
            return float(self.cost.get('unit', 0) or 0)
        return 0.0


__all__ = ["ReceiptLine"]
