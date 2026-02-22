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
        "addresses": [],
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
        "purchase": "purchase", "purchaseline": "purchase",
    }
    return aliases.get(n, n)

def default_quantity(transaction_type: str | None = None) -> Dict[str, Any]:
    """Return the canonical quantity JSONB structure for a line.

    Canonical keys (all transaction types):
      - placed:    quantity committed on this line
      - actioned:  quantity acted upon (meaning is context-dependent):
                     Proposal  → converted to order
                     Order     → shipped / invoiced
                     Invoice   → delivered
                     Purchase  → received from vendor
                     WorkOrder → completed
      - remaining: placed − actioned
      - is_fixed:  whether quantity is locked from editing
      - precision: decimal places for quantity math
      - is_blanket: blanket/open-ended quantity (optional)
      - increment:  minimum order increment (optional)

    Legacy keys (ordered, invoiced, received, shipped, packed) are DEPRECATED.
    Transfer services should read/write placed/actioned/remaining only.

    See: readmes/topics/transactions/transactions-totals.md §2
    """
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
        # Sales orders: actioned = qty shipped/invoiced downstream
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
        # Invoices: actioned = qty delivered/confirmed
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
        # Purchase: actioned = qty received from vendor
        # WorkOrder: actioned = qty completed
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
        # Default structure — used when transaction_type is unknown
        return {
            "placed": None,
            "actioned": None,
            "remaining": None,
            "is_fixed": False,
            "precision": 2,
        }

# Legacy quantity key → canonical key mapping.
# Any of these arriving from old data or external systems are mapped to placed/actioned.
_LEGACY_QTY_ALIASES: Dict[str, str] = {
    "ordered":  "placed",
    "quantity": "placed",
    "qty":      "placed",
    "shipped":  "actioned",
    "invoiced": "actioned",
    "received": "actioned",
    "packed":   "actioned",
    "completed": "actioned",
}


def normalize_quantity_map(q: Dict[str, Any] | None, transaction_type: str | None = None) -> Dict[str, Any]:
    """Normalize a quantity JSON blob to the canonical structure.

    Handles:
      1. None / empty → full default from default_quantity()
      2. Legacy keys (ordered, shipped, received, …) → placed / actioned
      3. Null numeric values → 0
      4. Missing canonical keys → backfilled from defaults
      5. remaining recalculated as placed − actioned
    """
    base = default_quantity(transaction_type)

    if not isinstance(q, dict) or not q:
        return base

    out = dict(base)  # start from full default

    # Map legacy keys first (only when canonical key is still at default)
    for legacy_key, canonical_key in _LEGACY_QTY_ALIASES.items():
        if legacy_key in q and canonical_key in out:
            val = q[legacy_key]
            # Only adopt legacy value if canonical key hasn't been explicitly set
            if q.get(canonical_key) in (None, 0, 0.0):
                try:
                    out[canonical_key] = float(val) if val is not None else 0
                except (TypeError, ValueError):
                    out[canonical_key] = 0

    # Overlay explicit canonical keys from input
    for key in ("placed", "actioned", "remaining"):
        if key in q and q[key] is not None:
            try:
                out[key] = float(q[key])
            except (TypeError, ValueError):
                out[key] = 0
        elif key in out and out[key] is None:
            out[key] = 0

    # Control / metadata keys
    if "is_fixed" in q:
        out["is_fixed"] = bool(q["is_fixed"])
    if "precision" in q:
        try:
            out["precision"] = int(q["precision"])
        except (TypeError, ValueError):
            pass
    if "is_blanket" in q:
        out["is_blanket"] = bool(q["is_blanket"])
    if "increment" in q:
        try:
            out["increment"] = float(q["increment"]) if q["increment"] is not None else 0
        except (TypeError, ValueError):
            out["increment"] = 0

    # Recalculate remaining
    placed = out.get("placed", 0) or 0
    actioned = out.get("actioned", 0) or 0
    out["remaining"] = float(_to_decimal(placed - actioned, places=out.get("precision", 2)))

    return out


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

    # Stable, user-visible line sequence number.  Auto-assigned from
    # parent.line_increment on first save when left at 0.
    # Replaces the old item.line_number JSON key.
    line_number = models.IntegerField(default=0, db_index=True)

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
        """Seed missing JSON envelopes and normalize existing ones.

        Called automatically by save(). Ensures every JSON field has a
        well-formed default structure so downstream code (totals rollup,
        transfer services) can safely read keys without existence checks.

        Flow:
          1. Seed missing envelopes from JSON_DEFAULT_FACTORIES
          2. Normalize quantity via normalize_quantity_map() — always runs
             (maps legacy keys like 'ordered' → 'placed', fills missing keys,
             fixes nulls, recalculates remaining)
          3. Normalize cost via normalize_cost_map() — always runs

        BaseSellLineModel overrides this to also normalize price and
        compute extended values.

        See: readmes/topics/transactions/transactions-totals.md §1
        """
        # Step 1: initialize configured JSON clusters from factory defaults
        for field_name, factory in self.JSON_DEFAULT_FACTORIES.items():
            val = getattr(self, field_name, None)
            if not val:
                setattr(self, field_name, factory())

        # Step 2: normalize quantity (maps legacy keys, fills missing, fixes nulls)
        self.quantity = normalize_quantity_map(
            getattr(self, "quantity", None),
            transaction_type=self._meta.model_name,
        )

        # Step 3: normalize cost strictly (fixes nulls, ensures all keys)
        self.cost = normalize_cost_map(getattr(self, "cost", None))

    def save(self, *args, **kwargs):
        """Save with JSON normalization and auto line_number assignment.

        1. ensure_json_defaults() seeds/normalizes all JSON envelopes.
        2. If line_number is still 0 and a parent header exists,
           auto-assign from parent.line_increment and bump increment.
        """
        self.ensure_json_defaults()

        # Auto-assign line_number from parent header's line_increment
        if self.line_number == 0:
            try:
                parent = self.parent
                if parent is not None and hasattr(parent, 'line_increment'):
                    self.line_number = parent.line_increment
                    parent.line_increment = (parent.line_increment or 10) + 10
                    parent.save(update_fields=['line_increment'])
            except Exception:
                pass  # graceful fallback — line_number stays 0

        return super().save(*args, **kwargs)


