from __future__ import annotations

from django.db import models
from common.models import BaseModel


class Warehouse(BaseModel):
    """Inventory storage location (physical or logical)."""

    name = models.CharField(max_length=160)
    location = models.JSONField(default=dict, blank=True, help_text="Physical address or location details for this warehouse")
    # to include aisle and shelf locations, barcodes, qr codes, and other relevant identifiers
    counted_by = models.JSONField(default=dict, blank=True, help_text="User or system that performed the last inventory count")
    priority = models.CharField(max_length=40, default="normal", help_text="Priority level for this warehouse")
    code = models.CharField(max_length=40, unique=True)
    site_code = models.CharField(max_length=40, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    # in .refs keep tack of the related inventory stacks, vendors, etc.
    class Meta:
        indexes = [
            models.Index(fields=("site_code", "is_active"), name="wh_site_active_idx"),
        ]

    def __str__(self):  # pragma: no cover
        return self.code


# CREATE TABLE IF NOT EXISTS "item_warehouses" (
#     	"address_id" INTEGER,
# "aisle" VARCHAR(255),
#     "barcode" VARCHAR(255),
#     "bin" VARCHAR(255),
#     "column" VARCHAR(255),
#     "counted_by" VARCHAR(255),
#     "description" VARCHAR(255),
 
#     "priority" INTEGER,
#     "quantity_last_count" DOUBLE PRECISION,
#     "quantity_on_hand" DOUBLE PRECISION,
#     "received_by" VARCHAR(255),
#     "references" JSONB,
#     "shelf" VARCHAR(255),
#     "vendor_packing_list" VARCHAR(255),
#     "vendor_po" VARCHAR(255),
#     "warehouse" VARCHAR(255)
# );
