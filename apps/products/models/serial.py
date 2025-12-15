from __future__ import annotations

from django.db import models
from common.models import BaseModel
from .item_base_model import ItemLinkedBase
from .warehouse import Warehouse


class Serial(ItemLinkedBase):
    """One serialized unit of an item."""
    # We may not control serial number uniqueness. use internal id as PK.
    serial_ida = models.CharField(max_length=120, unique=False)
    model_ida = models.CharField(max_length=120, blank=True, db_index=True)
    warranty = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=40, blank=True, db_index=True)
    # Current location / warehouse / inventory stack
    site = models.JSONField(default=dict, blank=True, help_text="Lightweight site/location snapshot (geo codes, address refs)")
    inventorylayer_id = models.ForeignKey('products.InventoryLayer', on_delete=models.SET_NULL, null=True, blank=True, related_name="serials")
    data = models.JSONField(default=dict, blank=True)
    qr_code = models.CharField(max_length=255, blank=True, db_index=True)
    # Access the parent item's primary key via `serial.item_id_id` (Django auto FK _id attribute).
    # ItemLinkedBase already defines an index on `item`; no need to duplicate here.


class SerialLog(BaseModel):
    """Log of actions / state changes for a serialized unit."""

    serial_id = models.ForeignKey(Serial, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=60, db_index=True)
    dt = models.BigIntegerField(db_index=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("serial_id", "dt"), name="seriallog_serial_dt_idx"),
        ]


# CREATE TABLE IF NOT EXISTS "serials" (
#     “item_id” BIGSERIAL PRIMARY KEY,
#     “item_uuid” UUID UNIQUE NOT NULL,
#     "claim_count" INTEGER,
#     "claim_price" DOUBLE PRECISION,
#     "comments" TEXT,
#     "cost" DOUBLE PRECISION,
#     "cost_claims" DOUBLE PRECISION,
#     "days_on_plan" INTEGER,
#     "description" VARCHAR(255),
#     "discount" DOUBLE PRECISION,
#     "is_floor_plan" BOOLEAN DEFAULT FALSE,
#     "model" VARCHAR(255),
#     "plan_line" INTEGER,
#     "price" DOUBLE PRECISION,
#     "reciept_retail" VARCHAR(255),
#     "references" JSONB,
#     "serial" VARCHAR(255),
#     "status" VARCHAR(255),
#     "value" DOUBLE PRECISION,
#     "warranty_days" INTEGER
# );
