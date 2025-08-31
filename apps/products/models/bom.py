from __future__ import annotations

from decimal import Decimal
from django.db import models
from common.models import BaseModel
from .item import Item


class BillOfMaterial(BaseModel):
    """Single component line for an assembled/bundle item."""

    parent = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="bom_parent")
    component = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="bom_component")
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("1"))
    scrap_factor = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent", "component"], name="uniq_bom_parent_component"),
        ]
        indexes = [
            models.Index(fields=("parent",), name="bom_parent_idx"),
        ]
