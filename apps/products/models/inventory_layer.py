from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from .item_base_model import ItemLinkedBase
from .warehouse import Warehouse

"""Inventory layer (stack) cost schema helpers.

We standardize the JSON shape stored in InventoryLayer.cost so downstream
code (pricing, valuation, reporting) can rely on consistent keys. All
monetary values are per-unit unless otherwise documented.

Keys:
    unit_po        - Original PO unit cost (base currency)
    fifo_snapshot  - FIFO pick price snapshot when layer created
    lifo_snapshot  - LIFO pick price snapshot when layer created
    moving_avg     - System moving average AFTER this receipt (per unit)
    landed         - Landed unit cost (unit_po + alloc freight/duty/handling - scrap allocation)
    freight        - Allocated freight per unit
    duty           - Allocated duties/tariffs per unit
    handling       - Allocated handling per unit
    vat            - VAT per unit (if tracked separately; 0 if N/A)
    scrap_cost     - Per-unit write‑off attributed to scrap for this layer
    trend_pct      - Percent change vs prior moving_avg (can be negative)
    currency       - 3-letter currency code
    exchange_rate  - Rate to convert currency -> accounting base (1 if same)

NOTE: Keep this lean; add new keys only with clear consumption paths.
"""

def default_cost() -> dict:
        return {
                "unit_po": 0.0,
                "fifo_snapshot": 0.0,
                "lifo_snapshot": 0.0,
                "moving_avg": 0.0,
                "landed": 0.0,
                "freight": 0.0,
                "duty": 0.0,
                "handling": 0.0,
                "vat": 0.0,
                "scrap_cost": 0.0,
                "trend_pct": 0.0,
                "currency": "USD",
                "exchange_rate": 1.0,
        }

STANDARD_COST_KEYS = tuple(default_cost().keys())  # Exportable reference


class InventoryLayer(ItemLinkedBase):
    """Received quantity at a specific unit cost (lot/stack)."""

    warehouse_id = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventory_layers")
    source = models.JSONField(default=dict, blank=True)
    # dt_s in metadata.history
    #dt_received = models.BigIntegerField(db_index=True)
    quantity = models.JSONField(default=dict, blank=True)
    #qty_perished
    #qty_received = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    #qty_remaining = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    # Standardized cost JSON (see default_cost docstring above)
    cost = models.JSONField(default=default_cost, blank=True)
    # (unit, freight, vat, etc... optional for landed cost breakdown)
    lot = models.CharField(max_length=80, blank=True, db_index=True)
    serial_numbers = models.JSONField(default=list, blank=True)  
    # list of serial numbers if tracked
    # if it exceeds a size, put it in an external doc store
    serial_batch = models.CharField(max_length=80, blank=True)
    source_doc_type = models.CharField(max_length=40, blank=True)
    source_doc_id = models.BigIntegerField(blank=True, null=True)
    # Soft concurrency / maintenance lock. When True direct issue mutations should enqueue a pending adjustment.
    is_locked = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=("item", "warehouse_id"), name="inv_item_wh_idx"),
            models.Index(fields=("lot",), name="inv_lot_idx"),
            GinIndex(fields=["quantity"], name="invstack_quantity_gin_idx"),
        ]

    def __str__(self):  # pragma: no cover
        qty = getattr(self, "quantity", {})
        return f"Stack#{self.pk}:{getattr(self.item, 'pk', '?')}:{qty}"

    # ---- Helpers ---------------------------------------------------------
    def remaining_qty(self) -> Decimal | float:
        q = getattr(self, 'quantity', {}) or {}
        received = Decimal(str(q.get('received', 0) or 0))
        issued = Decimal(str(q.get('issued', 0) or 0))
        scrapped = Decimal(str(q.get('scrapped', 0) or 0))
        return received - issued - scrapped

    def mark_issue(self, qty: Decimal | float):
        q = getattr(self, 'quantity', {}) or {}
        issued = Decimal(str(q.get('issued', 0) or 0)) + Decimal(str(qty))
        q['issued'] = float(issued)
        setattr(self, 'quantity', q)

    def apply_scrap(self, qty: Decimal | float, scrap_cost_per_unit: float | None = None):
        q = getattr(self, 'quantity', {}) or {}
        scrapped = Decimal(str(q.get('scrapped', 0) or 0)) + Decimal(str(qty))
        q['scrapped'] = float(scrapped)
        setattr(self, 'quantity', q)
        if scrap_cost_per_unit is not None:
            c = getattr(self, 'cost', {}) or default_cost()
            # accumulate scrap cost (per unit basis * qty scrapped)
            c['scrap_cost'] = float(c.get('scrap_cost', 0) + (float(scrap_cost_per_unit) * float(qty)))
            setattr(self, 'cost', c)

    def update_cost_after_receipt(self, unit_po: float, freight: float = 0.0, duty: float = 0.0, handling: float = 0.0, vat: float = 0.0, prior_moving_avg: float | None = None, trend_baseline: float | None = None):
        """Update cost JSON when this stack (layer) is created or adjusted.

        prior_moving_avg: moving average BEFORE applying this layer (if provided)
        trend_baseline: explicit baseline to compute trend_pct; defaults to prior_moving_avg
        """
        c = getattr(self, 'cost', {}) or default_cost()
        c.setdefault('currency', 'USD')
        c['unit_po'] = float(unit_po)
        c['freight'] = float(freight)
        c['duty'] = float(duty)
        c['handling'] = float(handling)
        c['vat'] = float(vat)
        c['landed'] = float(unit_po + freight + duty + handling + vat)
        # Snapshots remain if already set; set if zero
        if not c.get('fifo_snapshot'): c['fifo_snapshot'] = c['landed']
        if not c.get('lifo_snapshot'): c['lifo_snapshot'] = c['landed']
        if prior_moving_avg is not None:
            # naive moving avg placeholder; caller can override with precise weighted logic
            c['moving_avg'] = float(prior_moving_avg)  # caller responsibility to compute combined
        else:
            c.setdefault('moving_avg', c['landed'])
        base = trend_baseline if trend_baseline is not None else prior_moving_avg
        if base and base != 0:
            c['trend_pct'] = ((c['landed'] - float(base)) / float(base)) * 100.0
        else:
            c.setdefault('trend_pct', 0.0)
        setattr(self, 'cost', c)

    def issue_or_enqueue(self, qty: Decimal | float, reason: str = "issue", request_ref: dict | None = None):
        """Attempt to issue qty from this stack.

        If stack locked, create PendingInventoryAdjustment record and return (False, pending_obj).
        If not locked and sufficient remaining, apply immediately and return (True, self).
        NOTE: Does not persist self automatically when issuing; caller should save.
        """
        from .inventory_layer import PendingInventoryAdjustment  # local import to avoid circular in evaluation
        from django.utils import timezone
        from django.db.models import Sum
        # Treat active reservations (pending & unexpired) as reducing immediately issuable quantity.
        # We allow issuing only if (remaining_qty - active_reserved) >= qty so reserved holds are protected.
        if self.is_locked:
            pending = PendingInventoryAdjustment.objects.create(
                inventorylayer_id=self,
                qty=Decimal(str(qty)),
                state=PendingInventoryAdjustment.STATE_PENDING,
                reason=reason,
                request_ref=request_ref or {},
            )
            return False, pending
        remaining = Decimal(str(self.remaining_qty()))
        request_qty = Decimal(str(qty))
        if remaining < request_qty:
            pending = PendingInventoryAdjustment.objects.create(
                inventorylayer_id=self,
                qty=request_qty,
                state=PendingInventoryAdjustment.STATE_PENDING,
                reason="insufficient_issue",
                request_ref=request_ref or {"original_reason": reason},
            )
            return False, pending
        # Compute active reserved
        try:
            from apps.products.models.inventory_reservation import InventoryReservation
            now = timezone.now()
            active_reserved = (InventoryReservation.objects
                                .filter(inventorylayer_id=self, state='pending', expires_at__gt=now)
                                .aggregate(total=Sum('qty'))['total'] or Decimal('0'))
            active_reserved = Decimal(str(active_reserved))
        except Exception:
            # Fail open (if model not migrated yet) – treat as zero to avoid hard failure
            active_reserved = Decimal('0')
        available_for_issue = remaining - active_reserved
        if request_qty > available_for_issue:
            # Would infringe reserved holds; enqueue with reserved_conflict reason
            pending = PendingInventoryAdjustment.objects.create(
                inventorylayer_id=self,
                qty=request_qty,
                state=PendingInventoryAdjustment.STATE_PENDING,
                reason="reserved_conflict",
                request_ref=request_ref or {"original_reason": reason, "active_reserved": float(active_reserved)},
            )
            return False, pending
        self.mark_issue(qty)
        return True, self


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
    warehouse_id = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventory_movements")
    inventorylayer_id = models.ForeignKey(
        InventoryLayer, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements"
    )
    site_code = models.CharField(max_length=40, db_index=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    reason = models.CharField(max_length=120, blank=True)
    source_doc_type = models.CharField(max_length=40, blank=True)
    source_doc_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=("movement_type",), name="invmove_type_idx"),
            models.Index(fields=("item", "warehouse_id"), name="invmove_item_wh_idx"),
        ]


