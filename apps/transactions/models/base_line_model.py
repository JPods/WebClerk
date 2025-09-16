"""Abstract base line model for transaction line items.
Used by ProposalLine, SalesOrderLine, RequisitionLine, WorkOrderLine, InvoiceLine, PurchaseOrderLine.
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
        return {"is_blanket": False, "increment": 0}
    elif transaction_type == "order":
        # Sales orders track fulfillment progress
        return {"shipped": 0, "invoiced": 0}
    elif transaction_type == "invoice":
        # Invoices track packing/ship confirmation at line-level
        return {"packed": 0}
    else:
        # Default structure
        return {
            "placed": None,
            "backlog": None,
            "remaining": None,
            "is_fixed": False,
            "precision": 2,
        }

def default_cost() -> Dict[str, Any]:
    """Firm cost schema with JSON-serializable numeric defaults.

    Note: Use floats for JSONField compatibility; any precision enforcement
    happens during normalization.

    - unit: per-unit cost
    - freight: freight allocation cost
    - extended: unit * quantity minus discounts (if any)
    - is_fixed: whether cost is fixed (no auto recompute)
    - precision: decimal places to display/quantize
    """
    return {
        "unit": 0.0,
        "freight": 0.0,
        "extended": 0.0,
        "is_fixed": False,
        "precision": 2,
    }

def default_prefs() -> Dict[str, Any]:
    return {
        "currency": "",
        "locale": "",
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
        # Resource planning scaffold for lines
        "resources": {
            "required": {},
            "allocated": {},
        },
        "parent_link": {},  # populated during flow conversions (kind/id + quantity_at_parent)
        "forms": [],
    }

def default_refs() -> Dict[str, Any]:
    return {
        "serials": [],  # each: {id, serial_number, status, qty?, lot?}
        "links": {"linkage": []},  # list of linkage record ids (usually length 1 for flow lineage)
        # Optional execution dependencies
        "depends_on": {},
    }

def default_price() -> Dict[str, Any]:
    """Firm price schema per line (authoritative keys and defaults)."""
    return {
        "unit": Decimal("0.00"),
        "discount_percent": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "extended": Decimal("0.00"),
        "is_fixed": False,
        "precision": 2,
    }

# --- Normalization helpers -------------------------------------------------
def _to_decimal(val: Any, places: int = 2) -> Decimal:
    try:
        d = Decimal(str(val))
    except Exception:
        d = Decimal("0")
    q = Decimal("1").scaleb(-places)  # 10^(-places)
    try:
        return d.quantize(q)
    except Exception:
        return d

def normalize_price_map(p: Dict[str, Any] | None) -> Dict[str, Any]:
    base = default_price()
    data = dict(base)
    if isinstance(p, dict):
        if "unit" in p:
            data["unit"] = _to_decimal(p.get("unit"), places=int(base["precision"]))
        if "discount_percent" in p:
            data["discount_percent"] = _to_decimal(p.get("discount_percent"), places=2)
        if "discount_amount" in p:
            data["discount_amount"] = _to_decimal(p.get("discount_amount"), places=int(base["precision"]))
        if "extended" in p:
            data["extended"] = _to_decimal(p.get("extended"), places=int(base["precision"]))
        if "is_fixed" in p:
            data["is_fixed"] = bool(p.get("is_fixed"))
        if "precision" in p:
            val = p.get("precision")
            try:
                data["precision"] = int(val) if val is not None else data["precision"]
            except Exception:
                pass
    return data

def normalize_cost_map(c: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normalize cost JSON to a firm, JSON-serializable shape (floats/ints only)."""
    base = default_cost()
    data = dict(base)
    if isinstance(c, dict):
        # ensure precision first for quantization
        prec = base.get("precision", 2)
        if "precision" in c:
            try:
                raw_prec = c.get("precision")
                if raw_prec is not None:
                    prec = int(raw_prec)
            except Exception:
                pass
        data["precision"] = prec

        for key in ("unit", "freight", "extended"):
            if key in c:
                try:
                    # quantize using Decimal then cast to float for JSON
                    data[key] = float(_to_decimal(c.get(key), places=int(prec)))
                except Exception:
                    data[key] = float(0)
        if "is_fixed" in c:
            data["is_fixed"] = bool(c.get("is_fixed"))
    return data


