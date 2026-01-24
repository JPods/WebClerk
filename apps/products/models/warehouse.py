from __future__ import annotations

from django.db import models
from django.utils import timezone
from common.models import BaseModel


def default_count():
    """Canonical structure for `Warehouse.count` JSON.

    Keys:
        value (int|float): last counted quantity (>=0)
        aisle / column / shelf / bin (str): location granularity hints
        counted_by (str): human identifier (username or display)
        counted_by_id (int|None): internal user id if available
        dt_counted (int): epoch ms when count captured (UTC)
        deviation (float): optional variance vs system (may be +/-)
    """
    return {
        "value": 0,
        "aisle": "",
        "column": "",
        "shelf": "",
        "bin": "",
        "counted_by": "",
        "counted_by_id": None,
        "dt_counted": 0,
        "deviation": 0,
    }


class Warehouse(BaseModel):
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return self.name

    """Inventory storage location (physical or logical).

    Item relationships: instead of a direct FK or embedding `item_id` in the count JSON,
    associated item ids are tracked in `refs.links.items` (list of ints). This keeps the
    core table slim and leverages the existing JSON envelope for lightweight linkage.
    """
    name = models.CharField(max_length=160)
    location = models.JSONField(default=dict, blank=True, help_text="Physical address or location details for this warehouse")
    # to include aisle and shelf locations, barcodes, qr codes, and other relevant identifiers
    count = models.JSONField(
        default=default_count,
        blank=True,
        help_text=(
            "Inventory count snapshot JSON. Schema: {value, aisle, column, shelf, bin, counted_by, "
            "counted_by_id, dt_counted(ms epoch), deviation}"),
    )
    priority = models.CharField(max_length=40, default="normal", help_text="Priority level for this warehouse")
    code = models.CharField(max_length=40, unique=True)
    site_code = models.CharField(max_length=40, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    # in .refs keep tack of the related inventory stacks, vendors, etc.
    class Meta:
        indexes = [
            models.Index(fields=("site_code", "is_active"), name="wh_site_active_idx"),
            models.Index(fields=("is_active", "priority"), name="wh_active_priority_idx"),
        ]

    def __str__(self):  # pragma: no cover
        return self.code

    # ---------------- Helpers & Validation -----------------
    def clean(self):  # pragma: no cover (simple validation)
        from django.core.exceptions import ValidationError
        errors = {}
        if not isinstance(self.count, dict):
            self.count = default_count()
        else:
            # Ensure all keys exist
            base = default_count()
            for k, v in base.items():
                self.count.setdefault(k, v)
            # value & deviation validation
            val = self.count.get("value")
            if val is not None:
                try:
                    if float(val) < 0:
                        errors.setdefault("count", []).append("value must be >= 0")
                except Exception:
                    errors.setdefault("count", []).append("value must be numeric")
            dev = self.count.get("deviation")
            if dev is not None:
                try:
                    float(dev)
                except Exception:
                    errors.setdefault("count", []).append("deviation must be numeric")
            # length trims
            for key in ("aisle", "column", "shelf", "bin", "counted_by"):
                if not isinstance(self.count.get(key), str):
                    self.count[key] = ""
                else:
                    if len(self.count[key]) > 80:
                        self.count[key] = self.count[key][:80]
            # dt_counted numeric
            dtc = self.count.get("dt_counted")
            if dtc is not None and not isinstance(dtc, int):
                try:
                    self.count["dt_counted"] = int(dtc)
                except Exception:
                    errors.setdefault("count", []).append("dt_counted must be epoch ms int")
        if errors:
            raise ValidationError(errors)
        return super().clean()

    def update_count(self, value, user=None, deviation=None, item=None, **loc):  # pragma: no cover lightweight
        """Update count snapshot with current UTC time (ms).

        Args:
            value: numeric counted quantity (>=0)
            user: user object or string (optional)
            deviation: optional variance vs system expectation
            item: optional Item instance or id; added to refs.links.items if provided
            loc: optional location granularity overrides (aisle, column, shelf, bin)
        """
        if not isinstance(self.count, dict):
            self.count = default_count()
        now_ms = int(timezone.now().timestamp() * 1000)
        self.count["value"] = value
        if deviation is not None:
            self.count["deviation"] = deviation
        self.count["dt_counted"] = now_ms
        # track item linkage
        if item is not None:
            item_id = None
            if hasattr(item, "id"):
                item_id = getattr(item, "id")
            else:
                try:
                    item_id = int(item)
                except Exception:
                    item_id = None
            if item_id is not None:
                if not isinstance(self.refs, dict):  # sanity fallback
                    from common.models import default_refs  # local import to avoid circular
                    self.refs = default_refs()
                links = self.refs.setdefault("links", {})
                items_list = links.setdefault("items", [])
                if item_id not in items_list:
                    items_list.append(item_id)
        if user is not None:
            if hasattr(user, "id"):
                self.count["counted_by_id"] = getattr(user, "id")
            self.count["counted_by"] = getattr(user, "username", str(user))
        for k in ("aisle", "column", "shelf", "bin"):
            if k in loc and loc[k] is not None:
                self.count[k] = str(loc[k])[:80]
        return self

    def add_item_link(self, item):  # pragma: no cover simple helper
        """Add an item id to refs.links.items without updating count snapshot."""
        if hasattr(item, "id"):
            item_id = getattr(item, "id")
        else:
            try:
                item_id = int(item)
            except Exception:
                return self
        if not isinstance(self.refs, dict):
            from common.models import default_refs
            self.refs = default_refs()
        items_list = self.refs.setdefault("links", {}).setdefault("items", [])
        if item_id not in items_list:
            items_list.append(item_id)
        return self


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