class PendingInventoryAdjustment(models.Model):
    """Deferred inventory mutation when target stack is locked or insufficient.

    Processing strategy (future service): a periodic job or unlock hook attempts
    to apply PENDING rows in FIFO order. If successful, state -> APPLIED and dt_applied set.
    If permanently invalid (e.g., stack depleted), state -> CANCELED with a reason.
    """
    STATE_PENDING = "pending"
    STATE_APPLIED = "applied"
    STATE_CANCELED = "canceled"
    STATE_CHOICES = [
        (STATE_PENDING, "Pending"),
        (STATE_APPLIED, "Applied"),
        (STATE_CANCELED, "Canceled"),
    ]
    inventorylayer_id = models.ForeignKey(InventoryLayer, on_delete=models.CASCADE, related_name="pending_adjustments")
    qty = models.DecimalField(max_digits=14, decimal_places=4)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default=STATE_PENDING, db_index=True)
    reason = models.CharField(max_length=80, blank=True)
    request_ref = models.JSONField(default=dict, blank=True)
    dt_created = models.DateTimeField(auto_now_add=True)
    dt_applied = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=120, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("state",), name="pendinv_state_idx"),
            models.Index(fields=("inventorylayer_id", "state"), name="pendinv_stack_state_idx"),
        ]

    def apply_now(self):  # stub logic
        if self.state != self.STATE_PENDING:
            return False
        stack = self.inventorylayer_id
        if stack.remaining_qty() < self.qty and not stack.is_locked:
            # insufficient still
            return False
        if stack.is_locked:
            return False
        stack.mark_issue(self.qty)
        stack.save(update_fields=["quantity", "dt_modified", "version"])
        from django.utils import timezone
        self.state = self.STATE_APPLIED
        self.dt_applied = timezone.now()
        self.save(update_fields=["state", "dt_applied"])
        return True

    def cancel(self, reason: str):
        if self.state != self.STATE_PENDING:
            return False
        self.state = self.STATE_CANCELED
        self.cancel_reason = reason[:120]
        self.save(update_fields=["state", "cancel_reason"])
        return True
