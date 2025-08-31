from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from .item_base_model import ItemLinkedBase
from .warehouse import Warehouse


class InventoryStack(ItemLinkedBase):
    """Received quantity at a specific unit cost (lot/stack)."""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventory_stacks")
    source = models.JSONField(default=dict, blank=True)
    # dt_s in metadata.history
    #received_dt = models.BigIntegerField(db_index=True)
    quantity = models.JSONField(default=dict, blank=True)
    #qty_perished
    #qty_received = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    #qty_remaining = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    cost = models.JSONField(default=dict, blank=True)  
    # (unit, freight, vat, etc... optional for landed cost breakdown)
    lot = models.CharField(max_length=80, blank=True, db_index=True)
    serial_batch = models.CharField(max_length=80, blank=True)
    source_doc_type = models.CharField(max_length=40, blank=True)
    source_doc_id = models.BigIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=("item", "warehouse"), name="inv_item_wh_idx"),
            models.Index(fields=("lot",), name="inv_lot_idx"),
            GinIndex(fields=["quantity"], name="invstack_quantity_gin_idx"),
        ]

    def __str__(self):  # pragma: no cover
        qty = getattr(self, "quantity", {})
        return f"Stack#{self.pk}:{getattr(self.item, 'pk', '?')}:{qty}"


class SiteInventory(ItemLinkedBase):
    """Aggregated item position at a site (rollup / denormalized quantities).

    Purpose: Fast lookups for availability (on hand / reserved / backordered) without scanning stacks.
    Future: Could add qty_allocated, qty_in_transit. Maintains integrity via service layer updates.
    """

    site_code = models.CharField(max_length=40, db_index=True)
    # qty_on_hand = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    # qty_reserved = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    # qty_backordered = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    quantity = models.JSONField(default=dict, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "site_code"], name="uniq_item_site"),
        ]
        indexes = [
            models.Index(fields=("site_code",), name="siteinv_site_idx"),
            GinIndex(fields=["quantity"], name="siteinv_quantity_gin_idx"),
        ]


class InventoryMovement(ItemLinkedBase):
    """Immutable movement ledger (optional future use; scaffold only).

    Records inventory-affecting events (receipts, issues, adjustments) for auditing and
    reconstruction of site / stack balances. Not yet integrated with services.
    """

    MOVEMENT_RECEIPT = "receipt"
    MOVEMENT_ISSUE = "issue"
    MOVEMENT_ADJUST = "adjust"
    MOVEMENT_TYPES = [
        (MOVEMENT_RECEIPT, "Receipt"),
        (MOVEMENT_ISSUE, "Issue"),
        (MOVEMENT_ADJUST, "Adjust"),
    ]

    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventory_movements")
    source_stack = models.ForeignKey(
        InventoryStack, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements"
    )
    site_code = models.CharField(max_length=40, db_index=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    reason = models.CharField(max_length=120, blank=True)
    source_doc_type = models.CharField(max_length=40, blank=True)
    source_doc_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=("movement_type",), name="invmove_type_idx"),
            models.Index(fields=("item", "warehouse"), name="invmove_item_wh_idx"),
        ]
