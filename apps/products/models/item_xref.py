from __future__ import annotations

from django.db import models
from .item_base_model import ItemLinkedBase


class ItemXRef(ItemLinkedBase):
    """External cross reference mapping for supplier/manufacturer identifiers."""

    SOURCE_MANUFACTURER = "manufacturer"
    SOURCE_WHOLESALER = "wholesaler"
    SOURCE_OTHER = "other"
    SOURCE_CHOICES = [
        (SOURCE_MANUFACTURER, "Manufacturer"),
        (SOURCE_WHOLESALER, "Wholesaler"),
        (SOURCE_OTHER, "Other"),
    ]

    # Source system classification (manufacturer, wholesaler, other)
    source = models.CharField(max_length=40, choices=SOURCE_CHOICES, db_index=True)
    # Optional pointer details for external system record (if needed)
    source_id = models.BigIntegerField(blank=True, null=True)
    # Legacy field renamed to source_model_name (historical migration retains old name)
    source_model_name = models.CharField(max_length=40, blank=True)
    source_name = models.CharField(max_length=120, blank=True)
    external_sku = models.CharField(max_length=120, db_index=True)
    external_uuid = models.UUIDField(blank=True, null=True)
    # Structured cost object (e.g. {"value": 12.34, "currency": "USD", "breaks": []})
    cost = models.JSONField(default=dict, blank=True, null=True, help_text="Structured cost data (value, currency, tiers, etc.)")
    is_preferred = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "source", "external_sku"], name="uniq_item_source_sku"),
        ]
        indexes = [
            models.Index(fields=("source", "external_sku"), name="xref_source_sku_idx"),
        ]

    def __str__(self):  # pragma: no cover
        return f"{getattr(self.item, 'pk', '?')}:{self.source}:{self.external_sku}"
