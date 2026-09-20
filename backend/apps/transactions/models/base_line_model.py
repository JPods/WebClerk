"""Abstract base line model for transaction line items.
Used by QuoteLine, OrderLine, RequisitionLine, WorkOrderLine, InvoiceLine, PurchaseLine.
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
        "quote": "quote", "quote_line": "quote", "quoteline": "quote",
        "order": "order", "order_line": "order", "orderline": "order",
        "invoice": "invoice", "invoice_line": "invoice", "invoiceline": "invoice",
        "workorder": "workorder", "workorderline": "workorder", "work_order": "workorder",
        "purchase": "purchase", "purchaseline": "purchase", "purchase_line": "purchase",
        "receipt": "receipt", "receiptline": "receipt", "receipt_line": "receipt",
    }
    return aliases.get(n, n)



def default_quantity(transaction_type: str | None = None) -> Dict[str, Any]:
    """Return the canonical quantity JSONB structure for a line.

    quantity.active is the verb of the document:
      - quote_line:   quantity being proposed
      - order_line:      quantity being ordered
      - invoice_line:    quantity being shipped
      - purchase_line:   quantity being purchased
      - receipt_line:    quantity being received
      - workorder_line:  quantity being produced

    The same three keys carry every document type:
      - active:     the quantity this line is acting on (the verb)
      - remaining:  active minus what has transferred downstream
      - staged:     quantity committed from upstream (= active for standalone)

    Controls:
      - is_fixed:   whether quantity is locked from editing
      - precision:  decimal places for quantity math
      - is_blanket: blanket/open-ended quantity (optional)
      - increment:  minimum order increment (optional), used the blanket order fulfillment

    Quantity flow for standalone lines (no parent):
      All types: active=10 → staged=10, remaining=10

    Parent-child (quote_line -> order_line, order_line -> invoice_line only):
      child.parent_line_id = parent line pk, set at creation
      parent.remaining     = parent.active − Σ children.active   (recomputed, never decremented)

      Example: Order(active=10) → Invoice(active=6) → Order remaining = 4
               The 6 on the invoice IS the shipped quantity.

    Full definitions: readmes/transactions/line-quantity.md

    There is no 'shipped' or 'picked' key. Shipped quantity is
    invoice_line.quantity.active. Remaining to ship is order_line.quantity.remaining.
    The document type gives the quantity its meaning.

    Legacy keys (ordered, invoiced, received, placed, actioned, processing, etc.) are DEPRECATED.
    Transfer services should read/write staged/active/remaining only.
    """
    # All known types share the same canonical structure.
    # normalize_quantity_map() fills the staged snapshot on creation and
    # computes remaining. See readmes/transactions/line-quantity.md.
    _KNOWN_KINDS = {
        "quote", "order", "invoice", "purchase", "workorder", "receipt",
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


def normalize_quantity_map(
    q: Dict[str, Any] | None,
    transaction_type: str | None = None,
    *,
    children_sum: float | None = None,
    is_new: bool = False,
) -> Dict[str, Any]:
    """Normalize a quantity JSON blob to the canonical structure.

    This is the ONE writer of quantity.remaining.
    Definitions: readmes/transactions/line-quantity.md

      active    — the verb of the document; the only quantity any calculation reads
      staged    — snapshot at creation; filled from active only when is_new and absent
      remaining — active − children_sum; signed, never floored; 0 when is_complete

    children_sum is the sum of child lines' active (see services/line_parent.py).
    None means this line has no child line model; remaining = active.

    Quantities are signed. Unknown keys (children_active, parent_active,
    parent_remaining, converted_from_*, legacy keys) are dropped.
    """
    base = default_quantity(transaction_type)
    src = q if isinstance(q, dict) else {}
    out = dict(base)

    for key in ("staged", "active"):
        if src.get(key) is not None:
            try:
                out[key] = float(src[key])
            except (TypeError, ValueError):
                out[key] = 0
        elif out.get(key) is None:
            out[key] = 0

    if "is_fixed" in src:
        out["is_fixed"] = bool(src["is_fixed"])
    if "precision" in src:
        try:
            out["precision"] = int(src["precision"])
        except (TypeError, ValueError):
            pass
    if "is_complete" in src:
        out["is_complete"] = bool(src["is_complete"])
    if "is_blanket" in src:
        out["is_blanket"] = bool(src["is_blanket"])
    if "increment" in src:
        try:
            out["increment"] = float(src["increment"]) if src["increment"] is not None else 0
        except (TypeError, ValueError):
            out["increment"] = 0

    # staged is a snapshot taken once, at creation. An existing line keeps
    # whatever staged it has; edits to active never move it.
    if is_new and src.get("staged") is None:
        out["staged"] = out["active"]

    precision = out.get("precision", 2)
    active = out.get("active", 0) or 0
    consumed = float(children_sum or 0)
    out["remaining"] = float(_to_decimal(active - consumed, places=precision))
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
        "discount_amount": 0.0,     # a flat dollar discount on the line (used only when no percent)
        "is_fixed": False,
        "precision": 2,
    }

from common.decimals import safe_decimal as _to_decimal  # noqa: E302

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
        for key, places in (("unit", prec), ("discount_amount", prec)):
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


# ---------------------------------------------------------------------------
# Shared line behaviour: how a line moves inventory
# ---------------------------------------------------------------------------
# Every transaction line does the same thing to inventory — it moves quantity
# into exactly one bucket, chosen by its transaction type. That rule was written
# out longhand in each of the pending builders in services/line_manage.py, three
# times in three different shapes. The copies drifted: a fix to the quote
# probability guard in the line-add builder left the quantity-change and delete
# builders still zeroing on_qt, so editing or deleting a quote line silently
# wrote a zero. One rule, one place.

#: pending type code -> the Item.quantity bucket that type moves.
PENDING_TYPE_BUCKET: Dict[str, str] = {
    'QT': 'on_qt',    # quote — forecast, weighted by close probability
    'SO': 'on_so',   # sales order — reserved
    'PO': 'on_po',   # purchase order — incoming
    'WO': 'on_wo',   # work order — reserved for production
    'IN': 'on_in',   # invoice — issued
    'RC': 'on_rc',    # receipt — received
}

#: every bucket a pending record carries, so callers always emit a full envelope.
QUANTITY_BUCKETS: tuple = ('on_so', 'on_po', 'on_wo', 'on_in', 'on_rc', 'on_qt', 'on_hand')

#: pending types that also move on_hand, and in which direction, on a line ADD.
#: Quantity changes and deletes do not touch on_hand.
ON_HAND_DIRECTION: Dict[str, int] = {'IN': -1, 'RC': 1}


def forecast_probability(transaction: Any) -> float:
    """Close probability for a quote, as a 0.0-1.0 multiplier.

    Quote.probability is a FloatField defaulting to 0.0, so an untouched
    quote cannot be told apart from a deliberate 0%. Treating that default as
    a real probability multiplied every quote line's forecast by zero. Zero
    means "not set" here and yields 1.0.

    Accepts either scale: a stored value above 1.0 is read as a percentage.
    """
    prob_raw = getattr(transaction, 'probability', None)
    if prob_raw is None:
        metadata = getattr(transaction, 'metadata', None)
        if isinstance(metadata, dict):
            prob_raw = metadata.get('probability')
    if not prob_raw:
        return 1.0
    try:
        value = float(prob_raw)
    except (TypeError, ValueError):
        return 1.0
    if value > 1.0:
        value = value / 100.0
    return value if value > 0 else 1.0


def quantity_bucket_deltas(
    pending_type: str,
    quantity: Any,
    transaction: Any = None,
    *,
    affect_on_hand: bool = False,
) -> Dict[str, float]:
    """Build the full bucket envelope for one pending record.

    `quantity` is signed by the caller: positive to commit, negative to release.

    affect_on_hand is True only for a line ADD, where an invoice also decrements
    on_hand and a receipt increments it. Quantity changes and deletes leave
    on_hand alone, which is why this is a parameter rather than a lookup.
    """
    deltas: Dict[str, float] = {bucket: 0 for bucket in QUANTITY_BUCKETS}
    bucket = PENDING_TYPE_BUCKET.get(pending_type)
    if bucket is None:
        return deltas

    qty = float(quantity or 0)
    if pending_type == 'QT':
        qty = qty * forecast_probability(transaction)
    if pending_type == 'WO' and getattr(transaction, 'kind', '') == 'count':
        # A count is an audit, not work: it reserves nothing. What it finds reaches
        # on_hand when the line is completed (Bill, 2026-09-20).
        return deltas
    deltas[bucket] = qty

    if affect_on_hand and pending_type in ON_HAND_DIRECTION:
        deltas['on_hand'] = abs(float(quantity or 0)) * ON_HAND_DIRECTION[pending_type]
        if float(quantity or 0) < 0:
            deltas['on_hand'] = -deltas['on_hand']
    return deltas


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

    # Line type — controls how this line's amount routes in totals.
    #   product    (default) → adds to subtotal, taxed at header rate
    #   commission → rep line — invoiced to manufacturer for commission, not to customer
    #   tax        → adds to tax total (environmental fee, recycling, bottle deposit)
    #   shipping   → adds to shipping total (freight line, handling charge)
    #   discount   → subtracts from subtotal
    # No VAT mechanism at this time — US sales tax model only.
    LINE_TYPE_CHOICES = [
        ('product', 'Product'),
        ('commission', 'Commission'),
        ('tax', 'Tax'),
        ('shipping', 'Shipping'),
        ('discount', 'Discount'),
        ('finance_charge', 'Finance Charge'),  # interest on past-due balance → totals.finance_charge
    ]
    line_type = models.CharField(max_length=20, choices=LINE_TYPE_CHOICES, default='product', db_index=True)

    price_level = models.CharField(max_length=50, blank=True, null=True, db_column="price_level")
    # status inherited from BaseModel

    # FK-first: proper ForeignKey to Item for referential integrity.
    # The `item` JSONField below holds denormalized item details (description, etc.)
    # for fast reads; the FK is the source of truth for the relationship.
    item_fk = models.ForeignKey(
        'products.Item', on_delete=models.PROTECT,
        blank=True, null=True,
        db_column='item_id_fk', related_name='%(class)s_lines',
    )

    # The line whose backlog this line consumes. Only order_line (parent: quote_line)
    # and invoice_line (parent: order_line) set it; the child's type names the parent table.
    # BigInt, not FK: deleting a parent line must not delete its children.
    # Named parent_line_id because parent_id on a line means the header.
    parent_line_id = models.BigIntegerField(blank=True, null=True, db_index=True)

    # Common JSON fields (do NOT redeclare action/flow/source here; provided by BaseModel mixins)
    item = models.JSONField(default=dict, blank=True, null=True)
    quantity = models.JSONField(default=dict, blank=True, null=True)
    cost = models.JSONField(default=dict, blank=True, null=True)
    commission = models.JSONField(default=dict, blank=True, null=True)
    tax = models.JSONField(default=dict, blank=True, null=True)
    physical = models.JSONField(default=dict, blank=True, null=True)
    # Results of the line math, written only by the totals engine
    # (totals_compute.compute_totals). The header's totals.X = Σ line totals.X.
    totals = models.JSONField(default=dict, blank=True, null=True)

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
            children_sum=getattr(self, "_children_sum", None),
            is_new=self._state.adding,
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

        # Results (amount, discount, tax, cost, margin, total) are not computed here:
        # the totals engine writes them to line.totals (totals_compute.compute_totals).

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # Loaded state, so a save can tell whether this line's parent must recompute.
        # Read only fields this query loaded: touching a deferred field here loads it,
        # which calls from_db again.
        loaded = instance.__dict__
        if 'parent_line_id' in loaded and 'quantity' in loaded:
            instance._loaded_parent_line_id = loaded['parent_line_id']
            quantity = loaded['quantity']
            instance._loaded_active = quantity.get('active') if isinstance(quantity, dict) else None
        return instance

    def save(self, *args, **kwargs):
        """Save with JSON normalization and auto line_number assignment.

        1. parent_line_id is taken from refs.source when a child line is created.
        2. ensure_json_defaults() seeds/normalizes all JSON envelopes; a parent-type
           line passes its children's active sum so remaining is computed here.
        3. If line_number is still 0 and a parent header exists,
           auto-assign from parent.line_increment and bump increment.
        """
        from apps.transactions.services import line_parent

        self._assert_not_fixed()
        self._assert_parent_not_journalized()

        if self._state.adding and self.parent_line_id is None:
            self.parent_line_id = line_parent.parent_line_id_from_refs(self)
        if self._state.adding:
            line_parent.prorate_flat_discount(self)

        self._children_sum = line_parent.children_active_sum(self)
        self.ensure_json_defaults()
        status_changed = line_parent.apply_transferred_status(self)

        update_fields = kwargs.get('update_fields')
        if status_changed and update_fields is not None and 'status' not in update_fields:
            kwargs['update_fields'] = list(update_fields) + ['status']

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

    def _assert_parent_not_journalized(self) -> None:
        """A journalized document's contributing values are locked: its lines' quantity,
        price and cost cannot change. Comments and operational fields stay open
        (Bill, 2026-09-17)."""
        if self._state.adding or self.pk is None:
            return
        try:
            header = self.parent
        except Exception:
            return
        if header is None or not getattr(header, 'is_locked', False):
            return
        fields = ('quantity', 'price', 'cost')
        stored = type(self).objects.filter(pk=self.pk).values(
            *[f for f in fields if hasattr(self, f)]).first()
        if not stored:
            return
        changed = sorted(f for f, was in stored.items()
                         if _envelope_changed(was or {}, getattr(self, f, None) or {}))
        if changed:
            raise JournalizedLineError(self.pk, changed)

    # ── is_fixed ────────────────────────────────────────────────────────────
    FIXED_RATE_KEYS = ('unit', 'unit_base', 'discount_percent', 'discount_amount')

    def _assert_not_fixed(self) -> None:
        """quantity.is_fixed: the price and cost of this line cannot be changed
        (Bill, 2026-09-17). Quantity may still move; the rates may not.

        Enforced on the model so every path obeys it — /save, wcapi, manage actions,
        conversions and the admin alike.
        """
        if self._state.adding or self.pk is None:
            return
        quantity = self.quantity if isinstance(self.quantity, dict) else {}
        if not quantity.get('is_fixed'):
            return
        stored = type(self).objects.filter(pk=self.pk).values('price', 'cost').first() \
            if hasattr(self, 'price') else type(self).objects.filter(pk=self.pk).values('cost').first()
        if not stored:
            return
        for envelope in ('price', 'cost'):
            if envelope not in stored:
                continue
            was = stored.get(envelope) or {}
            now = getattr(self, envelope, None) or {}
            changed = [k for k in self.FIXED_RATE_KEYS
                       if k in was or k in now
                       if _num(was.get(k)) != _num(now.get(k))]
            if changed:
                raise FixedLineError(self.pk, envelope, changed)


class JournalizedLineError(ValueError):
    """An attempt to change a value that feeds a journalized document's totals."""

    def __init__(self, line_id, envelopes):
        self.envelopes = list(envelopes)
        super().__init__(
            f"line {line_id} belongs to a journalized document: {', '.join(self.envelopes)} "
            f"cannot change. Reverse the journal entry first. Comments, cash and operational "
            f"fields are not locked.")


