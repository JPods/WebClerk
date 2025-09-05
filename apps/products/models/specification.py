from __future__ import annotations

from django.db import models
from .item_base_model import ItemLinkedBase
from common.stats_mixin import StatsMixin


def default_details():
    """Free-form structured attributes for this specification.

    Suggested keys:
        kind: text|number|bool|enum|range|measure
        value: primary scalar or list
        unit: optional unit string
        enum_options: optional list for enum kinds
        min / max: for range kinds
        source: provenance label
        dt_defined: epoch ms timestamp
    """
    return {"kind": "text", "value": "", "unit": "", "source": "manual", "dt_defined": 0, "schema_version": 1}


def default_docs():
    return {}


def default_applies():
    return {}


class Specification(StatsMixin, ItemLinkedBase):
    """Specification / attribute metadata for an item or item family.

    Simplified structure: all typed value information resides inside `details` JSON. Legacy
    value_text/value_number/value_bool/value_type/slug fields removed.
    """

    name = models.CharField(max_length=120, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    description_long = models.TextField(blank=True)
    unit = models.CharField(max_length=30, blank=True, help_text="Optional canonical unit when numeric")
    details = models.JSONField(default=default_details, blank=True, help_text="Structured value payload (kind, value, unit, etc.)")
    docs = models.JSONField(default=default_docs, blank=True)
    applies_to = models.JSONField(default=default_applies, blank=True)
    # volumen of sales, number of items, 
    # number of returns, margins, margin velocity
    # across all times using based on this specification

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "name"], name="uniq_item_spec_name"),
        ]
        indexes = [
            models.Index(fields=("item", "name"), name="spec_item_name_idx"),
        ]

    def clean(self):  # pragma: no cover
        # Normalize details schema
        if not isinstance(self.details, dict):
            self.details = default_details()
        d = self.details
        d.setdefault("kind", "text")
        d.setdefault("value", "" if d.get("kind") == "text" else None)
        d.setdefault("dt_defined", 0)
        d.setdefault("schema_version", 1)
        if self.unit and d.get("unit") in (None, ""):
            d["unit"] = self.unit

    def save(self, *args, **kwargs):  # pragma: no cover
        self.clean()
        super().save(*args, **kwargs)