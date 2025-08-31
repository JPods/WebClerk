from __future__ import annotations

from django.db import models
from common.models import BaseModel
from .item_base_model import ItemLinkedBase


class Catalog(BaseModel):
    """Collection of items with pricing overrides and discounts."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=60, unique=True)
    currency = models.CharField(max_length=8, default="USD")
    effective_start_dt = models.BigIntegerField()
    effective_end_dt = models.BigIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=("is_active", "effective_start_dt"), name="catalog_active_idx"),
        ]


class CatalogLine(ItemLinkedBase):
    """Item entry in a catalog with specific pricing overrides."""

    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="lines")
    price_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["catalog", "item"], name="uniq_catalog_item"),
        ]
        indexes = [
            models.Index(fields=("catalog",), name="catalogline_catalog_idx"),
        ]
