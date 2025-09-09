"""Abstract base line model for transaction line items.

The goal is to keep a compact set of JSON fields that capture the rich
state of a line (pricing, cost, quantities, taxes, metadata, workflow, etc.)
without exploding the relational schema. Each JSON field has a structured
default producer for clarity and forward compatibility.

Google Doc (design):
https://docs.google.com/document/d/12C8LHt8x1Bl6spM_iHFC6DK01eIxQzD5_4-3cK9ybow/edit?tab=t.0
"""

from decimal import Decimal
from typing import Callable, Dict, Any

from django.core.exceptions import ValidationError
from django.db import models

from common.models import BaseModel

BASE_DECIMAL_DEFAULT = Decimal("0.00")
BASE_INT_DEFAULT = Decimal("0")

def default_item() -> Dict[str, Any]:
    return {
        "id_num": None,
        "ida_item": "",
        "uuid_item": "",
        "description": "",
        "description_text": "",
        "time_lead": None,
        "locations": [],
        "unit_measure": "",
        "sequence": 0,
        "line_number": 0,
        "is_deleted": False,
        "is_active": True,
        "is_archived": False
    }

def default_quantity(transaction_type: str | None = None) -> Dict[str, Any]:
    if transaction_type == "proposal":
        return {
            "is_blanket": False,
            "increment": 0
        }
    elif transaction_type == "order":
        return {
            "shipped": 0
        }
    elif transaction_type == "invoice":
        return {
            "packed": 0
        }
    else:
        # Default structure
        return {
            "placed": None,
            "backlog": None,
            "remaining": None,
            "is_fixed": False,
            "precision": 2
        }

def default_cost() -> Dict[str, Any]:
    return {
        "freight": None,
        "unit": None,
        "extended": None,
        "is_fixed": False,
        "precision": 2
    }

def default_price() -> Dict[str, Any]:
    return {
        "unit": None,
        "discount_percent": None,
        "discount_amount": None,
        "extended": None,
        "margins": None,
        "is_fixed": False,
        "precision": 2,
        "manufacturer_suggested_retail": None
    }

def default_tax() -> Dict[str, Any]:
    return {
        "sales_rate": None,
        "sales": None,
        "cost_rate": None,
        "cost": None,
        "shipping": None
    }


def default_comments() -> Dict[str, Any]:
    return {
        "public": "",
        "process": "",
        "foreign": ""
    }

def default_action() -> Dict[str, Any]:
    return {
        "action_next":{"who":"","when":0,"what":""},
        "created": {"who":"","when":0},
        "requested": {"who":"","when":0},
        "updated": {"who":"","when":0}
    }

def default_physical() -> Dict[str, Any]:
    return {
        "unit": 0,
        "extended": 0,
        "volume":{},
        "hazardous": {}
    }

# tracks the how we got this transaction and where it was resolved
# mostly at the transaction level unless split across multiple entities
def default_transaction_flow() -> Dict[str, Any]:
    return {
        "source": [{"type": "", "id": 0}],
        "destination": [{"type": "", "id": 0}]
    }

def default_source() -> Dict[str, Any]:
    return {
        "campaign_id": 0,
        "catalog_id": None,
        "vendor_id": 0,
        "manufacturer_id": 0
    }

def default_metadata() -> Dict[str, Any]:
    return {
    # History is a dict keyed by event ('created','modified', etc.)
    "history": {},
        "parent_link": {},  # populated during flow conversions (kind/id + quantity_at_parent)
        "forms": [],
    }

def default_refs() -> Dict[str, Any]:
    return {
        "serials": [],  # each: {id, serial_number, status, qty?, lot?}
        "bill_to": {},
    "ship_to": {},
    "links": {"linkage": []},  # list of linkage record ids (usually length 1 for flow lineage)
    }

def default_prefs() -> Dict[str, Any]:
    return {"currency": "", "locale": "", "terms": ""}


