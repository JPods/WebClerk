from __future__ import annotations

"""Inventory check (cycle / spot count) domain models.

Purpose
=======
`InventoryCheck` and `InventoryCheckLine` capture a *point-in-time* physical (or
system-assisted) verification of on‑hand quantities for a set of org items at a
customer (or internal) organization. Unlike a `DeliveryVisit` (see `flow.py`),
an inventory check is **diagnostic** / **audit oriented** rather than a routed
logistic execution event.

Relationship to Flow (Delivery) Models
--------------------------------------
* DeliveryVisit answers: "What operational movement is occurring right now?"
* InventoryCheck answers: "What does reality say we *actually* have right now?"
An implementation may schedule both for the same physical stop: the visit drives
movement; the inventory check validates stock accuracy pre/post movement.

Granularity
-----------
The parent `InventoryCheck` stores metadata, actor, timing and status. Each
`InventoryCheckLine` stores a counted quantity for a specific `OrgItem`. Variance
is derived (counted - prior) and persisted for downstream reporting, exception
flagging, or reconciliation workflows.

Extensibility Notes
-------------------
The `data` JSON fields (on both parent and line) act as flexible envelopes for
device fingerprints, method hints (rfid, barcode, manual), geo anchors, or
confidence scores without requiring frequent schema migrations. Keep payloads
compact and avoid PII.

Status Lifecycle (InventoryCheck)
---------------------------------
planned -> in_progress -> completed (or canceled)

Typical Transitions:
1. Create (planned)
2. User/device begins scan (in_progress)
3. All lines counted + review (completed) OR aborted (canceled)

Concurrency / Integrity
-----------------------
Multiple overlapping checks for the same org are allowed by design (e.g., zone
based counting) but downstream reconciliation logic should treat overlapping
in_progress windows carefully if performing automatic adjustments.

Future Ideas
------------
* Introduce a `scope` JSON (zones / categories) for partial cycle counts.
* Add a summarization service to compute aggregate variance stats on completion.
* Link to an `InventoryAdjustmentBatch` record if automatic corrections are
    applied from variances.
"""

from django.db import models
from django.conf import settings
from common.models import BaseModel
from apps.products.choices import INVENTORY_CHECK_STATUS_CHOICES


class InventoryCheck(BaseModel):
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return self.notes

    """Top-level inventory audit event.

    Key Fields:
        orgbase_id: Organization whose inventory is being verified.
        catalog_id: Optional scoping object restricting which org items are *expected*.
        user_id: User (or system user) responsible for the check finalization.
        dt_performed: Epoch ms timestamp representing when the *count snapshot* was
            effectively captured (freeze point). For multi-hour counts consider
            storing a range inside `data` (e.g. {"window": {"start":..., "end":...}}).

    Status Semantics:
        planned      - created / scheduled; lines may be seeded or empty.
        in_progress  - active counting / scanning.
        completed    - frozen; lines should no longer mutate (except metadata).
        canceled     - abandoned; lines retained for audit but ignored in KPIs.

    Validation / Business Rules (enforced externally today):
        * Only transition to completed if every intended line has a counted_qty
            (or explicit skip marker in data envelope).
        * Post-completion mutations should be restricted; consider future
            enforcement in `save()` or a state transition service layer.
    """

    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"
    STATUSES = INVENTORY_CHECK_STATUS_CHOICES

    orgbase_id = models.ForeignKey('orgs.OrgBase', on_delete=models.CASCADE, related_name='inventory_checks')
    catalog_id = models.ForeignKey('products.Catalog', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_checks')
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_checks')
    dt_performed = models.BigIntegerField(help_text="Epoch ms when the primary count occurred / was finalized")
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PLANNED, db_index=True)
    notes = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True, help_text="Optional metadata envelope (device info, geo, method, etc.)")

    class Meta:
        indexes = [
            models.Index(fields=("orgbase_id", "dt_performed"), name="invchk_org_dt_idx"),
            models.Index(fields=("catalog_id", "dt_performed"), name="invchk_cat_dt_idx"),
            models.Index(fields=("status",), name="invchk_status_idx"),
        ]


class InventoryCheckLine(BaseModel):

    item_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="String identifier for this inventory check line")
    description = models.CharField(max_length=255, blank=True, help_text="Description for this inventory check line")

    @property
    def ida(self):
        return str(self.pk)

    @property
    def item_ida_value(self):
        return self.item_ida or str(self.pk)

    @property
    def description_value(self):
        return self.description or str(self.orgitem_id) if hasattr(self, 'orgitem_id') else ""

    """Per-item counted quantity within an InventoryCheck.

    Fields:
        counted_qty: Quantity observed / measured during the check.
        prior_qty: Prior system-known quantity (snapshot at start) for variance
            comparison. Optional to allow late attachment if system state is
            resolved asynchronously.
        variance_qty: Derived convenience field = counted - prior (when both
            present). Not recalculated if either source becomes null after save.
        auto_flag: Set by upstream heuristic (e.g., large variance threshold) to
            route into exception workflows.

    Derivation Logic:
        On save, if both counted_qty and prior_qty are provided, variance_qty is
        recomputed. This is intentionally simple; multi-save race conditions are
        acceptable because each save recomputes deterministically.

    Potential Enhancements:
        * Add normalization (e.g., disallow negative counted_qty) with explicit
          validation errors.
        * Track capture provenance (device_id, method) in `data`.
        * Support multi-count lines (store array of attempts and a resolved value).
    """

    inventorycheck_id = models.ForeignKey(InventoryCheck, on_delete=models.CASCADE, related_name='lines')
    orgitem_id = models.ForeignKey('products.OrgItem', on_delete=models.CASCADE, related_name='inventory_check_lines')
    counted_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    prior_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text="Optional previously known quantity for variance calc")
    variance_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text="counted - prior if both available")
    auto_flag = models.BooleanField(default=False, help_text="Flagged automatically (below min / above max / anomaly)")
    data = models.JSONField(default=dict, blank=True, help_text="Aux attributes: source_type, adjustments, raw capture details")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("inventorycheck_id", "orgitem_id"), name="uniq_invchk_orgitem"),
        ]
        indexes = [
            models.Index(fields=("auto_flag",), name="invchkline_autoflag_idx"),
        ]

    def save(self, *args, **kwargs):  # pragma: no cover simple arithmetic
        if self.counted_qty is not None and self.prior_qty is not None:
            self.variance_qty = self.counted_qty - self.prior_qty
        super().save(*args, **kwargs)
