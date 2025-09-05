from __future__ import annotations

from django.db import models
from common.models import BaseModel
from .item_base_model import ItemLinkedBase


def default_catalog_metrics():
    """Default metrics structure for a Catalog.

    Keys:
        item_count: Total items linked (lines)
        active_item_count: Subset currently active/eligible
        dt_last_priced: Epoch ms of last pricing change event
        dt_last_sync: Epoch ms of last external sync (if connected)
        plan_value_total: Planned extended value for next delivery window
        actual_value_total: Actual delivered/confirmed value
        variance_value_total: actual - plan value
        fill_rate_pct: Delivered lines / planned lines * 100
        avg_margin_pct: Average margin across active lines (if pricing present)
        usage_rolling_30d: Aggregate usage (units) in trailing 30 days for analytics
        update_accuracy_pct: % of attempted updates accepted by downstream systems
    """
    return {
        "item_count": 0,
        "active_item_count": 0,
        "dt_last_priced": None,
        "dt_last_sync": None,
        "plan_value_total": None,
        "actual_value_total": None,
        "variance_value_total": None,
        "fill_rate_pct": None,
        "avg_margin_pct": None,
        "usage_rolling_30d": None,
        "update_accuracy_pct": None,
    }

CATALOG_METRICS_KEY_INFO = {
    "item_count": "Total catalog lines (denormalized count)",
    "active_item_count": "Count of lines currently valid/active",
    "dt_last_priced": "Last epoch ms a price was changed",
    "dt_last_sync": "Epoch ms of last integration sync",
    "plan_value_total": "Planned extended delivery value for upcoming window",
    "actual_value_total": "Actual delivered extended value",
    "variance_value_total": "Actual - planned value variance",
    "fill_rate_pct": "% of planned lines successfully fulfilled",
    "avg_margin_pct": "Average margin percent across active lines",
    "usage_rolling_30d": "Rolling 30 day usage units (aggregated)",
    "update_accuracy_pct": "Percent of attempted external updates accepted",
}


class Catalog(BaseModel):
    """Collection of items with pricing overrides and discounts."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=60, db_index=True, help_text="Catalog code (unique per vendor_org; may repeat across vendors)")
    currency = models.CharField(max_length=8, default="USD")
    dt_effective_start = models.BigIntegerField()
    dt_effective_end = models.BigIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    vendor_org = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='vendor_catalogs', help_text='Owning / publishing vendor organization (optional)')
    customer_org = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_catalogs', help_text='Target customer organization scope (optional)')
    manufacturer_org = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='manufacturer_catalogs', help_text='Manufacturer associated with this catalog (optional)')
    rep_org = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='rep_catalogs', help_text='Representative / agent organization (optional)')
    employee_org = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_catalogs', help_text='Internal employee / corporate organizational context (optional)')
    connection = models.ForeignKey(
        'sync.Connection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='catalogs',
        help_text='Sync connection managing external catalog integration (optional)'
    )
    metrics = models.JSONField(default=default_catalog_metrics, blank=True, null=True, help_text="Operational & performance metrics (plan vs actual, sync stats, counts)")

    class Meta:
        indexes = [
            models.Index(fields=("is_active", "dt_effective_start"), name="catalog_active_idx"),
            models.Index(fields=("vendor_org",), name="catalog_vendor_idx"),
            models.Index(fields=("customer_org",), name="catalog_customer_idx"),
            models.Index(fields=("manufacturer_org",), name="catalog_manufacturer_idx"),
            models.Index(fields=("rep_org",), name="catalog_rep_idx"),
            models.Index(fields=("employee_org",), name="catalog_employee_idx"),
            models.Index(fields=("connection",), name="catalog_connection_idx"),
        ]
        constraints = [
            # Allow same code across different vendors, but enforce uniqueness per vendor.
            models.UniqueConstraint(fields=("code", "vendor_org"), name="uniq_catalog_code_vendor"),
            # Enforce temporal validity (end >= start when end present)
            models.CheckConstraint(
                check=(models.Q(dt_effective_end__isnull=True) | models.Q(dt_effective_end__gte=models.F("dt_effective_start"))),
                name="ck_catalog_effective_range",
            ),
        ]

    # Backwards compatibility aliases
    @property
    def effective_dt_start(self):  # pragma: no cover
        return self.dt_effective_start

    @effective_dt_start.setter
    def effective_dt_start(self, v):  # pragma: no cover
        self.dt_effective_start = v

    @property
    def effective_dt_end(self):  # pragma: no cover
        return self.dt_effective_end

    @effective_dt_end.setter
    def effective_dt_end(self, v):  # pragma: no cover
        self.dt_effective_end = v


class CatalogLine(ItemLinkedBase):
    """Item entry in a catalog with specific pricing overrides."""

    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="lines")
    price_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    items = models.JSONField(default=dict, blank=True, null=True)
        # list ids prices, attributes, etc. for denormalized lookup
        # if it exceeds a size, put it in an external doc store
    metrics = models.JSONField(default=default_catalog_metrics, blank=True, help_text="Line-level metrics snapshot (plan/actual/value deltas)")
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["catalog", "item"], name="uniq_catalog_item"),
        ]

    # Lightweight metric helpers
    def touch_pricing(self, epoch_ms: int | None = None):  # pragma: no cover simple helper
        if not isinstance(self.metrics, dict):
            self.metrics = default_catalog_metrics()
        if epoch_ms is None:
            import time
            epoch_ms = int(time.time() * 1000)
        self.metrics["dt_last_priced"] = epoch_ms  # type: ignore[index]
        return self.metrics

    def record_sync(self, epoch_ms: int | None = None):  # pragma: no cover simple helper
        if not isinstance(self.metrics, dict):
            self.metrics = default_catalog_metrics()
        if epoch_ms is None:
            import time
            epoch_ms = int(time.time() * 1000)
        self.metrics["dt_last_sync"] = epoch_ms  # type: ignore[index]
        return self.metrics

    def update_plan_actual_value(self, plan: float | None, actual: float | None):  # pragma: no cover
        if not isinstance(self.metrics, dict):
            self.metrics = default_catalog_metrics()
        if plan is not None:
            self.metrics["plan_value_total"] = float(plan)  # type: ignore[index]
        if actual is not None:
            self.metrics["actual_value_total"] = float(actual)  # type: ignore[index]
        if plan is not None and actual is not None:
            self.metrics["variance_value_total"] = float(actual - plan)  # type: ignore[index]
            if plan > 0:
                # fill_rate_pct remains separate; plan vs actual value could inform margin accuracy
                pass
        return self.metrics
        indexes = [
            models.Index(fields=("catalog",), name="catalogline_catalog_idx"),
        ]
