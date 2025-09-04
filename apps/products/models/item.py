from __future__ import annotations

from django.db import models
from common.models import BaseModel
from common.stats_mixin import StatsMixin


# ---- Default JSON factories (document expected schema) -----------------
def default_price():
    """Price dictionary structure.

    Keys:
        base: primary sell price
        msrp: manufacturer suggested retail price
        tiers: list of {level, price} for customer segment based overrides (not quantity)
        qty_breaks: list of quantity-based breaks sorted by min_qty ascending.
            Each element either:
              {min_qty:int, unit_price:Decimal}  -- inline quantity break
              OR {min_qty:int, variant_item_id:int} -- delegate to variant item pricing
        currency: ISO currency code
        history: optional recent adjustments (not authoritative ledger)
    """
    return {"base": None, "msrp": None, "tiers": [], "qty_breaks": [], "currency": "USD", "history": []}


def default_cost():
    """Cost dictionary structure.

    Keys:
        standard: standard costing (may align with GL)
        last: last receipt unit cost
        avg: moving average cost
        landed: landed cost (including freight/duties)
        currency: ISO currency
        components: optional breakdown (freight, duty, overhead)
        breaks: list of quantity-based cost breaks (same pattern as pricing qty_breaks)
    """
    return {
        "standard": None,
        "last": None,
        "avg": None,
        "landed": None,
        "currency": "USD",
        "components": {},
        "breaks": [],
    }


def default_catalog():
    """Catalog placement data.

    Keys:
        categories: ordered list of category slugs/ids
        attributes: free-form spec key/value pairs
        web: {slug, title, short, seo:{...}}
        flags: lightweight booleans (featured, seasonal, restricted)
    """
    return {"categories": [], "attributes": {}, "web": {}, "flags": {}}


def ensure_item_prefs(prefs: dict | None) -> dict:
    """Ensure prefs has minimal item-specific sections without overwriting user data."""
    if not isinstance(prefs, dict):
        prefs = {}
    prefs.setdefault("display", {})            # presentation (columns, default_uom)
    prefs.setdefault("restrictions", {})       # channel / region restrictions
    prefs.setdefault("shipping", {})           # weight, dims cache
    prefs.setdefault("userdefined", "")       # preserve original base key
    return prefs

# Explicit wrapper factories (some Django system checks were not recognizing
# the prior function objects as callables for JSONField defaults in certain
# import orders). Using simple un-nested factories guarantees compliance.
def price_default_factory():
    return default_price()

def cost_default_factory():
    return default_cost()


