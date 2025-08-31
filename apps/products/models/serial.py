from __future__ import annotations

from django.db import models
from common.models import BaseModel
from .item_base_model import ItemLinkedBase
from .warehouse import Warehouse


class Serial(ItemLinkedBase):
    """One serialized unit of an item."""

    serial_number = models.CharField(max_length=120, unique=True)
    status = models.CharField(max_length=40, blank=True, db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name="serials")
    inventory_stack = models.ForeignKey('products.InventoryStack', on_delete=models.SET_NULL, null=True, blank=True, related_name="serials")

    class Meta:
        indexes = [
            models.Index(fields=("item",), name="serial_item_idx"),
        ]


class SerialLog(BaseModel):
    """Log of actions / state changes for a serialized unit."""

    serial = models.ForeignKey(Serial, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=60, db_index=True)
    dt = models.BigIntegerField(db_index=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("serial", "dt"), name="seriallog_serial_dt_idx"),
        ]