class BaseLineModel(BaseModel):
    """Abstract transactional line base.

    Concrete subclasses (e.g., ProposalLine, OrderLine, InvoiceLine) can add
    relational FKs or specialized fields. JSON structures are initialized lazily
    (or on first save) to ensure shape consistency without forcing migrations
    for additive keys.
    """

    parent_ref_id = models.BigIntegerField(help_text="Parent transaction primary key (redundant copy of FK for fast filters)", db_index=True)
    probability = models.IntegerField(blank=True, null=True, help_text="For proposals: 0-100 probability percent")
    type_sale = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)

    # JSON field shells (populated via ensure_json_defaults)
    # Core JSON structures (kept intentionally denormalized for agility)
    item = models.JSONField(default=dict, blank=True, null=True)
    quantity = models.JSONField(default=dict, blank=True, null=True)
    cost = models.JSONField(default=dict, blank=True, null=True)
    price = models.JSONField(default=dict, blank=True, null=True)
    tax = models.JSONField(default=dict, blank=True, null=True)
    action = models.JSONField(default=dict, blank=True, null=True)
    physical = models.JSONField(default=dict, blank=True, null=True)
    flow = models.JSONField(default=dict, blank=True, null=True)
    source = models.JSONField(default=dict, blank=True, null=True)
    # Extended / governance & linkage JSON clusters
    metadata = models.JSONField(default=dict, blank=True, null=True, help_text="Lifecycle + lineage (parent_link, history, forms, etc.)")
    refs = models.JSONField(default=dict, blank=True, null=True, help_text="Structured references (bill_to, ship_to, campaign, serials, etc.)")
    prefs = models.JSONField(default=dict, blank=True, null=True, help_text="Preference / option flags (currency, terms, locale, etc.)")
    #comments = models.JSONField(default=dict, blank=True, null=True, help_text="Public/process/foreign comment channels")

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=("parent_ref_id",), name="baseline_parent_ref_idx"),
        ]

    # Mapping of attribute name -> default factory (callable)
    JSON_DEFAULT_FACTORIES: Dict[str, Callable[[], Dict[str, Any]]] = {
        "comments": default_comments,
        "item": default_item,
        # quantity handled separately due to transaction type nuance
        "cost": default_cost,
        "price": default_price,
        "tax": default_tax,
        "action": default_action,
        "physical": default_physical,
        "flow": default_transaction_flow,
        "source": default_source,
    "metadata": default_metadata,
    "refs": default_refs,
    "prefs": default_prefs,
    }

    def ensure_json_defaults(self) -> None:
        """Ensure each JSON field has a structured object instead of empty dict/None.

        Quantity is derived based on model name (heuristic) to allow variant defaults.
        We don't persist (save) here; caller decides when to save – used inside save().
        """
        # Standard fields
        for field_name, factory in self.JSON_DEFAULT_FACTORIES.items():
            val = getattr(self, field_name)
            if not val:  # covers None / empty dict / empty string
                setattr(self, field_name, factory())

        # Quantity (dependent on model variant)
        if not self.quantity:
            setattr(self, "quantity", default_quantity(transaction_type=self._meta.model_name))

    # Backwards compatibility shim
    def populate_json_fields(self):  # pragma: no cover - retained for legacy calls
        self.ensure_json_defaults()
        self.save(update_fields=[
            "comments", "item", "quantity", "cost", "price", "tax",
            "action", "physical", "flow", "source"
        ])

    def clean(self):  # Validation hook
        if self.probability is not None and not (0 <= self.probability <= 100):
            raise ValidationError({"probability": "Must be between 0 and 100."})
        super().clean()

    def save(self, *args, **kwargs):  # noqa: D401
        """Primary save override (JSON initialization + parent FK mirror)."""
        self.ensure_json_defaults()
        parent_obj = getattr(self, "parent", None)
        if parent_obj is not None and getattr(parent_obj, "pk", None):
            # Always mirror (avoid stale copy) rather than only when empty
            self.parent_ref_id = parent_obj.pk
        return super().save(*args, **kwargs)

    def to_compact_dict(self) -> Dict[str, Any]:
        """Lightweight serialization for logs or keyword extraction."""
        return {
            "id": getattr(self, "id", None),
            "parent_ref_id": self.parent_ref_id,
            "status": self.status,
            "type_sale": self.type_sale,
            "probability": self.probability,
            "item": self.item,
            "quantity": self.quantity,
            "price": self.price,
            "cost": self.cost,
        }

    # Legacy commented field list intentionally removed for clarity.

    # NOTE: Avoid embedding raw SQL DDL here. Django migrations own schema evolution.

