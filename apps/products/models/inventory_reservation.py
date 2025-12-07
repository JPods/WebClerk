from __future__ import annotations

from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal

from .inventory_layer import InventoryLayer
from .item import Item
from .warehouse import Warehouse


def default_context():  # simple JSONField default
    return {}


class InventoryReservation(models.Model):
    """Soft hold of inventory for a limited time (cart/seat style reservation).

    States:
      pending    - actively holding quantity from availability (not yet converted)
      committed  - converted to real issue (inventory permanently deducted)
      canceled   - released before commitment (put back)
      expired    - system reclaimed after ttl

    Reservation does NOT immediately reduce stack.quantity.issued; instead we
    track reserved qty per stack in this table and subtract logically when computing
    availability. On commit we convert to an actual issue; on release we simply drop.
    """

    STATE_PENDING = 'pending'
    STATE_COMMITTED = 'committed'
    STATE_CANCELED = 'canceled'
    STATE_EXPIRED = 'expired'
    STATES = [
        (STATE_PENDING, 'Pending'),
        (STATE_COMMITTED, 'Committed'),
        (STATE_CANCELED, 'Canceled'),
        (STATE_EXPIRED, 'Expired'),
    ]

    item_id = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='reservations')
    warehouse_id = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='reservations')
    inventorylayer_id = models.ForeignKey(InventoryLayer, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')
    qty = models.DecimalField(max_digits=14, decimal_places=4)
    state = models.CharField(max_length=20, choices=STATES, default=STATE_PENDING, db_index=True)
    dt_expires = models.DateTimeField(db_index=True)
    dt_committed = models.DateTimeField(null=True, blank=True)
    dt_released = models.DateTimeField(null=True, blank=True)
    context = models.JSONField(default=default_context, blank=True)
    reason = models.CharField(max_length=80, blank=True)
    dt_created = models.DateTimeField(auto_now_add=True)
    dt_modified = models.DateTimeField(auto_now=True)

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
            # lock self row
            r = type(self).objects.select_for_update().get(pk=self.pk)
            if r.state != self.STATE_PENDING:
                return False
            # Convert to real issue from stack (if still available)
            if r.inventorylayer_id and r.inventorylayer_id.remaining_qty() >= self.qty:
                r.inventorylayer_id.mark_issue(self.qty)
                r.inventorylayer_id.save(update_fields=['quantity', 'dt_modified', 'version'])
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
