from __future__ import annotations

from django.db import models
from django.utils import timezone
from apps.products.choices import (
    ORG_ITEM_AVAILABILITY_CHOICES,
    ORG_ITEM_INVENTORY_FREQUENCY_CHOICES,
)
from .item_base_model import ItemLinkedBase


def default_org_item_data():
        """Default structured operational data for an OrgItem.

        Keys:
            quantity_minimum: (number | null) Minimum desired stocking / listing threshold
            quantity_maximum: (number | null) Maximum soft cap for planning / alerts
            inventory_frequency: (string | null) Cron-ish or code (e.g. 'weekly', 'daily', '30d')
            dt_next_check: (int | null) Epoch ms for scheduled next verification
            dt_last_check: (int | null) Epoch ms of last verification
            count_last_check: (number | null) Observed on-hand qty at last check
            checked_by_attention: (bool) Flag set if last check required manual review
            checked_by_id: (int | null) User / agent id that performed last check
        """
        return {
                "quantity_minimum": None,
                "quantity_maximum": None,
                "inventory_frequency": None,
                "dt_next_check": None,
                "dt_last_check": None,
                "count_last_check": None,
                "checked_by_attention": False,
                "checked_by_id": None,
        }

def default_org_item_metrics():
    """Default metrics feedback loop for plan vs actual performance.

    Keys:
        plan_last_qty: (number|None) Last planned quantity (e.g. expected delivery qty)
        actual_last_qty: (number|None) Last actual observed quantity / delivery
        variance_last_qty: (number|None) actual - plan if both present
        plan_accuracy_pct: (number|None) (actual/plan)*100 if plan >0
        rolling_daily_usage: (number|None) Derived consumption rate (units/day)
        rolling_days_of_supply: (number|None) Estimated days cover at last count
    """
    return {
        "plan_last_qty": None,
        "actual_last_qty": None,
        "variance_last_qty": None,
        "plan_accuracy_pct": None,
        "rolling_daily_usage": None,
        "rolling_days_of_supply": None,
    }

ORG_ITEM_DATA_ALLOWED_KEYS = set(default_org_item_data().keys())
ORG_ITEM_METRICS_KEY_INFO = {
    "plan_last_qty": "Last planned quantity for a delivery or replenishment action",
    "actual_last_qty": "Last actual delivered or counted quantity",
    "variance_last_qty": "Variance actual - plan for last recorded event",
    "plan_accuracy_pct": "(actual/plan)*100 for last event when plan > 0",
    "rolling_daily_usage": "Smoothed consumption rate (units per day)",
    "rolling_days_of_supply": "Projected days of supply at last observed on-hand",
}