class Item(StatsMixin, BaseModel):
    """Catalog item (physical good, service placeholder, or bundle)."""

    KIND_PHYSICAL = "physical"
    KIND_SERVICE = "service"
    KIND_BUNDLE = "bundle"
    KIND_CHOICES = [
        (KIND_PHYSICAL, "Physical"),
        (KIND_SERVICE, "Service"),
        (KIND_BUNDLE, "Bundle"),
    ]

    name = models.CharField(max_length=160, db_index=True)
    sku = models.CharField(max_length=80, blank=True, null=True, unique=True)
    qr_code = models.CharField(max_length=255, blank=True, null=True, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_PHYSICAL, db_index=True)
    uom = models.CharField(max_length=20, blank=True, help_text="Unit of measure (EA, HR, KG, etc)")
    base_uom = models.CharField(max_length=20, blank=True, help_text="Canonical base unit for conversions when uom varies")
    description = models.TextField(blank=True)
    default_cost = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    default_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    gls = models.JSONField(default=dict, blank=True, help_text="General ledger account mappings: {inventory, cogs, revenue, variance}")
        #     #"gl_cost" VARCHAR(255),
        #     #"gl_inventory" VARCHAR(255),
        #     #"gl_sales" VARCHAR(255),
    is_back_order_allowed = models.BooleanField(default=False)
    is_discountable = models.BooleanField(default=False)
    is_linked = models.BooleanField(default=False)
    is_not_tracked = models.BooleanField(default=False)
    is_pacing = models.BooleanField(default=False)
    is_print_not = models.BooleanField(default=False)
    is_serialized = models.BooleanField(default=False)
    is_tally_by_type = models.BooleanField(default=False)
    price = models.JSONField(default=price_default_factory, blank=True, help_text="Pricing information dict; see default_price() schema")
    #"price_average_sale" DOUBLE PRECISION,
    #"price_manufacturer_suggested" DOUBLE PRECISION
    # retail, wholesale, education, distributor, etc...,
    cost = models.JSONField(default=cost_default_factory, blank=True, help_text="Cost information dict; see default_cost() schema")
    #average, last_inship, landed, etc...
    security_level = models.IntegerField(default=0, db_index=True)  
    tax_code = models.CharField(max_length=120, blank=True)
    specification_id = models.BigIntegerField(("Specification ID"), null=True, blank=True)
    catalog = models.JSONField("Catalog", default=default_catalog, blank=True, help_text="Catalog placement data; see default_catalog() schema")
    # volumen of sales, number of items, 
    # number of returns, margins, margin velocity
    quantity = models.JSONField(default=dict, blank=True, help_text="Inventory quantity status (on hand, allocated, available, on order)")

    class Meta:
        indexes = [
            models.Index(fields=("kind", "is_active"), name="item_kind_active_idx"),
        ]

    def __str__(self):  # pragma: no cover
        return self.name or f"Item#{self.pk}"

    # Enforce/merge JSON schema defaults & item-pref enrichment
    def save(self, *args, **kwargs):  # pragma: no cover - behavior validated indirectly
        # Defensive merges (avoid overwriting existing populated dicts)
        if not isinstance(self.price, dict):
            self.price = default_price()
        else:
            base_schema = default_price()
            for k, v in base_schema.items():
                self.price.setdefault(k, v)
        if not isinstance(self.cost, dict):
            self.cost = default_cost()
        else:
            cost_schema = default_cost()
            for k, v in cost_schema.items():
                self.cost.setdefault(k, v)
        if not isinstance(self.catalog, dict):
            self.catalog = default_catalog()
        else:
            cat_schema = default_catalog()
            for k, v in cat_schema.items():
                self.catalog.setdefault(k, v)
        # prefs from BaseModel (PrefsMixin)
        if hasattr(self, 'prefs'):
            self.prefs = ensure_item_prefs(getattr(self, 'prefs'))  # type: ignore[attr-defined]

        # --- Validation / normalization for quantity breaks -----------------
        def _normalize_breaks(seq, price_key: str):
            """Normalize and validate a list of break dicts.

            Rules:
              - Must be a list of dicts
              - Each requires integer min_qty >= 0
              - Either unit_{price_key} present (Decimal/number) OR variant_item_id (int) but not both missing
              - No duplicate min_qty values
              - Sorted ascending by min_qty
            Returns cleaned list (sorted).
            """
            if not isinstance(seq, list):
                return []
            cleaned = []
            seen_qty = set()
            value_field = f"unit_{price_key}"
            for row in seq:
                if not isinstance(row, dict):
                    continue
                mq = row.get("min_qty")
                if not isinstance(mq, int) or mq < 0:
                    raise ValueError("min_qty must be non-negative int")
                if mq in seen_qty:
                    raise ValueError("Duplicate min_qty in breaks")
                variant_id = row.get("variant_item_id")
                val = row.get(value_field)
                if variant_id is None and val is None:
                    raise ValueError(f"Each break needs {value_field} or variant_item_id")
                cleaned.append({"min_qty": mq, **({"variant_item_id": variant_id} if variant_id is not None else {}), **({value_field: val} if val is not None else {})})
                seen_qty.add(mq)
            cleaned.sort(key=lambda r: r["min_qty"])  # stable
            return cleaned

        # Normalize pricing quantity breaks
        self.price["qty_breaks"] = _normalize_breaks(self.price.get("qty_breaks", []), "price")
        # Normalize cost breaks
        self.cost["breaks"] = _normalize_breaks(self.cost.get("breaks", []), "cost")
        super().save(*args, **kwargs)


# CREATE TABLE IF NOT EXISTS "items" (
#     "bar_code" VARCHAR(255),
#     "category" VARCHAR(80),
#     "type" VARCHAR(255),
#     "description" VARCHAR(255),
#     "description_text" TEXT,
# 	“Gls” JSONB
#     "status" VARCHAR(80),


#     #metadata "hazard_category" VARCHAR(255),
#     "is_active" BOOLEAN DEFAULT FALSE,

 

# 	“pricing” JSONB
#     "security_level" INTEGER,
#     "tax_code" VARCHAR(120),
#     "web_page" VARCHAR(255)
# );
