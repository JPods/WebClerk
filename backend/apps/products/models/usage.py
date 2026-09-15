from __future__ import annotations

from typing import Dict, Any
from django.db import models
from django.utils import timezone
from .item_base_model import ItemLinkedBase


# Direct dotted metric keys (no legacy mapping upgrade retained).
METRIC_DEFAULTS: Dict[str, Any] = {
    "turns.actual": 0,
    "turns.average": 0,
    "turns.target": 0,
    "adjustment.quantity": 0,
    "adjustment.value": 0,
    "bill_of_material.quantity.actual": 0,
    "capacity.value": 0,
    "cost.actual": 0,
    "cost.plan": 0,
    "count.invoices": 0,
    "count.sos": 0,
    "inventory.actual": 0,
    "inventory.eom_count": 0,
    "inventory.plan": 0,
    "lead.time": 0,
    "margin.factor": 0,
    "order.quantity.actual": 0,
    "order.quantity.plan": 0,
    "order.value.actual": 0,
    "order.value.plan": 0,
    "purchase.quantity": 0,
    "purchase.value": 0,
    "sales.actual": 0,
    "sales.plan": 0,
    "sales.quantity.actual": 0,
    "sales.quantity.plan": 0,
    "scrap.actual": 0,
    "scrap.plan": 0,
}


def default_metrics() -> Dict[str, Any]:
    """Factory for metrics JSON envelope using dotted keys."""
    base: Dict[str, Any] = dict(METRIC_DEFAULTS)
    base["meta"] = {"description": "", "purpose": "", "type": ""}
    base["dt_updated"] = 0
    base["version"] = 1
    base["schema_version"] = 1
    return base


class ItemUsage(ItemLinkedBase):

    item_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="String identifier for this usage record")
    description = models.CharField(max_length=255, blank=True, help_text="Description for this usage record")

    @property
    def ida(self):
        return str(self.pk)

    @property
    def item_ida_value(self):
        return self.item_ida or str(self.pk)

    @property
    def description_value(self):
        return self.description or self.metrics.get('meta', {}).get('description', "")

    """Monthly usage / planning / performance metrics snapshot.

    Simplified: all numeric facts & plan values live in `metrics` JSON.
    Removed legacy `qty_*` columns; helpers now operate solely on JSON metrics keys.
    """

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    metrics = models.JSONField(default=default_metrics, blank=True, help_text="Aggregated usage & planning metrics")

    # ----------------- Helpers -----------------
    def _ensure_metrics(self):  # pragma: no cover trivial
        if not isinstance(self.metrics, dict):
            self.metrics = default_metrics()
        # ensure all numeric keys exist
        for k, v in METRIC_DEFAULTS.items():
            self.metrics.setdefault(k, v)
        if "meta" not in self.metrics:
            self.metrics["meta"] = {"description": "", "purpose": "", "type": ""}
        if "dt_updated" not in self.metrics:
            self.metrics["dt_updated"] = 0
        if "version" not in self.metrics:
            self.metrics["version"] = 1
        if "schema_version" not in self.metrics:
            self.metrics["schema_version"] = 1
        return self.metrics

    def bump(self, key: str, amount):  # pragma: no cover lightweight
        """Increment a numeric metric by amount (creates key if new)."""
        self._ensure_metrics()
        try:
            cur = self.metrics.get(key, 0) or 0
            self.metrics[key] = float(cur) + float(amount)
        except Exception:
            pass
        return self

    def set_metric(self, key: str, value):  # pragma: no cover lightweight
        self._ensure_metrics()
        self.metrics[key] = value
        return self

    def get_metric(self, key: str, default=0):  # pragma: no cover lightweight
        self._ensure_metrics()
        return self.metrics.get(key, default)

    # Domain flavored helpers
    def record_sale(self, quantity, value=None):  # pragma: no cover lightweight
        self.bump("sales.quantity.actual", quantity)
        if value is not None:
            self.bump("sales.actual", value)
        return self

    def record_purchase(self, quantity, value=None):  # pragma: no cover lightweight
        self.bump("purchase.quantity", quantity)
        if value is not None:
            self.bump("purchase.value", value)
        return self

    def record_return(self, quantity):  # pragma: no cover lightweight
        self.bump("sales.quantity.actual", -abs(quantity))  # treat returns as negative sales qty
        return self

    def recompute_turns(self):  # pragma: no cover lightweight
        self._ensure_metrics()
        inv = float(self.metrics.get("inventory.plan") or 0) or float(self.metrics.get("inventory.actual") or 0)
        sales = float(self.metrics.get("sales.actual") or 0)
        if inv > 0:
            self.metrics["turns.actual"] = sales / inv
        return self

    def touch_metrics(self):  # pragma: no cover lightweight
        self._ensure_metrics()
        self.metrics["dt_updated"] = int(timezone.now().timestamp() * 1000)
        return self

    def save(self, *args, **kwargs):  # pragma: no cover simplified
        self._ensure_metrics()
        self.touch_metrics()
        return super().save(*args, **kwargs)

    def clean(self):  # pragma: no cover lightweight validation
        errors = {}
        if not (1 <= self.month <= 12):
            errors["month"] = "month must be 1-12"
        if not (2000 <= self.year <= 2100):
            errors["year"] = "year out of allowed range (2000-2100)"
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)
        return super().clean()

    @property
    def period_key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def as_flat_dict(self) -> Dict[str, Any]:  # pragma: no cover lightweight
        self._ensure_metrics()
        flat = {f"metric.{k}": v for k, v in self.metrics.items() if k not in {"meta", "dt_updated"}}
        if isinstance(self.metrics.get("meta"), dict):
            for mk, mv in self.metrics["meta"].items():
                flat[f"meta.{mk}"] = mv
        flat.update({
            "item_id": getattr(getattr(self, "item", None), "id", None),
            "year": self.year,
            "month": self.month,
            "period": self.period_key,
            "metrics.dt_updated": self.metrics.get("dt_updated", 0),
            "metrics.version": self.metrics.get("version", 1),
        })
        return flat

    def __str__(self):
        return f"Usage {self.id} ({self.period_key})"

    class Meta:
        indexes = [
            models.Index(fields=("year", "month"), name="usage_year_month_idx"),
        ]

