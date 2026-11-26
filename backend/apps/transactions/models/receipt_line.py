from django.db import models
from .base_line_model import BaseExecLineModel, EVENTS_HELP, default_events


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

    events = models.JSONField(default=default_events, blank=True, help_text=EVENTS_HELP)

    # Lot/serial tracking
    lot = models.CharField(max_length=100, blank=True, help_text="Lot number")
    serial_batch = models.CharField(max_length=100, blank=True, help_text="Serial or batch number")

    # Adjustment-specific field
    adjustment_reason = models.CharField(
        max_length=50,
        blank=True,
        help_text="Reason for adjustment (cycle_count, damage, shrinkage, found, etc.)"
    )

    def save(self, *args, **kwargs):
        self._assert_reduction_is_held()
        super().save(*args, **kwargs)

    def _assert_reduction_is_held(self):
        """A received line is corrected until its receipt is journalized: its quantity (readme 108,
        "Amendment confirmed") and its cost and charges (Bill, 2026-11-25: "Users should be able to
        change the cost. They are responsible." — replaces R3, the dock cost never changes). The
        line door brings the receipt's layers to their lines' landed cost after every change
        (line_door.reconcile_receipt_layers). A journalized receipt refuses both
        (_assert_parent_not_journalized). What is refused here is taking back units the layer no
        longer holds."""
        from apps.core.services.door import Refused
        stored = (type(self).objects.filter(pk=self.pk).values('quantity').first()
                  if self.pk else None) or {}
        was = float((stored.get('quantity') or {}).get('active') or 0)
        now = float((self.quantity or {}).get('active') or 0)
        if was and now < was - 1e-9 and self.inventory_layer_id:
            # A received quantity is corrected until the receipt is journalized (readme 108,
            # "Amendment confirmed"); a reduction only takes back what the layer still holds.
            from apps.products.models import InventoryLayer
            layer = InventoryLayer.objects.filter(pk=self.inventory_layer_id).first()
            held = float(layer.remaining_qty()) if layer else 0.0
            if was - now > held + 1e-9:
                gone = round(was - held, 6)
                raise Refused(409, 'received_already_used',
                              f'{gone:g} of the {was:g} received on this line have already left the shelf '
                              f'(shipped, used or scrapped), so this line can come down to {gone:g} at the '
                              f'least. A count workorder corrects the rest.',
                              {'line_id': self.pk, 'received': was, 'held': held, 'lowest': gone})

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