class BaseSellLineModel(BaseLineCore):
    """Sell-side line base for Proposal, Order, Invoice.

    Adds the ``price`` JSON envelope and auto-computes extended values
    on every save via _calculate_extended_price().

    Extended calculation (runs in ensure_json_defaults → _calculate_extended_price):
      price.extended = (quantity.placed × price.unit) − discount_amount
      cost.extended  = (quantity.placed × cost.unit)  − discount_amount

    See: readmes/topics/transactions/transactions-totals.md §1
    """
    price = models.JSONField(default=dict, blank=True, null=True)

    class Meta(BaseLineCore.Meta):
        abstract = True

    JSON_DEFAULT_FACTORIES = dict(BaseLineCore.JSON_DEFAULT_FACTORIES, price=default_price)

    def ensure_json_defaults(self) -> None:
        """Extends BaseLineCore: also normalizes price and computes extended."""
        super().ensure_json_defaults()           # seed + normalize cost
        self.price = normalize_price_map(getattr(self, "price", None))  # normalize price
        self._calculate_extended_price()         # compute extended from qty × unit

    def _calculate_extended_price(self) -> None:
        """Compute price.extended and cost.extended from quantity.placed.

        Formula for both price and cost envelopes:
          gross = quantity.placed × unit
          discount_amount = explicit value if set, else gross × (discount_percent / 100)
          extended = gross − discount_amount

        This is the line-level calculation that feeds into header totals
        rollup via compute_*_sell_cost_totals() services.

        See: readmes/topics/transactions/transactions-totals.md §1
        """
        # quantity.placed drives both price and cost extended calculations
        quantity = self.quantity.get("placed", 0) if self.quantity else 0

        # --- SELL EXTENDED: price.extended = qty × price.unit − discount ---
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

        # --- COST EXTENDED: cost.extended = qty × cost.unit − discount ---
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
    """Exec-side line base for Purchase, WorkOrder, Receipt.

    No price envelope — exec lines track cost only.
    Does NOT auto-compute cost.extended on save (unlike BaseSellLineModel).
    Extended cost must be set explicitly by the caller or via
    LineItemService._recalculate_line().

    See: readmes/topics/transactions/transactions-totals.md §1
    """
    class Meta(BaseLineCore.Meta):
        abstract = True