# CREATE TABLE IF NOT EXISTS "usages" (
#     "item_id" BIGSERIAL,
#     "actual_turns" DOUBLE PRECISION,
#     "adjustment_quantity" DOUBLE PRECISION,
#     "adjustment_value" DOUBLE PRECISION,
#     "average_turn" DOUBLE PRECISION,
#     "bom_quantity_actual" DOUBLE PRECISION,
#     "capacity" DOUBLE PRECISION,
#     "cost_actual" DOUBLE PRECISION,
#     "cost_plan" DOUBLE PRECISION,
#     "count_invoices" INTEGER,
#     "count_sos" INTEGER,
#     "description" VARCHAR(255),
#     "inventory_actual" DOUBLE PRECISION,
#     "inventory_eom_count" DOUBLE PRECISION,
#     "inventory_plan" DOUBLE PRECISION,
#     "lead_time" DOUBLE PRECISION,
#     "margin_factor" DOUBLE PRECISION,
#     "order_quantity_actual" DOUBLE PRECISION,
#     "order_quantity_plan" DOUBLE PRECISION,
#     "order_value_actual" DOUBLE PRECISION,
#     "order_value_plan" DOUBLE PRECISION,
#     "purchase_quantity" DOUBLE PRECISION,
#     "purchase_value" DOUBLE PRECISION,
#     "purpose" VARCHAR(255),
#     "sales_actual" DOUBLE PRECISION,
#     "sales_plan" DOUBLE PRECISION,
#     "sales_quantity_actual" DOUBLE PRECISION,
#     "sales_quantity_plan" DOUBLE PRECISION,
#     "scrap_actual" DOUBLE PRECISION,
#     "scrap_plan" DOUBLE PRECISION,
#     "target_turns" DOUBLE PRECISION,
#     "type" VARCHAR(255)