class BaseLineModel(BaseModel):
    """Abstract base line model for transactional documents.

    Note: The concrete line models must declare a ForeignKey named `parent` to their
    header model (e.g., Invoice). Django will automatically provide a `parent_id`
    attribute/column for fast filtering; we do not define a separate `parent_id`
    field here to avoid column clashes.
    """
    # Mirror of parent FK for legacy compatibility (db column may be NOT NULL in some envs)
    parent_id = models.BigIntegerField(blank=True, null=True, db_index=True)

    # price selection level (retail, wholesale, distributor, sample, promo, etc.)
    price_level = models.CharField(max_length=50, blank=True, null=True, db_column="price_level")
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

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=("parent",), name="baseline_parent_idx"),
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
        # The BaseModel already provides metadata/refs/prefs fields; we do not
        # supply full replacements here. Instead we add missing subkeys below.
        # Keeping factories here allows legacy populate_json_fields to work if
        # those values are empty/falsy at runtime.
        "metadata": default_metadata,
        "refs": default_refs,
        "prefs": default_prefs,
    }

    # --- Schema enforcement helpers -------------------------------------
    @staticmethod
    def _coerce_number(val: Any, precision: int = 2) -> int | float:
        try:
            # Use Decimal for rounding, then cast back to float/int for JSON
            d = Decimal(str(val))
            q = d.quantize(Decimal(10) ** -precision) if precision >= 0 else d
            # Keep integers as int when precision is 0
            return int(q) if precision == 0 else float(q)
        except Exception:
            return 0 if precision == 0 else float(0)

    def _normalize_price_schema(self) -> None:
        """Ensure price JSON has firm keys and normalized types/values.

        Required keys: unit, discount_percent, discount_amount, extended, is_fixed, precision
        Optional: margins, manufacturer_suggested_retail (left as-is if provided)
        """
        data = getattr(self, "price", None) or {}
        if not isinstance(data, dict):
            data = {}
        precision = data.get("precision", 2)
        try:
            precision = int(precision)
        except Exception:
            precision = 2
        normalized = {
            "unit": self._coerce_number(data.get("unit", 0), precision),
            "discount_percent": self._coerce_number(data.get("discount_percent", 0), 2),
            "discount_amount": self._coerce_number(data.get("discount_amount", 0), precision),
            "extended": self._coerce_number(data.get("extended", 0), precision),
            "is_fixed": bool(data.get("is_fixed", False)),
            "precision": precision,
        }
        # Preserve optional keys if present; otherwise keep None
        if "margins" in data:
            normalized["margins"] = data.get("margins")
        else:
            normalized["margins"] = None
        if "manufacturer_suggested_retail" in data:
            normalized["manufacturer_suggested_retail"] = data.get("manufacturer_suggested_retail")
        else:
            normalized["manufacturer_suggested_retail"] = None
        # Only assign back if changed to avoid unnecessary writes
        if data != normalized:
            self.price = normalized  # type: ignore[assignment]

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

        # Ensure line‑specific keys exist inside inherited envelopes
        # Metadata: ensure resources + parent_link + forms
        if isinstance(getattr(self, "metadata", None), dict):
            md = dict(self.metadata)
            res = md.setdefault("resources", {})
            if isinstance(res, dict):
                res.setdefault("required", {})
                res.setdefault("allocated", {})
            md.setdefault("parent_link", {})
            md.setdefault("forms", [])
            self.metadata = md  # type: ignore[assignment]

        # Refs: ensure expected line refs scaffolding exists without clobbering base keys
        if isinstance(getattr(self, "refs", None), dict):
            rf = dict(self.refs)
            rf.setdefault("serials", [])
            rf.setdefault("bill_to", {})
            rf.setdefault("ship_to", {})
            links = rf.setdefault("links", {})
            if isinstance(links, dict):
                links.setdefault("linkage", [])
            rf.setdefault("depends_on", rf.get("depends_on", {}))
            self.refs = rf  # type: ignore[assignment]

        # Prefs: ensure common line prefs exist
        if isinstance(getattr(self, "prefs", None), dict):
            pf = dict(self.prefs)
            pf.setdefault("currency", "")
            pf.setdefault("locale", "")
            pf.setdefault("terms", "")
            self.prefs = pf  # type: ignore[assignment]

        # Final: normalize price/cost shapes strictly
        self.price = normalize_price_map(getattr(self, "price", None))
        self.cost = normalize_cost_map(getattr(self, "cost", None))

        # Enforce firm schemas on certain JSON clusters
        self._normalize_price_schema()

    # Backwards compatibility shim
    def populate_json_fields(self):  # pragma: no cover - retained for legacy calls
        self.ensure_json_defaults()
        self.save(update_fields=[
            "comments", "item", "quantity", "cost", "price", "tax",
            "action", "physical", "flow", "source"
        ])

    def clean(self):  # Validation hook
        super().clean()

    def save(self, *args, **kwargs):  # noqa: D401
        """Primary save override (JSON initialization + parent FK mirror)."""
        self.ensure_json_defaults()
        # Maintain parent_ref_id mirror for environments requiring the column
        try:
            pid = getattr(self, "parent_id", None)
            if pid and getattr(self, "parent_ref_id", None) != pid:
                self.parent_ref_id = pid  # type: ignore[assignment]
        except Exception:
            pass
        return super().save(*args, **kwargs)

    def to_compact_dict(self) -> Dict[str, Any]:
        """Lightweight serialization for logs or keyword extraction."""
        return {
            "id": getattr(self, "id", None),
            # Keep both keys for a short deprecation window; native field is parent_id
            "parent_id": getattr(self, "parent_id", None),
            "status": self.status,
            # Back-compat export: keep type_sale key for now (mirrors price_level)
            "type_sale": getattr(self, "price_level", None),
            "price_level": getattr(self, "price_level", None),
            # probability intentionally omitted (proposal-specific)
            "item": self.item,
            "quantity": self.quantity,
            "price": self.price,
            "cost": self.cost,
        }

    # Legacy commented field list intentionally removed for clarity.

    # NOTE: Avoid embedding raw SQL DDL here. Django migrations own schema evolution.

