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
        "order": "order", "order_line": "order", "orderline": "order",
        "invoice": "invoice", "invoice_line": "invoice", "invoiceline": "invoice",
        "workorder": "workorder", "workorderline": "workorder", "work_order": "workorder",
        "purchase": "purchase", "purchaseline": "purchase", "purchase_line": "purchase",
        "receipt": "receipt", "receiptline": "receipt", "receipt_line": "receipt",
    }
    return aliases.get(n, n)



def default_quantity(transaction_type: str | None = None) -> Dict[str, Any]:
    """Return the canonical quantity JSONB structure for a line.

    Canonical keys (all transaction types):
      - staged:     quantity committed on this line (= active for standalone)
      - active:     user-entered quantity (always the primary input)
      - remaining:  uncommitted inventory available for downstream transfer
      - is_fixed:   whether quantity is locked from editing
      - precision:  decimal places for quantity math
      - is_blanket: blanket/open-ended quantity (optional)
      - increment:  minimum order increment (optional)

    Quantity flow for standalone lines (no parent):
      All types: active=10 → staged=10, remaining=10

    Transfer semantics (how inventory responsibility moves):
      target.staged = transfer_qty  (taken from source.remaining)
      source.remaining -= transfer_qty
      
      Example: Order(remaining=10) → Invoice(staged=6)
               Order remaining becomes 10-6=4

    Legacy keys (ordered, invoiced, received, placed, actioned, processing, etc.) are DEPRECATED.
    Transfer services should read/write staged/active/remaining only.

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    # All known types share the same canonical structure.
    # normalize_quantity_map() handles standalone mirroring (staged=active)
    # and remaining calculation at normalisation time.
    _KNOWN_KINDS = {
        "proposal", "order", "invoice", "purchase", "workorder", "receipt",
    }
    kind = _normalize_line_kind(transaction_type)
    if kind in _KNOWN_KINDS:
        return {
            "staged": 0,
            "active": 0,
            "remaining": 0,
            "is_fixed": False,
            "is_complete": False,
            "precision": 2,
            "is_blanket": False,
            "increment": 0,
        }
    # Unknown type — use None sentinels so callers can detect missing data
    return {
        "staged": None,
        "active": None,
        "remaining": None,
        "is_fixed": False,
        "precision": 2,
    }


def normalize_quantity_map(q: Dict[str, Any] | None, transaction_type: str | None = None) -> Dict[str, Any]:
    """Normalize a quantity JSON blob to the canonical structure.

    Handles:
      1. None / empty → full default from default_quantity()
      2. Null numeric values → 0
      3. Missing canonical keys → backfilled from defaults
      4. Standalone mirroring: if active set but staged is 0, staged = active
      5. Remaining calculation varies by context (see below)

    Quantity Semantics:
      The user always enters 'active' as the primary quantity input.
      
      staged  — allocated FROM parent (frozen at transfer); mirrors active for standalone
      active  — user input (what this line is actually for)
      remaining — available FOR children = active − sum(children.active)
      
      Without children (the common case at normalize time):
        remaining = active
      
      With children (children_active tracker present):
        remaining = active − children_active["sum"]
    """
    base = default_quantity(transaction_type)

    if not isinstance(q, dict) or not q:
        return base

    out = dict(base)  # start from full default

    # Overlay explicit canonical keys from input
    for key in ("staged", "active", "remaining"):
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
    if "is_complete" in q:
        out["is_complete"] = bool(q["is_complete"])
    if "is_blanket" in q:
        out["is_blanket"] = bool(q["is_blanket"])
    if "increment" in q:
        try:
            out["increment"] = float(q["increment"]) if q["increment"] is not None else 0
        except (TypeError, ValueError):
            out["increment"] = 0

    # ── Preserve children_active tracker (set by transaction_save) ───
    if "children_active" in q and isinstance(q["children_active"], dict):
        out["children_active"] = q["children_active"]

    # ── Standalone detection: mirror staged = active ─────────────────
    # When user enters active (standalone entry) and staged was not
    # explicitly provided, mirror staged = active.
    staged_val = out.get("staged", 0) or 0
    active_val = out.get("active", 0) or 0
    
    if active_val and not staged_val:
        # Standalone entry: user provided active, mirror to staged
        out["staged"] = active_val
        staged_val = active_val

    # ── Remaining calculation (all transaction types) ────────────────
    # remaining = active − sum(children.active)
    # At normalize time, children_active may not be present, so
    # remaining defaults to active (no children consumed yet).
    active = out.get("active", 0) or 0
    precision = out.get("precision", 2)
    
    children_active = out.get("children_active")
    if children_active and isinstance(children_active, dict):
        children_sum = float(children_active.get("sum", 0) or 0)
        out["remaining"] = float(_to_decimal(active - children_sum, places=precision))
    else:
        # No children yet: full active qty available for downstream
        out["remaining"] = float(_to_decimal(active, places=precision))

    # ── is_complete: cancel backlog ─────────────────────────────────
    # When marked complete, remaining is forced to 0 — backlog cancelled.
    if out.get("is_complete"):
        out["remaining"] = 0

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
    commission = models.JSONField(default=dict, blank=True, null=True)
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
          2. Snapshot submitted quantity for AI audit
          3. Normalize quantity via normalize_quantity_map() — always runs
             (maps legacy keys like 'ordered' → 'staged', fills missing keys,
             fixes nulls, recalculates remaining)
          4. AI audit: compare submitted vs normalized quantity
          5. Normalize cost via normalize_cost_map() — always runs

        BaseSellLineModel overrides this to also normalize price and
        compute extended values.

        See: readmes/topics/transactions/transactions-totals.md §1
        """
        # Step 1: initialize configured JSON clusters from factory defaults
        for field_name, factory in self.JSON_DEFAULT_FACTORIES.items():
            val = getattr(self, field_name, None)
            if not val:
                setattr(self, field_name, factory())

        # Step 2: snapshot submitted quantity before normalization (AI audit)
        submitted_qty = None
        raw_qty = getattr(self, "quantity", None)
        if isinstance(raw_qty, dict) and raw_qty:
            submitted_qty = dict(raw_qty)  # shallow copy

        # Step 3: normalize quantity (maps legacy keys, fills missing, fixes nulls)
        self.quantity = normalize_quantity_map(
            getattr(self, "quantity", None),
            transaction_type=self._meta.model_name,
        )

        # Step 4: AI audit — compare submitted vs normalized quantity
        if submitted_qty:
            try:
                from apps.accounts.services.ai_audit import check_quantity
                check_quantity(self, submitted_qty)
            except Exception:
                pass  # never break save for audit

        # Step 5: normalize cost strictly (fixes nulls, ensures all keys)
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
      price.extended = (quantity.staged × price.unit) − discount_amount
      cost.extended  = (quantity.staged × cost.unit)  − discount_amount

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
        """Compute price.extended and cost.extended from quantity.staged (or active).

        Formula for both price and cost envelopes:
          gross = quantity.staged × unit
          discount_amount = explicit value if set, else gross × (discount_percent / 100)
          extended = gross − discount_amount

        AI Audit: captures r25-submitted extended values before recalculating,
        then compares.  Discrepancies are logged and persisted to the Audit
        table via apps.accounts.services.ai_audit.

        This is the line-level calculation that feeds into header totals
        rollup via compute_*_sell_cost_totals() services.

        See: readmes/topics/transactions/transactions-totals.md §1
        """
        # ── Snapshot r25-submitted values BEFORE recalculating ────────
        submitted_price_ext = (
            self.price.get("extended") if isinstance(self.price, dict) else None
        )
        submitted_cost_ext = (
            self.cost.get("extended") if isinstance(self.cost, dict) else None
        )

        # quantity.staged (or active) drives both price and cost extended calculations
        quantity = self.quantity.get("staged", 0) or self.quantity.get("active", 0) if self.quantity else 0

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

        # ── AI Audit: compare r25 submission vs wc3 recalculation ────
        try:
            from apps.accounts.services.ai_audit import check_extended_prices
            check_extended_prices(self, submitted_price_ext, submitted_cost_ext)
        except Exception:
            pass  # never break save for audit


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