class OrgItem(ItemLinkedBase):
    """Organization ↔ Item assortment / listing association.

    Represents that a given organization (customer, vendor, manufacturer channel, etc.)
    carries or lists the referenced catalog Item. Neutral naming (OrgItem) avoids
    implying inventory ownership ("stocked") while conveying relationship.

    Notes:
      - Inherits `item` FK from ItemLinkedBase.
      - `orgbase_id` provides direction; org_type classification available via related org.
      - `description` can hold planogram, merchandising, pricing notes, etc.
    """

    orgbase = models.ForeignKey('orgs.OrgBase', on_delete=models.CASCADE, related_name="org_items", db_column='orgbase_id')
    catalog = models.ForeignKey('products.Catalog', on_delete=models.SET_NULL, blank=True, null=True, related_name="org_items", db_column='catalog_id', help_text="Optional catalog / channel context scoping this association")
    item_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="String identifier for this org item")
    description = models.CharField(max_length=255, blank=True, help_text="Description for this org item")

    @property
    def ida(self):
        return str(self.pk)

    @property
    def item_ida_value(self):
        return self.item_ida or str(self.pk)

    @property
    def description_value(self):
        return self.description
    # --- Enumerations / standardized codes ---------------------------------
    STATE_ENABLED = "enabled"
    STATE_PAUSED = "paused"
    STATE_RETIRED = "retired"
    AVAILABILITY_STATES = ORG_ITEM_AVAILABILITY_CHOICES

    FREQ_DAILY = "daily"
    FREQ_WEEKLY = "weekly"
    FREQ_MONTHLY = "monthly"
    FREQ_30D = "30d"
    INVENTORY_FREQUENCIES = ORG_ITEM_INVENTORY_FREQUENCY_CHOICES

    availability_state = models.CharField(
        max_length=20,
        choices=AVAILABILITY_STATES,
        blank=True,
        db_index=True,
        help_text="Lifecycle availability state of this OrgItem relationship",
    )
    quantity_minimum = models.DecimalField(max_digits=14, decimal_places=4, blank=True, null=True, help_text="Min threshold (if set) mirrors data.quantity_minimum")
    quantity_maximum = models.DecimalField(max_digits=14, decimal_places=4, blank=True, null=True, help_text="Max threshold (if set) mirrors data.quantity_maximum")
    inventory_frequency = models.CharField(
        max_length=30,
        choices=INVENTORY_FREQUENCIES,
        blank=True,
        help_text="Inventory verification cadence code",
    )
    dt_last_checked = models.BigIntegerField(blank=True, null=True, db_index=True, help_text="Epoch ms of last verification (duplicate of data.dt_last_check for indexable queries)")
    dt_next_check = models.BigIntegerField(blank=True, null=True, db_index=True, help_text="Epoch ms when next inventory verification is due (mirrors data.dt_next_check)")
    data = models.JSONField(
        default=default_org_item_data,
        blank=True,
        null=True,
        help_text="Operational inventory / verification attributes (thresholds, scheduling, last check metadata)",
    )
    metrics = models.JSONField(
        default=default_org_item_metrics,
        blank=True,
        null=True,
        help_text="Aggregated plan vs actual performance metrics (consumption, variance, accuracy)",
    )

    class Meta:
        # Keep existing DB constraint/index names (from original ItemCarried) after RenameModel migration
        constraints = [
            models.UniqueConstraint(fields=["item_id", "orgbase_id", "catalog_id"], name="uniq_item_org_catalog"),
            models.CheckConstraint(check=models.Q(quantity_minimum__gte=0) | models.Q(quantity_minimum__isnull=True), name="ck_orgitem_qty_min_nonneg"),
            models.CheckConstraint(check=models.Q(quantity_maximum__gte=0) | models.Q(quantity_maximum__isnull=True), name="ck_orgitem_qty_max_nonneg"),
            models.CheckConstraint(
                check=(
                    models.Q(quantity_minimum__isnull=True)
                    | models.Q(quantity_maximum__isnull=True)
                    | models.Q(quantity_maximum__gte=models.F("quantity_minimum"))
                ),
                name="ck_orgitem_qty_order",
            ),
        ]
        indexes = [
            models.Index(fields=("orgbase_id", "item_id"), name="carried_org_item_idx"),
            models.Index(fields=("orgbase_id", "availability_state"), name="orgitem_org_state_idx"),
            models.Index(fields=("catalog_id",), name="orgitem_catalog_idx"),
            models.Index(fields=("dt_last_checked",), name="orgitem_lastcheck_idx"),
            models.Index(fields=("dt_next_check",), name="orgitem_nextcheck_idx"),
        ]

    # Custom manager with common query helpers
    class OrgItemQuerySet(models.QuerySet):
        def for_org(self, org):
            return self.filter(orgbase_id=org)

        def due_for_check(self, now_ms: int | None = None):
            if now_ms is None:
                now_ms = int(timezone.now().timestamp() * 1000)
            return self.filter(
                models.Q(dt_next_check__lte=now_ms) &
                models.Q(dt_next_check__isnull=False)
            )

    class OrgItemManager(models.Manager):
        def get_queryset(self):  # type: ignore[override]
            return OrgItem.OrgItemQuerySet(self.model, using=self._db)

        def for_org(self, org):
            return self.get_queryset().for_org(org)

        def due_for_check(self, now_ms: int | None = None):
            return self.get_queryset().due_for_check(now_ms)

    objects = OrgItemManager()

    # Optional lightweight normalization; invoked manually or could be integrated in save hooks
    def normalize_data(self):  # pragma: no cover (simple guard)
        if not isinstance(self.data, dict):
            self.data = default_org_item_data()
            return
        changed = False
        # Remove unknown keys
        for k in list(self.data.keys()):
            if k not in ORG_ITEM_DATA_ALLOWED_KEYS:
                self.data.pop(k, None)
                changed = True
        # Ensure all expected keys exist
        for k, v in default_org_item_data().items():
            if k not in self.data:
                self.data[k] = v
                changed = True
        if changed:
            # Mark dt_modified via BaseModel touch on next save through normal flow
            pass

    def pre_save_hook(self, data):  # pragma: no cover - light validation
        # Sync promoted columns from data if not explicitly set
        if isinstance(self.data, dict):
            self.quantity_minimum = self.data.get("quantity_minimum", self.quantity_minimum)
            self.quantity_maximum = self.data.get("quantity_maximum", self.quantity_maximum)
            self.inventory_frequency = self.data.get("inventory_frequency", self.inventory_frequency)
            self.dt_last_checked = self.data.get("dt_last_check", self.dt_last_checked)
            self.dt_next_check = self.data.get("dt_next_check", self.dt_next_check)
        # Auto compute next check if frequency + dt_last_checked available
        if self.inventory_frequency and self.dt_last_checked:
            # Only recalc if dt_next_check missing or dt_last_checked changed (approx by comparing <= dt_last_checked)
            if not self.dt_next_check or (self.dt_next_check and self.dt_next_check <= self.dt_last_checked):
                freq = self.inventory_frequency
                interval_ms = None
                if freq == self.FREQ_DAILY:
                    interval_ms = 86_400_000
                elif freq == self.FREQ_WEEKLY:
                    interval_ms = 7 * 86_400_000
                elif freq in (self.FREQ_MONTHLY, self.FREQ_30D):
                    interval_ms = 30 * 86_400_000
                if interval_ms:
                    self.dt_next_check = self.dt_last_checked + interval_ms
                    # mirror into data structure
                    if isinstance(self.data, dict):
                        self.data["dt_next_check"] = self.dt_next_check
        # Basic semantic checks (duplicates constraint logic for clearer API errors)
        if (
            self.quantity_minimum is not None
            and self.quantity_minimum < 0
        ):
            return "quantity_minimum must be >= 0"
        if (
            self.quantity_maximum is not None
            and self.quantity_maximum < 0
        ):
            return "quantity_maximum must be >= 0"
        if (
            self.quantity_minimum is not None
            and self.quantity_maximum is not None
            and self.quantity_maximum < self.quantity_minimum
        ):
            return "quantity_maximum must be >= quantity_minimum"
        return None

    # Convenience accessor
    def get_thresholds(self):  # pragma: no cover simple helper
        return {
            "min": self.quantity_minimum,
            "max": self.quantity_maximum,
            "next_check": self.dt_next_check,
            "last_check": self.dt_last_checked,
        }

    # Simple metrics update helper (can be called after external plan vs actual events)
    def update_plan_actual(self, planned: float | None, actual: float | None):  # pragma: no cover utility
        if not isinstance(self.metrics, dict):
            self.metrics = default_org_item_metrics()
        if planned is not None:
            self.metrics["plan_last_qty"] = float(planned)  # type: ignore[index]
        if actual is not None:
            self.metrics["actual_last_qty"] = float(actual)  # type: ignore[index]
        if planned is not None and actual is not None:
            variance = actual - planned
            self.metrics["variance_last_qty"] = variance  # type: ignore[index]
            if planned > 0:
                self.metrics["plan_accuracy_pct"] = (actual / planned) * 100.0  # type: ignore[index]
        # leave rolling metrics to background jobs / later computation
        return self.metrics
