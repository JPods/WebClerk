"""Abstract base line model for transaction line items.
Used by ProposalLine, OrderLine, RequisitionLine, WorkOrderLine, InvoiceLine, PurchaseLine.
The goal is to keep a compact set of JSON fields that capture the rich
state of a line (pricing, cost, quantities, taxes, metadata, workflow, etc.)
    without exploding the relational schema. Each JSON field has a structured
    default producer for clarity and forward compatibility.

Google Doc (design):
https://docs.google.com/document/d/12C8LHt8x1Bl6spM_iHFC6DK01eIxQzD5_4-3cK9ybow/edit?tab=t.0
"""

from decimal import Decimal
from typing import Any, Callable, Dict
from django.db import models
from common.models import BaseModel, default_prefs, default_metadata, default_refs
from apps.transactions.models.base_transaction_model import default_tax

BASE_DECIMAL_DEFAULT = Decimal("0.00")
BASE_INT_DEFAULT = Decimal("0")
def default_readonly():
    return {
        "readonly":["item_id","uuid_item","line_number","is_archived",]
    }

def default_item() -> Dict[str, Any]:
    return {
        # id of the item record, its soft ida, etc...
        # readonly on frontend
        "item_id": None,
        "ida_item": "",
        "uuid_item": "",
        #readwrite
        "description": "",
        "description_text": "",
        "time_lead": None,
        "locations": [],
        "unit_measure": "",
        # sequence of display in frontend. User changeable
        "sequence": 0,
        "line_number": 0,
        "is_deleted": False,
        "is_active": True,
        "is_archived": False
    }

def _normalize_line_kind(name: str | None) -> str:
    """Map model_name or ad-hoc tokens to a canonical line kind."""
    n = (name or "").lower().strip()
    n = n.replace("-", "_")
    # collapse common variants
    aliases = {
        "proposal": "proposal", "proposal_line": "proposal", "proposalline": "proposal",
        "order": "order", "order_line": "order",
        "invoice": "invoice", "invoice_line": "invoice", "invoiceline": "invoice",
        "workorder": "workorder", "workorderline": "workorder",
        "purchase": "purchase", "purchase_order": "purchase", "purchaseline": "purchase", "purchaseorderline": "purchase",
    }
    return aliases.get(n, n)

def default_quantity(transaction_type: str | None = None) -> Dict[str, Any]:
    kind = _normalize_line_kind(transaction_type)
    if kind == "proposal":
        return {
            "placed": 0,
            "actioned": 0,
            "remaining": 0,
            "is_fixed": False,
            "precision": 2,
            "is_blanket": False,
            "increment": 0
            }
    elif kind == "order":
        # Sales orders track fulfillment progress
        return {
            "placed": 0,
            "actioned": 0,
            "remaining": 0,
            "is_fixed": False,
            "precision": 2,
            "is_blanket": False,
            "increment": 0
            }
    elif kind == "invoice":
        # Invoices track packing/ship confirmation at line-level
        return {
            "placed": 0,
            "actioned": 0,
            "remaining": 0,
            "is_fixed": False,
            "precision": 2,
            "is_blanket": False,
            "increment": 0
            }
    
    elif kind == "purchase" or kind == "workorder":
        # Invoices track packing/ship confirmation at line-level
        return {
            "placed": 0,
            "actioned": 0,
            "remaining": 0,
            "is_fixed": False,
            "precision": 2,
            "is_blanket": False,
            "increment": 0
            }
    else:
        # Default structure
        return {
            "placed": None,
            "actioned": None,
            "remaining": None,
            "is_fixed": False,
            "precision": 2,
        }

def default_cost() -> Dict[str, Any]:
    """Firm cost schema for all line models (exec + sell).
    Keys mirror what Purchase totals expect to aggregate.
    """
    return {
        # per-line unit and extended
        "unit": 0.0,
        "unit_base": 0.0,
        "discount_percent": 0.0,
        "discount_amount": 0.0,
        "extended": 0.0,
        # surcharges and logistics
        "shipping": 0.0,
        "handling": 0.0,
        "freight": 0.0,
        "commissions": 0.0,
        # taxes
        "tax_rate": 0.0,
        "tax": 0.0,
        # controls
        "is_fixed": False,
        "precision": 2,
        # optional metadata (stable keys, keep but don’t rely on for math)
        "tax_code": "",
        "tax_code_id": 0,
        "tax_lookup_id": 0,
    }

