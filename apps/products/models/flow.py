from __future__ import annotations

"""Flow (delivery & field execution) domain models.

Why the name "flow"?
    We group operational, in-the-field execution objects (delivery visits, the
    lines within them, future potential extensions like pickups / returns /
    merchandising actions) under a neutral, *marketing-friendly* banner. These
    represent directional movement of product and related observational data
    (quantities, confirmations, adjustments) between a vendor org and a
    customer org.

Conceptual distinctions:
    * DeliveryVisit vs InventoryCheck: a DeliveryVisit is a routed / scheduled
      operational stop (with optional fulfillment activity). An InventoryCheck
      is a focused quantitative audit event. A visit might embed a lightweight
      spot verification but its primary purpose is executing a logistic flow.
    * DeliveryLine captures the intent + outcome for a single org_item on that
      stop (planned, loaded, delivered, skipped, partial) and carries flexible
      JSON for device / pricing / adjustment metadata.

Data / migration note:
    This file was renamed from delivery.py to flow.py. We intentionally kept the
    model class names (DeliveryVisit, DeliveryLine) unchanged to avoid a noisy
    RenameModel migration and preserve existing table names & constraints. If a
    true rename becomes desirable later (e.g., FlowVisit), create an explicit
    migration with Django's RenameModel plus any index / constraint renames.

Forward-looking:
    Additional flow-scoped activity types (returns, reverse logistics, pickup
    consolidations) can co-locate here or in sibling modules (e.g. returns.py)
    while sharing higher-level orchestration / status semantics.
"""

from django.db import models

from common.models import BaseModel
from apps.products.choices import (
    DELIVERY_LINE_STATUS_CHOICES,
    DELIVERY_VISIT_STATUS_CHOICES,
)


class DeliveryVisit(BaseModel):
    """A routed stop (planned -> en_route -> arrived -> closed/canceled) between vendor & customer.

    Purpose:
        Represents an operational window where product may be delivered, counts
        confirmed, exceptions noted, or ancillary actions (device scans, photo
        capture) performed.

    Status lifecycle (typical):
        planned -> en_route -> arrived -> (closed | canceled)
        ("arrived" is optional if system auto-closes upon completion.)

    Catalog linkage:
        If provided, constrains or contextualizes permissible org items &
        pricing snapshots. Validation enforces catalog org alignment.

    Migration rationale:
        Class name retained after module rename to avoid implicit table rename.
    """

    STATUS_PLANNED = "planned"
    STATUS_EN_ROUTE = "en_route"
    STATUS_ARRIVED = "arrived"
    STATUS_CLOSED = "closed"
    STATUS_CANCELED = "canceled"
    STATUSES = DELIVERY_VISIT_STATUS_CHOICES

    orgbase_id = models.ForeignKey('orgs.OrgBase', on_delete=models.CASCADE, related_name='delivery_visits_as_vendor')
    customer_orgbase_id = models.ForeignKey('orgs.OrgBase', on_delete=models.CASCADE, related_name='delivery_visits_as_customer')
    catalog_id = models.ForeignKey('products.Catalog', on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_visits')
    dt_scheduled = models.BigIntegerField(help_text="Epoch ms scheduled time window start")
    dt_arrived = models.BigIntegerField(null=True, blank=True)
    dt_completed = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUSES, default=STATUS_PLANNED, db_index=True)
    notes = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True, help_text="Flexible metadata: route info, geo, truck id, etc.")

    class Meta:
        indexes = [
            models.Index(fields=("orgbase_id", "dt_scheduled"), name="delv_vendor_sched_idx"),
            models.Index(fields=("customer_orgbase_id", "dt_scheduled"), name="delv_customer_sched_idx"),
            models.Index(fields=("status",), name="delv_status_idx"),
        ]

    def clean(self):  # pragma: no cover simple validation
        from django.core.exceptions import ValidationError
        catalog_id = getattr(self, "catalog_id_id", None)
        if catalog_id:
            catalog = getattr(self, "catalog_id")
            vendor_org_id = getattr(catalog, "vendor_org_id_id", None)
            customer_org_id = getattr(catalog, "customer_org_id_id", None)
            if vendor_org_id and vendor_org_id != getattr(self, "orgbase_id_id", None):  # type: ignore[attr-defined]
                raise ValidationError("catalog.vendor_org mismatch with visit.vendor_org")
            if customer_org_id and customer_org_id != getattr(self, "customer_orgbase_id_id", None):  # type: ignore[attr-defined]
                raise ValidationError("catalog.customer_org mismatch with visit.customer_org")
        return super().clean()


class DeliveryLine(BaseModel):
    """Intent + execution record for a single org item on a DeliveryVisit.

    Quantity semantics:
        * planned_qty  - expectation (route planning / allocation)
        * loaded_qty   - what was physically loaded prior to departure
        * delivered_qty- actual confirmed transfer to customer location
        Variance / exceptions (skipped / partial) are expressed via status and
        optional data payload (e.g., device captures, signatures, photos).

    Skipping vs Partial:
        skipped  -> zero delivered; reason captured in skipped_reason.
        partial  -> delivered_qty < planned_qty but > 0.

    Metadata (data JSON):
        Space for ephemeral or structured snapshots (pricing, lot/serials,
        geo positions, capture device identifiers) without schema churn.
    """

    STATUS_PLANNED = "planned"
    STATUS_LOADED = "loaded"
    STATUS_DELIVERED = "delivered"
    STATUS_SKIPPED = "skipped"
    STATUS_PARTIAL = "partial"
    STATUSES = DELIVERY_LINE_STATUS_CHOICES

    deliveryvisit_id = models.ForeignKey(DeliveryVisit, on_delete=models.CASCADE, related_name='lines')
    orgitem_id = models.ForeignKey('products.OrgItem', on_delete=models.CASCADE, related_name='delivery_lines')
    planned_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    loaded_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    delivered_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    skipped_reason = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=STATUSES, default=STATUS_PLANNED, db_index=True)
    data = models.JSONField(default=dict, blank=True, help_text="Aux data: pricing snapshot, adjustments, device capture")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("deliveryvisit_id", "orgitem_id"), name="uniq_delivery_visit_orgitem"),
        ]
        indexes = [
            models.Index(fields=("status",), name="delvline_status_idx"),
        ]