def _envelope_changed(was: dict, now: dict) -> bool:
    keys = set(was) | set(now)
    return any(_num(was.get(k)) != _num(now.get(k)) for k in keys
               if isinstance(was.get(k, 0), (int, float, type(None)))
               and isinstance(now.get(k, 0), (int, float, type(None))))


class FixedLineError(ValueError):
    """An attempt to change the price or cost of a fixed line."""

    def __init__(self, line_id, envelope: str, keys):
        self.line_id, self.envelope, self.keys = line_id, envelope, list(keys)
        super().__init__(
            f"line {line_id} is fixed: {envelope}.{', '.join(self.keys)} cannot be changed. "
            f"Clear quantity.is_fixed first, or change the quantity instead.")


def _num(value) -> float:
    try:
        return round(float(value or 0), 6)
    except (TypeError, ValueError):
        return 0.0


class BaseSellLineModel(BaseLineCore):
    """Sell-side line base for Quote, Order, Invoice.

    Adds the ``price`` JSON envelope: inputs only (unit, discount_percent, a flat
    discount_amount, precision). The results — the discounted unit, amount,
    discount, tax, cost, margin, total — are written to line.totals by the totals
    engine (totals_compute.compute_totals). One source of truth.
    """
    price = models.JSONField(default=dict, blank=True, null=True)

    class Meta(BaseLineCore.Meta):
        abstract = True

    JSON_DEFAULT_FACTORIES = dict(BaseLineCore.JSON_DEFAULT_FACTORIES, price=default_price)

    def ensure_json_defaults(self) -> None:
        """Extends BaseLineCore: also normalizes price."""
        super().ensure_json_defaults()
        self.price = normalize_price_map(getattr(self, "price", None))


class BaseExecLineModel(BaseLineCore):
    """Exec-side line base for Purchase, WorkOrder, Receipt.

    No price envelope — exec lines track cost only.
    Auto-computes cost.extended on save via BaseLineCore._calculate_extended_cost()
    (runs in ensure_json_defaults). Single source of truth — same computation
    used by BaseSellLineModel for the cost side.

    See: readmes/topics/transactions/transactions-totals.md §1
    """
    class Meta(BaseLineCore.Meta):
        abstract = True