def default_price() -> Dict[str, Any]:
    """Firm price schema per line (authoritative keys and defaults)."""
    return {
        "unit": 0.0,
        "unit_base": 0.0,
        "discount_percent": 0.0,
        "discount_amount": 0.0,
        "extended": 0.0,
        "is_fixed": False,
        "precision": 2,
    }

def _to_decimal(val: Any, places: int = 2) -> Decimal:
    try:
        d = Decimal(str(val))
        return d.quantize(Decimal(10) ** -places) if places >= 0 else d
    except Exception:
        return Decimal(0)

def normalize_price_map(p: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normalize price JSON to a JSON-serializable shape (floats/ints only)."""
    base = default_price()
    data = dict(base)
    if isinstance(p, dict):
        # precision
        prec = base.get("precision", 2)
        if "precision" in p:
            try:
                raw = p.get("precision")
                if raw is not None:
                    prec = int(raw)
            except Exception:
                pass
        data["precision"] = prec
        # money-like values
        for key, places in (("unit", prec), ("discount_amount", prec), ("extended", prec)):
            if key in p:
                try:
                    data[key] = float(_to_decimal(p.get(key), places=int(places)))
                except Exception:
                    data[key] = 0.0
        # percent with fixed 2dp
        if "discount_percent" in p:
            try:
                data["discount_percent"] = float(_to_decimal(p.get("discount_percent"), places=2))
            except Exception:
                data["discount_percent"] = 0.0
        if "is_fixed" in p:
            data["is_fixed"] = bool(p.get("is_fixed"))
    return data

def normalize_cost_map(c: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normalize line.cost to a strict, JSON-serializable shape."""
    base = default_cost()
    out = dict(base)

    if not isinstance(c, dict):
        return out

    # precision first
    prec = base["precision"]
    if "precision" in c:
        try:
            raw = c.get("precision")
            if raw is not None:
                prec = int(raw)
        except Exception:
            pass
    out["precision"] = prec

    # money-like values coerced to floats with given precision
    for key, places in (
        ("unit", prec),
        ("extended", prec),
        ("shipping", prec),
        ("handling", prec),
        ("freight", prec),
        ("commissions", prec),
        ("tax", prec),
    ):
        if key in c:
            try:
                out[key] = float(_to_decimal(c.get(key), places=int(places)))
            except Exception:
                out[key] = float(0)

    # tax_rate as float (4dp tolerance)
    if "tax_rate" in c:
        try:
            out["tax_rate"] = float(_to_decimal(c.get("tax_rate"), places=4))
        except Exception:
            out["tax_rate"] = 0.0

    # controls and optional metadata
    if "is_fixed" in c:
        out["is_fixed"] = bool(c.get("is_fixed"))
    if "tax_code" in c:
        out["tax_code"] = str(c.get("tax_code") or "")
    if "tax_code_id" in c:
        try:
            out["tax_code_id"] = int(c.get("tax_code_id") or 0)
        except Exception:
            out["tax_code_id"] = 0

    return out


def default_physical() -> Dict[str, Any]:
    return {
        "weight": {"value": 0.0, "unit": ""},
        "dimensions": {"length": 0.0, "width": 0.0, "height": 0.0, "unit": ""},
        "volume": {"value": 0.0, "unit": ""},
        "package_count": 0,
        "is_hazmat": False
    }


class BaseLineCore(BaseModel):
    """Abstract core for all transaction line models.
    Shared envelopes only; no price field here.
    Concrete models must define `parent = models.ForeignKey(...)`.
    """
    # IMPORTANT: do NOT declare parent_id here; Django will add it from the FK on concrete classes.

    price_level = models.CharField(max_length=50, blank=True, null=True, db_column="price_level")
    status = models.CharField(max_length=50, blank=True, null=True)

    # FK-first: proper ForeignKey to Item for referential integrity.
    # The `item` JSONField below holds denormalized item details (description, etc.)
    # for fast reads; the FK is the source of truth for the relationship.
    item_fk = models.ForeignKey(
        'products.Item', on_delete=models.PROTECT,
        blank=True, null=True,
        db_column='item_id_fk', related_name='%(class)s_lines',
    )

    # Common JSON fields (do NOT redeclare action/flow/source here; provided by BaseModel mixins)
    item = models.JSONField(default=dict, blank=True, null=True)
    quantity = models.JSONField(default=dict, blank=True, null=True)
    cost = models.JSONField(default=dict, blank=True, null=True)
    tax = models.JSONField(default=dict, blank=True, null=True)
    physical = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        abstract = True
        indexes = [
            # Let Django auto-name; applies per concrete model that defines 'parent'
            models.Index(fields=["parent"]),
        ]

    JSON_DEFAULT_FACTORIES: Dict[str, Callable[[], Dict[str, Any]]] = {
        "item": default_item,
        "cost": default_cost,
        "tax": default_tax,
        "physical": default_physical,
        # metadata/refs/prefs live on BaseModel; still safe to seed here
        "metadata": default_metadata,
        "refs": default_refs,
        "prefs": default_prefs,
    }

    def ensure_json_defaults(self) -> None:
        # initialize configured JSON clusters
        for field_name, factory in self.JSON_DEFAULT_FACTORIES.items():
            val = getattr(self, field_name, None)
            if not val:
                setattr(self, field_name, factory())

        # quantity variant by model kind
        if not self.quantity:
            self.quantity = default_quantity(transaction_type=self._meta.model_name)

        # normalize cost strictly
        self.cost = normalize_cost_map(getattr(self, "cost", None))

    def save(self, *args, **kwargs):
        self.ensure_json_defaults()
        return super().save(*args, **kwargs)


class BaseSellLineModel(BaseLineCore):
    """Sell-side documents (proposal, order, invoice)."""
    price = models.JSONField(default=dict, blank=True, null=True)

    class Meta(BaseLineCore.Meta):
        abstract = True

    JSON_DEFAULT_FACTORIES = dict(BaseLineCore.JSON_DEFAULT_FACTORIES, price=default_price)

    def ensure_json_defaults(self) -> None:
        super().ensure_json_defaults()
        self.price = normalize_price_map(getattr(self, "price", None))
        self._calculate_extended_price()

    def _calculate_extended_price(self) -> None:
        """Calculate and update the extended prices in price and cost JSON."""
        quantity = self.quantity.get("placed", 0) if self.quantity else 0

        # Calculate sell extended
        if self.price:
            unit_price = self.price.get("unit", 0)
            discount_amount = self.price.get("discount_amount", None)
            discount_percent = self.price.get("discount_percent", 0) or 0
            precision = self.price.get("precision", 2)
            gross = _to_decimal(quantity * unit_price, places=precision)
            if discount_amount is None or (discount_amount == 0 and discount_percent):
                discount_amount = float(_to_decimal(gross * (Decimal(discount_percent) / Decimal("100")), places=precision))
            self.price["discount_amount"] = float(_to_decimal(discount_amount, places=precision))
            extended = float(_to_decimal(gross - Decimal(str(self.price["discount_amount"])), places=precision))
            self.price["extended"] = extended

        # Calculate cost extended
        if self.cost:
            unit_cost = self.cost.get("unit", 0)
            discount_cost_amount = self.cost.get("discount_amount", None)
            discount_cost_percent = self.cost.get("discount_percent", 0) or 0
            precision = self.cost.get("precision", 2)
            gross_cost = _to_decimal(quantity * unit_cost, places=precision)
            if discount_cost_amount is None or (discount_cost_amount == 0 and discount_cost_percent):
                discount_cost_amount = float(_to_decimal(gross_cost * (Decimal(discount_cost_percent) / Decimal("100")), places=precision))
            self.cost["discount_amount"] = float(_to_decimal(discount_cost_amount, places=precision))
            extended_cost = float(_to_decimal(gross_cost - Decimal(str(self.cost["discount_amount"])), places=precision))
            self.cost["extended"] = extended_cost


class BaseExecLineModel(BaseLineCore):
    """Execution-side documents (purchase/work orders)."""
    class Meta(BaseLineCore.Meta):
        abstract = True

