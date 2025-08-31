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
            tiers: list of {level, price} for customer segments
            currency: ISO currency code
            history: optional recent adjustments (not authoritative ledger)
        """
        return {"base": None, "msrp": None, "tiers": [], "currency": "USD", "history": []}


def default_cost():
        """Cost dictionary structure.

        Keys:
            standard: standard costing (may align with GL)
            last: last receipt unit cost
            avg: moving average cost
            landed: landed cost (including freight/duties)
            currency: ISO currency
            components: optional breakdown (freight, duty, overhead)
        """
        return {
                "standard": None,
                "last": None,
                "avg": None,
                "landed": None,
                "currency": "USD",
                "components": {},
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
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_PHYSICAL, db_index=True)
    uom = models.CharField(max_length=20, blank=True, help_text="Unit of measure (EA, HR, KG, etc)")
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
    price = models.JSONField(default=default_price, blank=True, help_text="Pricing information dict; see default_price() schema")
    #"price_average_sale" DOUBLE PRECISION,
    #"price_manufacturer_suggested" DOUBLE PRECISION
    # retail, wholesale, education, distributor, etc...,
    cost = models.JSONField(default=default_cost, blank=True, help_text="Cost information dict; see default_cost() schema")
    #average, last_inship, landed, etc...
    security_level = models.IntegerField(default=0, db_index=True)  
    tax_code = models.CharField(max_length=120, blank=True)
    specification_id = models.BigIntegerField(("Specification ID"), null=True, blank=True)
    catalog = models.JSONField("Catalog", default=default_catalog, blank=True, help_text="Catalog placement data; see default_catalog() schema")
    # volumen of sales, number of items, 
    # number of returns, margins, margin velocity


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
