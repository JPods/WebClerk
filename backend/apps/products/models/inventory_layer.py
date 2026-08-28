from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from apps.products.choices import (
    INVENTORY_MOVEMENT_TYPE_CHOICES,
)
from common.models import CoreModel
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
                     PLACEHOLDER: stored on receipt but no conversion logic yet.
                     All valuation assumes base currency (USD). Multi-currency
                     conversion is a Phase 5 feature — do not build on this field
                     until conversion service exists.

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
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return self.lot

    """Received quantity at a specific unit cost (lot/stack)."""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventory_layers", db_column='warehouse_id')
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
    dt_locked = models.DateTimeField(null=True, blank=True, help_text="When the lock was acquired. Auto-expires after 5 minutes.")

    class Meta:
        indexes = [
            models.Index(fields=("item", "warehouse"), name="inv_item_wh_idx"),
            models.Index(fields=("lot",), name="inv_lot_idx"),
            GinIndex(fields=["quantity"], name="invstack_quantity_gin_idx"),
        ]

    def __str__(self):  # pragma: no cover
        qty = getattr(self, "quantity", {})
        return f"Stack#{self.pk}:{getattr(self.item, 'pk', '?')}:{qty}"

    LOCK_TIMEOUT_SECONDS = 300  # 5 minutes

    def check_lock_expired(self) -> bool:
        """If lock has expired, release it (which drains pending queue). Otherwise return False."""
        if not self.is_locked or not self.dt_locked:
            return False
        from django.utils import timezone
        import datetime
        if timezone.now() - self.dt_locked > datetime.timedelta(seconds=self.LOCK_TIMEOUT_SECONDS):
            self.release_lock()
            return True
        return False

    def acquire_lock(self):
        from django.utils import timezone
        self.is_locked = True
        self.dt_locked = timezone.now()
        self.save(update_fields=['is_locked', 'dt_locked', 'dt_modified', 'version'])

    def release_lock(self):
        """Clear the lock and drain any pending adjustments queued while locked."""
        self.is_locked = False
        self.dt_locked = None
        self.save(update_fields=['is_locked', 'dt_locked', 'dt_modified', 'version'])
        # Drain the pending queue — the whole reason pending exists
        from apps.transactions.services.inventory_pending_process import process_pending_for_item
        process_pending_for_item(item_id=self.item_id)

    # Override LifecycleMixin so admin lock/unlock also honors the pending contract
    def lock(self):
        self.acquire_lock()

    def unlock(self):
        self.release_lock()

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
        """Create a Pending record for this inventory layer issue.

        The Pending.save() automatically calls try_apply() which applies
        immediately if the item is not locked. If locked, celery picks it up.
        Returns (applied: bool, pending_obj).
        """
        from apps.core.models import Pending

        request_qty = Decimal(str(qty))
        item_id = self.item_id

        # Create Pending — try_apply fires automatically in save()
        pending = Pending.objects.create(
            model_name='item',
            record_id=str(item_id),
            purpose='inventory_line_add',
            name=f'Layer issue: {reason}',
            changes={
                'on_hand': float(-request_qty),
                'item_id': item_id,
                'layer_id': self.pk,
                'reason': reason,
                **(request_ref or {}),
            },
        )

        applied = pending.is_processed()
        if applied:
            # Also update the layer's issued quantity
            self.mark_issue(qty)
            self.save(update_fields=['quantity', 'dt_modified', 'version'])

        return applied, pending


class SiteInventory(ItemLinkedBase):
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return self.site_code

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
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return self.reason

    """Immutable movement ledger (optional future use; scaffold only).

    Records inventory-affecting events (receipts, issues, adjustments) for auditing and
    reconstruction of site / stack balances. Not yet integrated with services.
    """

    MOVEMENT_RECEIPT = "receipt"
    MOVEMENT_ISSUE = "issue"
    MOVEMENT_ADJUST = "adjust"
    MOVEMENT_TYPES = INVENTORY_MOVEMENT_TYPE_CHOICES

    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inventory_movements", db_column='warehouse_id')
    inventory_layer = models.ForeignKey(
        InventoryLayer, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements", db_column='inventorylayer_id'
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


