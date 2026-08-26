from __future__ import annotations

from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal

from apps.products.choices import INVENTORY_RESERVATION_STATE_CHOICES
from .inventory_layer import InventoryLayer
from .item import Item
from .warehouse import Warehouse
from .item_base_model import ItemLinkedBase


class InventoryReservation(ItemLinkedBase):
    """Soft hold of inventory for a limited time (cart/seat style reservation).

    States:
      pending    - actively holding quantity from availability (not yet converted)
      committed  - converted to real issue (inventory permanently deducted)
      canceled   - released before commitment (put back)
      expired    - system reclaimed after ttl

    Reservation does NOT immediately reduce stack.quantity.issued; instead we
    track reserved qty per stack in this table and subtract logically when computing
    availability. On commit we convert to an actual issue; on release we simply drop.

    Inherits from ItemLinkedBase:
      item FK, item_ida, description, status (+ all BaseModel fields)
    """

    STATE_PENDING = 'pending'
    STATE_COMMITTED = 'committed'
    STATE_CANCELED = 'canceled'
    STATE_EXPIRED = 'expired'
    STATES = INVENTORY_RESERVATION_STATE_CHOICES

    # Override item FK to set related_name specific to reservations
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='reservations', db_column='item_id')

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='reservations', db_column='warehouse_id')
    inventory_layer = models.ForeignKey(InventoryLayer, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations', db_column='inventorylayer_id')
    qty = models.DecimalField(max_digits=14, decimal_places=4)
    state = models.CharField(max_length=20, choices=STATES, default=STATE_PENDING, db_index=True)
    dt_expires = models.DateTimeField(db_index=True)
    dt_committed = models.DateTimeField(null=True, blank=True)
    dt_released = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=80, blank=True)

    def __str__(self):
        label = self.item_ida or f'Item {self.item_id}'
        return f"Reservation {self.id} ({self.state}) — {label}"

    class Meta:
        indexes = [
            models.Index(fields=("state", "dt_expires"), name="invres_state_exp_idx"),
            models.Index(fields=("item_id", "warehouse_id", "state"), name="invres_item_wh_state_idx"),
        ]

    # --- Core transitions -------------------------------------------------
    def commit(self):
        if self.state != self.STATE_PENDING:
            return False
        with transaction.atomic():
            r = type(self).objects.select_for_update().get(pk=self.pk)
            if r.state != self.STATE_PENDING:
                return False
            if r.inventory_layer and r.inventory_layer.remaining_qty() >= self.qty:
                r.inventory_layer.mark_issue(self.qty)
                r.inventory_layer.save(update_fields=['quantity', 'dt_modified', 'version'])
            r.state = self.STATE_COMMITTED
            r.dt_committed = timezone.now()
            r.save(update_fields=['state', 'dt_committed'])
        return True

    def release(self, reason: str = 'canceled'):
        if self.state != self.STATE_PENDING:
            return False
        self.state = self.STATE_CANCELED
        self.dt_released = timezone.now()
        self.reason = reason[:80]
        self.save(update_fields=['state', 'dt_released', 'reason'])
        return True

    def mark_expired(self):
        if self.state != self.STATE_PENDING:
            return False
        self.state = self.STATE_EXPIRED
        self.dt_released = timezone.now()
        self.save(update_fields=['state', 'dt_released'])
        return True

    # --- Helpers ----------------------------------------------------------
    @property
    def is_active(self):
        return self.state == self.STATE_PENDING and self.dt_expires > timezone.now()
