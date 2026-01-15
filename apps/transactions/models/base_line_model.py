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
        "order": "order", "order_line": "order", "sales_order_line": "order", "salesorderline": "order",
        "invoice": "invoice", "invoice_line": "invoice", "invoiceline": "invoice",
        "work_order": "work_order", "work_order_line": "work_order", "workorderline": "work_order",
        "purchase_order": "purchase_order", "purchase_order_line": "purchase_order", "purchaseorderline": "purchase_order",
    }
    return aliases.get(n, n)

def default_quantity(transaction_type: str | None = None) -> Dict[str, Any]:
    kind = _normalize_line_kind(transaction_type)
    if kind == "proposal":
        return {
            "placed": 0,
            "ordered": 0,
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
            "invoiced": 0,
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
            "packed": 0,
            "remaining": 0,
            "is_fixed": False,
            "precision": 2,
            "is_blanket": False,
            "increment": 0
            }
    
    elif kind == "purchase" or kind == "work_order":
        # Invoices track packing/ship confirmation at line-level
        return {
            "placed": 0,
            "received": 0,
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
            "remaining": None,
            "is_fixed": False,
            "precision": 2,
        }

def default_cost() -> Dict[str, Any]:
    """Firm cost schema for all line models (exec + sell).
    Keys mirror what PurchaseOrder totals expect to aggregate.
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

        # Set placed from item defaults if not already set
        self._apply_item_quantity_default()

        # normalize cost strictly
        self.cost = normalize_cost_map(getattr(self, "cost", None))

        # Set default cost from item for exec-side transactions
        self._apply_item_cost_default()

    def _apply_item_quantity_default(self) -> None:
        """Set quantity.placed from item's sell/purchase_quantity_default based on transaction type."""
        if not isinstance(self.quantity, dict):
            return
        # Only apply default if placed is 0 or None (not yet set by user)
        placed = self.quantity.get("placed")
        if placed not in (0, None):
            return

        kind = _normalize_line_kind(self._meta.model_name)
        item_qty = self.item.get("quantity") if isinstance(self.item, dict) else None

        if kind in ("proposal", "order", "invoice"):
            # Sell-side: use sell_quantity_default
            default_qty = 1
            if isinstance(item_qty, dict):
                default_qty = item_qty.get("sell_quantity_default", 1) or 1
            self.quantity["placed"] = default_qty
        elif kind in ("purchase_order", "work_order"):
            # Exec-side: use purchase_quantity_default
            default_qty = 1
            if isinstance(item_qty, dict):
                default_qty = item_qty.get("purchase_quantity_default", 1) or 1
            self.quantity["placed"] = default_qty

    def _apply_item_cost_default(self) -> None:
        """Set cost.unit and cost.unit_base from item cost for exec-side transactions.
        
        Precedence: standard -> last -> avg -> 0
        """
        if not isinstance(self.cost, dict):
            return
        # Only apply default if unit is 0 or None (not yet set)
        if self.cost.get("unit") not in (0, 0.0, None):
            return

        kind = _normalize_line_kind(self._meta.model_name)
        if kind not in ("purchase_order", "work_order"):
            return

        item_cost = self.item.get("cost") if isinstance(self.item, dict) else None
        default_cost = 0.0

        if isinstance(item_cost, dict):
            # Try in order: standard, last, avg
            for key in ("standard", "last", "avg"):
                val = item_cost.get(key)
                if val is not None and val != 0:
                    try:
                        default_cost = float(val)
                        break
                    except (TypeError, ValueError):
                        continue

        self.cost["unit"] = default_cost
        self.cost["unit_base"] = default_cost

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
        self._apply_item_price_default()
        self._calculate_extended_price()

    def _apply_item_price_default(self) -> None:
        """Set price.unit and price.unit_base from item.price.base for sell transactions.
        
        Only applies if no price_level is defined or there are no values for that level.
        """
        if not isinstance(self.price, dict):
            return
        # Only apply default if unit is 0 or None (not yet set)
        if self.price.get("unit") not in (0, 0.0, None):
            return

        item_price = self.item.get("price") if isinstance(self.item, dict) else None
        default_price = 0.0

        # Check if price_level is defined and has a value
        price_level = getattr(self, "price_level", None)
        if price_level and isinstance(item_price, dict):
            # Try to get price from tiers for this level
            tiers = item_price.get("tiers") or []
            for tier in tiers:
                if isinstance(tier, dict) and tier.get("level") == price_level:
                    tier_price = tier.get("price")
                    if tier_price is not None and tier_price != 0:
                        try:
                            default_price = float(tier_price)
                            break
                        except (TypeError, ValueError):
                            continue

        # If no price_level or no tier value found, use base price
        if default_price == 0.0 and isinstance(item_price, dict):
            base_price = item_price.get("base")
            if base_price is not None:
                try:
                    default_price = float(base_price)
                except (TypeError, ValueError):
                    default_price = 0.0

        self.price["unit"] = default_price
        self.price["unit_base"] = default_price

    def _calculate_extended_price(self) -> None:
        """Calculate and update the extended prices in price and cost JSON."""
        quantity = self.quantity.get("placed", 0) if self.quantity else 0

        # Calculate sell extended
        if self.price:
            unit_price = self.price.get("unit", 0)
            discount_amount = self.price.get("discount_amount", 0)
            extended = float(_to_decimal(quantity * unit_price - discount_amount, places=self.price.get("precision", 2)))
            self.price["extended"] = extended

        # Calculate cost extended
        if self.cost:
            unit_cost = self.cost.get("unit", 0)
            extended_cost = float(_to_decimal(quantity * unit_cost, places=self.cost.get("precision", 2)))
            self.cost["extended"] = extended_cost


class BaseExecLineModel(BaseLineCore):
    """Execution-side documents (purchase/work orders)."""
    class Meta(BaseLineCore.Meta):
        abstract = True

