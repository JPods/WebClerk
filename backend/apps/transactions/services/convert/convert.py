"""
Document Conversion Chain — the fundamental commerce workflow.

    Quote → Order → Invoice → Cash
                Order → Purchase (procurement / drop-ship)
    Quote → Invoice (over-the-counter, skip order)

The one conversion engine (Bill, 2026-09-24: convert is a command,
``POST /wcapi/<source>/<id>/convert/`` {to, line_ids?, vendor_id?, contact_id?}). There were
four: this one, the endpoint wrappers (transfer_*), convert_engine.execute_transfer (lines
written outside the door) and transaction_flow.order_to_purchase (a raw copy). Plan: Allie
readmes/assessments/2026-09-24-one-route-per-verb.md §14, §14a.

The target is saved through the save door as the caller — their create rights and scope
decide, the target's own hooks run — with its header built here from the source and passed
as ``server_set``, so a role that may not type lineage, tax setup or commission still
carries them forward. The target is saved WITH its lines in the same unit: everything the
source has left, or the lines the caller names (``lines: [{line_id, qty?}]``, as shipping does).
Bill, 2026-11-08: "Save with lines" — the person reviews and edits a saved planned document, so
nothing is lost by navigating away; this replaces his 2026-09-27 "review before save" for
conversions (an unsaved review left a header-only purchase, 1028-po, and re-seeded stale lines
onto a saved invoice, 1056-inv). A purchase born without a vendor is saved and coached: pick a
vendor before release (validate_status refuses the release until then).

Design rules (from Bill):
  1. Commission populates at the earliest chain point and flows forward.
     Never recalculated downstream unless manually overridden.
  2. Lines copy forward with ALL their data.
  3. parent_id / parent_model link child to parent.
  4. Partial conversions are supported (convert N of M lines).
  5. Source transaction status updates after conversion.
  6. All inventory changes go through Pending — no direct writes to item.quantity.
"""
from __future__ import annotations

import copy
import logging
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db import transaction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fields copied from source header to target header (sell-side: quote→order→invoice)
# Customer data transfers — same party through the sell chain.
_HEADER_COPY_FIELDS_SELL = (
    "customer", "customer_id", "contact_id",
    "company", "attention", "ship_via",
    # The rep travels with the sale: quote → order → invoice (Bill, 2026-09-23).
    "rep_id", "attention_rep",
    # Party blocks shown in bill_to / ship_to. The JSON aspects are the source
    # of truth; address_full/email/phone are read-only properties derived from them.
    "addresses", "emails", "phones",
    "price_level", "terms",
    # How the sale came in and when it is needed travel with it (Bill, 2026-11-06: source_name
    # did not track from the quote to the order).
    "source_name", "priority", "dt_needed",
    "is_commission", "conditions_id", "conditions_description",
    # Tax jurisdiction and rate: the same sale is taxed the same way at every step.
    "finance",
    "config", "source",
)

# Fields copied for buy-side (order→purchase, order→workorder)
# Customer does NOT transfer — purchase/workorder are vendor-side.
# Only item references and basic config carry forward.
_HEADER_COPY_FIELDS_BUY = (
    "config", "source",
    # A receipt is from its purchase's vendor and carries its need; an order has no vendor_id, so
    # order → purchase copies nothing here and the person names the vendor on the saved purchase.
    "vendor_id", "source_name", "priority", "dt_needed",
)

# Fields copied from source line to target line (sell-side)
_SELL_LINE_COPY_FIELDS = (
    "line_type", "item", "item_fk_id", "price", "cost", "commission",
    "tax", "physical", "price_level", "status",
)

# Fields copied for exec-side (purchase) lines — no price
_EXEC_LINE_COPY_FIELDS = (
    "item", "item_fk_id", "cost", "commission",
    "tax", "physical", "price_level", "status",
)


class ConversionError(Exception):
    """Business-rule violation during document conversion."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_model(model_name: str):
    """Resolve a transaction model by lowercase name."""
    name_map = {
        "quote": "Quote",
        "order": "Order",
        "invoice": "Invoice",
        "purchase": "Purchase",
        "cash": "Cash",
    }
    cls_name = name_map.get(model_name)
    if not cls_name:
        raise ConversionError(f"Unknown model: {model_name}")
    return dj_apps.get_model("transactions", cls_name)


def _get_line_model(model_name: str):
    """Resolve a transaction line model by lowercase name."""
    name_map = {
        "quote": "QuoteLine",
        "order": "OrderLine",
        "invoice": "InvoiceLine",
        "purchase": "PurchaseLine",
    }
    cls_name = name_map.get(model_name)
    if not cls_name:
        raise ConversionError(f"Unknown line model: {model_name}")
    return dj_apps.get_model("transactions", cls_name)


def _get_line_fk_field(model_name: str) -> str:
    """Return the FK field name on the line model that points to the header."""
    return model_name  # quote, order, invoice, purchase


def _get_lines(header, model_name: str, line_ids: Optional[List[int]] = None):
    """Select lines from a header, optionally filtered by IDs."""
    LineModel = _get_line_model(model_name)
    fk_field = _get_line_fk_field(model_name)
    qs = LineModel.objects.select_for_update().filter(**{fk_field: header})

    if line_ids is not None:
        qs = qs.filter(id__in=line_ids)
        found_ids = set(qs.values_list("id", flat=True))
        missing = [i for i in line_ids if i not in found_ids]
        if missing:
            raise ConversionError(f"Line IDs not found on {model_name}: {missing}")

    lines = list(qs)
    if not lines:
        raise ConversionError(f"No lines to convert on {model_name} #{header.pk}")
    return lines


def _carry_document_discount(source, target) -> None:
    """A document discount travels to the next document as a percent (design v2):
    a percent as is; a dollar discount as its share of the source's amount, so a
    partial conversion gets its proportion. Shipping and other do not carry."""
    alloc = getattr(source, "allocations", None) or {}
    pct = Decimal(str(alloc.get("discount_percent") or 0))
    amt = Decimal(str(alloc.get("discount_amount") or 0))
    if amt:
        gross = Decimal(str((getattr(source, "totals", None) or {}).get("amount") or 0)) + amt
        if gross > 0:
            pct = max(pct, (amt / gross * 100).quantize(Decimal("0.000001")))
    if pct:
        target.allocations = {**(getattr(target, "allocations", None) or {}), "discount_percent": float(pct)}


def _item_unit_cost_for_line(src_line) -> Decimal:
    """The line's item cost — the one buy-side costing behavior (resolve_cost)."""
    from apps.products.services.price_resolver import resolve_cost
    item = getattr(src_line, "item_fk", None)
    return resolve_cost(item).unit if item else Decimal("0")


def _copy_commission(source_commission: Optional[dict]) -> dict:
    """Copy commission forward — never recalculate, preserve overrides."""
    if not source_commission or not isinstance(source_commission, dict):
        return {}
    # Deep copy to avoid mutation
    import copy
    comm = copy.deepcopy(source_commission)
    # Reset accrual state — accrual happens on invoice journalize
    comm["accrued"] = False
    comm["dt_accrued"] = 0
    return comm


def _refuse(code: str, message: str, details=None):
    from apps.core.services.door import Refused
    return Refused(400, code, message, details)


#: (source, target) → sell side? The pairs this engine converts.
PAIRS = {
    ("quote", "order"): True,
    ("quote", "invoice"): True,
    ("order", "invoice"): True,
    ("order", "purchase"): False,
    # Receiving is a convert, like order→invoice (Bill, 2026-09-27, R3).
    ("purchase", "receipt"): False,
}


def _header(source, source_type: str, target_type: str, is_sell_side: bool,
            contact_id=None, vendor_id=None) -> Dict[str, Any]:
    """The target's header, built from the source — what the server authors."""
    header: Dict[str, Any] = {"status": "planned", "parent_id": source.pk,
                              "parent_model": source_type}
    for field in (_HEADER_COPY_FIELDS_SELL if is_sell_side else _HEADER_COPY_FIELDS_BUY):
        if field == "customer":
            continue                                   # the id travels, not the instance
        val = getattr(source, field, None)
        if val is not None:
            header[field] = copy.deepcopy(val) if isinstance(val, (dict, list)) else val
    if is_sell_side:
        probe = type("Probe", (), {"allocations": {}})()
        _carry_document_discount(source, probe)
        if probe.allocations:
            header["allocations"] = probe.allocations
    commission = getattr(source, "commission", None)
    if commission:
        header["commission"] = _copy_commission(commission)
    if contact_id is not None:
        header["contact_id"] = contact_id
    if vendor_id is not None:
        header["vendor_id"] = vendor_id
    if source_type == "purchase" and target_type == "receipt":
        # The receipt's vendor block is its purchase's, as it stood (readme 109): a snapshot,
        # not the vendor's values of today. The party fill leaves an aspect the payload carries.
        for aspect in ("addresses", "emails", "phones"):
            block = (getattr(source, aspect, None) or {}).get("vendor")
            if block:
                header[aspect] = {"vendor": copy.deepcopy(block)}
    header["refs"] = {**copy.deepcopy(header.get("refs") or {}),
                      "source": {"converted_from": source_type, f"{source_type}_id": source.pk}}
    return header


def _target_lines(source_lines, source_type: str, target_type: str,
                  is_sell_side: bool) -> List[Dict[str, Any]]:
    """The target's lines, built from the source's: what the target is saved with."""
    from apps.core.services.door import resolve_model
    line_model = resolve_model(target_type)[0].lines.rel.related_model
    target_fields = {f.name for f in line_model._meta.get_fields()} | {
        f.attname for f in line_model._meta.concrete_fields}
    lines = []
    for src_line in source_lines:
        src_qty = getattr(src_line, "quantity", None) or {}
        remaining = float(src_qty.get("remaining", 0) or 0)
        if target_type == "receipt":
            # Goods stay on order until received, so the purchase line's remaining counts only
            # what was received; what open receipts already plan is not left to plan again.
            remaining = round(remaining - planned_not_received(src_line), 6)
        # What is left goes, a credit line (a negative quantity) included (Bill, 2026-11-13). A
        # line received or invoiced past its quantity has a remaining of the other sign: that is
        # not something left to convert.
        ordered = float(src_qty.get("active", 0) or 0)
        if remaining == 0 or (remaining > 0) != (ordered > 0):
            continue
        # A document discount line moved into allocations; it travels there, not as a line.
        if isinstance(getattr(src_line, "metadata", None), dict) and src_line.metadata.get("document_discount"):
            continue
        target_qty = {"active": remaining, "staged": remaining, "remaining": remaining}
        for key in ("precision", "is_fixed"):
            if key in src_qty:
                target_qty[key] = src_qty[key]
        cost = copy.deepcopy(getattr(src_line, "cost", None) or {})
        if target_type == "purchase":
            # A purchase is what we pay the vendor: the item's cost at the company default,
            # never the sell line's estimate.
            cost["unit"] = float(_item_unit_cost_for_line(src_line))
        # A receipt keeps the purchase line's whole cost: what was bought is what lands on the
        # layer (Bill, 2026-09-27). Copied once; the two costs are independent after that.
        line = {
            "line_number": getattr(src_line, "line_number", 0) or 0,
            # A discount line stays a discount line; as a product it adds instead of subtracts.
            "line_type": getattr(src_line, "line_type", None) or "product",
            "item": getattr(src_line, "item", None) or {},
            "quantity": target_qty,
            "price": getattr(src_line, "price", None) or {},
            "cost": cost,
            "price_level": getattr(src_line, "price_level", "") or "",
            "status": "",
            "is_active": True,
            "refs": {"source": {f"{source_type}_line_id": src_line.pk}},
            "_dirty": True,
        }
        # Carried forward when they hold something. An empty container names no leaf, and the
        # door offers it as a bare path that no role grants (a person's convert was refused).
        carried = {
            "comments": getattr(src_line, "comments", None),
            "config": getattr(src_line, "config", None),
            "commission": _copy_commission(getattr(src_line, "commission", None)),
        }
        line.update({key: value for key, value in carried.items() if value})
        from apps.transactions.services import line_contacts
        if f'{target_type}line' in line_contacts.LINE_DOCUMENTS and line_contacts.is_on(target_type):
            people = line_contacts.carried(src_line)       # the warranty holder goes with the line
            if people:
                line["refs"]["contacts"] = people
        if target_type == "receipt":
            from apps.transactions.services.line_door import _stock_warehouse
            # A receipt line declares no price, commission, comments, config or refs.source:
            # parent_line_id is its one link, and the purchase line's remaining follows it.
            for key in ("price", "commission", "comments", "config", "refs"):
                line.pop(key, None)
            line["parent_line_id"] = src_line.pk
            # The default warehouse while the warehouse feature is set aside (action 31277).
            line["warehouse_id"] = _stock_warehouse(src_line)
        # Only what the target's line declares: a purchase line has no price, and the door
        # refuses a path no line has (order → purchase failed on lines.price.*, 2026-10-25).
        lines.append({k: v for k, v in line.items() if k.startswith("_") or k in target_fields})
    return lines


def _fill_from_stock(lines: List[dict]) -> tuple:
    """Order → invoice (Bill, 2026-11-13): each line invoices what the order has left, up to what
    the item has in stock; the rest stays on the order line. Stock is counted down in line order,
    so two lines of one item do not both take it. A credit line (a negative quantity) and a line
    whose item holds no stock (labor, freight) go whole. The invoice line keeps what was asked
    as ``staged`` and what ships as ``active``; ``staged − active`` is what did not ship.

    Returns (the lines to save, [(label, asked, shipped)] for each line that ships short).
    """
    from apps.products.models import Item
    from apps.transactions.behaviours import stock_available
    from apps.transactions.services.line_door import _is_tracked

    def item_id_of(line):
        item = line.get("item") or {}
        return item.get("id") or item.get("item_id")

    ids = {int(item_id_of(line)) for line in lines if item_id_of(line)}
    items = {i.pk: i for i in Item.objects.select_for_update().filter(pk__in=ids)}
    left = {pk: max(stock_available(item), 0.0) for pk, item in items.items() if _is_tracked(pk)}

    kept, short = [], []
    for line in lines:
        quantity = line.get("quantity") or {}
        asked = float(quantity.get("active") or 0)
        item_id = item_id_of(line)
        item_id = int(item_id) if item_id else None
        if asked <= 0 or item_id not in left:
            kept.append(line)
            continue
        shipped = round(min(asked, left[item_id]), 6)
        left[item_id] = round(left[item_id] - shipped, 6)
        if shipped < asked:
            item = items[item_id]
            short.append((item.sku or item.ida or str(item_id), asked, shipped))
        if shipped <= 0:
            continue
        line["quantity"] = {**quantity, "active": shipped, "staged": asked}
        kept.append(line)
    return kept, short


def planned_not_received(purchase_line) -> float:
    """What open receipts plan against this purchase line and have not received yet."""
    from apps.transactions.models import ReceiptLine
    planned = 0.0
    for q in ReceiptLine.objects.filter(parent_line_id=purchase_line.pk).values_list("quantity", flat=True):
        q = q if isinstance(q, dict) else {}
        planned += max(float(q.get("staged") or 0) - float(q.get("active") or 0), 0.0)
    return round(planned, 6)


def _take_named(lines_named, source_type: str) -> Callable[[List[dict]], List[dict]]:
    """``lines: [{line_id, qty?}]`` — the source lines affected (Bill, 2026-09-27): only those,
    each at the qty given or else at what is left. Whether a qty above what is left may stand
    is the target's rule (check_transfer refuses it for an invoice; a receipt takes it)."""
    wanted: Dict[int, Optional[float]] = {}
    for row in lines_named:
        if not isinstance(row, dict) or row.get("line_id") in (None, ""):
            raise _refuse("line_id_required", 'Each line names its "line_id".')
        qty = row.get("qty")
        if qty not in (None, ""):
            try:
                qty = float(qty)
            except (TypeError, ValueError):
                raise _refuse("bad_qty", f'Line {row["line_id"]}: "{qty}" is not a quantity.')
            if qty <= 0:
                raise _refuse("qty_not_positive",
                              f'Line {row["line_id"]}: convert a quantity above 0 ({qty:g} was asked).')
        wanted[int(row["line_id"])] = None if qty in (None, "") else qty

    def take(built_lines):
        kept = []
        for line in built_lines:
            source_line_id = (((line.get("refs") or {}).get("source") or {}).get(f"{source_type}_line_id")
                              or line.get("parent_line_id"))
            if source_line_id not in wanted:
                continue
            qty = wanted[source_line_id]
            if qty is not None:
                line["quantity"] = {**line["quantity"], "active": qty, "staged": qty,
                                      "remaining": qty}
            kept.append(line)
        return kept
    return take


@transaction.atomic
def convert_record(actor, source_type: str, source_id: int, target_type: str, *,
                   line_ids: Optional[List[int]] = None, contact_id: Optional[int] = None,
                   vendor_id: Optional[int] = None,
                   take: Optional[Callable[[List[dict]], List[dict]]] = None,
                   stamp: Optional[Dict[str, Any]] = None, hold: bool = False) -> Dict[str, Any]:
    """Convert ``source_type`` #``source_id`` to a new ``target_type``, as ``actor``.

    The target is saved once with its lines — one save, its hooks once, the transfer check in
    the same unit. Without ``take`` every line the source has left goes; with it,
    ``take(built_lines)`` names the lines to keep and their quantities (shipping, the named
    path). ``stamp`` is more of the header the server authors (a shipping record), carried
    like the rest. ``hold`` (a receipt only) saves the goods as staged, not received (R2).
    """
    from apps.core.services.save import save_record

    is_sell_side = PAIRS.get((source_type, target_type))
    if is_sell_side is None:
        raise _refuse("unknown_conversion",
                      f"A {source_type} does not convert to a {target_type}.",
                      {"conversions": sorted(f"{s}→{t}" for s, t in PAIRS if s == source_type)})

    SourceModel = _get_model(source_type)
    source = SourceModel.objects.select_for_update().filter(pk=source_id).first()
    if source is None:
        from apps.core.services.door import Refused
        raise Refused(404, "not_found", f"{source_type} {source_id} not found")
    if getattr(source, "dt_journaled", 0):
        from apps.core.services.door import Refused
        raise Refused(409, "locked", f"{source_type} {source_id} is journalized; it cannot be converted.")
    try:
        source_lines = _get_lines(source, source_type, line_ids)
    except ConversionError as e:
        raise _refuse("no_lines", str(e)) from e

    if target_type == "receipt":
        # Vendor, contact and terms inherit from the purchase on save.
        header_extra = {"source_type": "purchase_receipt"}
    else:
        header_extra = {}
    if target_type == "purchase" and vendor_id is None:
        vendor_id = getattr(source, "vendor_id", None)     # the person may set it on the saved purchase
    header = _header(source, source_type, target_type, is_sell_side, contact_id, vendor_id)
    built = _target_lines(source_lines, source_type, target_type, is_sell_side)
    if not built:
        raise _refuse("nothing_to_convert", "No convertible lines (every line has remaining 0).")

    header.update(header_extra)
    header.update(copy.deepcopy(stamp or {}))
    lines = (take or list)(copy.deepcopy(built))
    short = []
    if (source_type, target_type) == ("order", "invoice") and take is None:
        lines, short = _fill_from_stock(lines)
        if not lines:
            raise _refuse("nothing_in_stock",
                          "Nothing on this order is in stock to invoice: "
                          + ", ".join(f"{label} needs {asked:g}" for label, asked, _ in short) + ".",
                          {"short": [{"item": label, "asked": asked} for label, asked, _ in short]})
    if target_type == "receipt":
        # Saving a receipt receives the goods (Bill, 2026-11-11, R1): each line is saved with what
        # was asked as active, and its door moves on_hand / on_rc, the layer and the purchase line's
        # remaining. Hold is a positive act (R2): the goods wait as staged until Receive.
        for line in lines:
            asked = float((line.get("quantity") or {}).get("active") or 0)
            line["quantity"] = {**line["quantity"], "active": 0 if hold else asked, "staged": asked,
                                "remaining": 0}
    # The lines are the server's too, built from the source: they ride with the header past the
    # role's field filter, so a role that may convert but may not type a line's fields still
    # gets its document whole (a USER's convert was refused on lines.item.id_num, 2026-11-08).
    header["lines"] = lines
    result = save_record(actor, {}, model_key=target_type, server_set=header)

    forwarded = 0
    if (source_type, target_type) == ("order", "invoice"):
        from apps.transactions.services.cash.cash_door import relink_deposits
        forwarded = relink_deposits(source, result.obj)

    messages = list(result.messages or [])
    if short:
        messages.append("Not everything shipped. " + "; ".join(
            f"{label}: {shipped:g} of {asked:g} invoiced, {asked - shipped:g} stays on the order"
            for label, asked, shipped in short) + ".")
    if target_type == "purchase" and not getattr(result.obj, "vendor_id", None):
        # Saved all the same (Bill, 2026-11-08: never a silent empty purchase); the release
        # gate (validate_status.REQUIRES) keeps refusing until a vendor is named.
        messages.append("Pick a vendor before this purchase is released.")
    return {
        f"{target_type}_id": result.obj_id,
        f"{target_type}_ida": getattr(result.obj, "ida", ""),
        "lines_saved": len(lines),
        "cash_entries_forwarded": forwarded,
        "messages": messages,
    }


def convert_command(ctx) -> Dict[str, Any]:
    """POST /wcapi/<source>/<id>/convert/ {to, lines?: [{line_id, qty?}], vendor_id?, contact_id?, hold?}.

    ``lines`` names the source lines affected (Bill, 2026-09-27); the target is saved with
    exactly those. Without it, the target is saved with everything the source has left
    (Bill, 2026-11-08). ``hold: true`` on a receipt keeps the goods staged until Receive
    (Bill, 2026-11-11, R2: hold is a positive act); without it, saving the receipt receives them.
    """
    to = (ctx.data.get("to") or "").lower()
    if not to:
        raise _refuse("to_required", f"Name what the {ctx.model_key} converts to: {{\"to\": ...}}.")
    from apps.core.services.door import Refused
    from apps.transactions.services import validate_status
    needs = validate_status.CONVERT_REQUIRES.get(to)
    missing = validate_status.incomplete(ctx.obj, ctx.model_key, needs=needs) if needs else []
    if missing:   # a money step: the source is complete or it stays as it is (the team, 2026-11-06)
        raise Refused(409, "incomplete_document",
                      validate_status.incomplete_coaching(ctx.model_key, f"convert to {to}", missing, needs),
                      {"missing": missing})
    named = ctx.data.get("lines")
    line_ids, take = None, None
    if named is not None:
        if not isinstance(named, list) or not named:
            raise _refuse("lines_required", 'Name the lines affected: "lines": [{"line_id", "qty"?}].')
        take = _take_named(named, ctx.model_key)
        line_ids = [int(row["line_id"]) for row in named]
    return convert_record(ctx.actor, ctx.model_key, ctx.obj.pk, to,
                          line_ids=line_ids, contact_id=ctx.data.get("contact_id"),
                          vendor_id=ctx.data.get("vendor_id"), take=take,
                          hold=_hold(ctx.data.get("hold"), to))


def _hold(value, to: str) -> bool:
    """``hold`` is a yes or a no, and only a receipt holds goods."""
    if value in (None, False, ""):
        return False
    if value is not True:
        raise _refuse("bad_hold", f'"hold" is true or false ({value!r} was sent).')
    if to != "receipt":
        raise _refuse("hold_not_receipt", f"Only a receipt holds goods; a {to} has nothing to hold.")
    return True


def _system(source="convert"):
    from apps.core.services.door import Actor
    return Actor.system(source=source)


# ---------------------------------------------------------------------------
# The engine as services call it (training, simulations, tests): the system actor.
# ---------------------------------------------------------------------------

def convert_quote_to_order(quote_id: int, line_ids: Optional[List[int]] = None,
                           contact_id: Optional[int] = None) -> Dict[str, Any]:
    return convert_record(_system(), "quote", quote_id, "order", line_ids=line_ids,
                          contact_id=contact_id)


def convert_order_to_invoice(order_id: int, line_ids: Optional[List[int]] = None,
                             contact_id: Optional[int] = None) -> Dict[str, Any]:
    return convert_record(_system(), "order", order_id, "invoice", line_ids=line_ids,
                          contact_id=contact_id)


def convert_order_to_purchase(order_id: int, line_ids: Optional[List[int]] = None,
                              vendor_id: Optional[int] = None,
                              contact_id: Optional[int] = None) -> Dict[str, Any]:
    return convert_record(_system(), "order", order_id, "purchase", line_ids=line_ids,
                          vendor_id=vendor_id, contact_id=contact_id)


def convert_quote_to_invoice(quote_id: int, line_ids: Optional[List[int]] = None,
                             contact_id: Optional[int] = None) -> Dict[str, Any]:
    return convert_record(_system(), "quote", quote_id, "invoice", line_ids=line_ids,
                          contact_id=contact_id)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def get_conversion_history(
    transaction_id: int,
    model_name: str,
) -> Dict[str, Any]:
    """Trace the conversion chain — walk parent_id/parent_model up and children down.

    Args:
        transaction_id: PK of the transaction
        model_name: lowercase model name ("quote", "order", "invoice", "purchase")

    Returns:
        {
            parents: [{model, id, ida, status}],
            children: [{model, id, ida, status}],
            self: {model, id, ida, status},
        }
    """
    try:
        Model = _get_model(model_name)
    except ConversionError:
        return {"error": f"Unknown model: {model_name}", "parents": [], "children": []}

    try:
        record = Model.objects.get(pk=transaction_id)
    except Model.DoesNotExist:
        return {"error": f"{model_name} #{transaction_id} not found", "parents": [], "children": []}

    self_info = {
        "model": model_name,
        "id": record.pk,
        "ida": getattr(record, "ida", ""),
        "status": getattr(record, "status", ""),
    }

    # Walk up the parent chain
    parents = []
    current = record
    visited = {(model_name, transaction_id)}
    while True:
        parent_id = getattr(current, "parent_id", None)
        parent_model = getattr(current, "parent_model", None)
        if not parent_id or not parent_model:
            break
        key = (parent_model, parent_id)
        if key in visited:
            break  # prevent loops
        visited.add(key)
        try:
            ParentModel = _get_model(parent_model)
            parent = ParentModel.objects.get(pk=parent_id)
            parents.append({
                "model": parent_model,
                "id": parent.pk,
                "ida": getattr(parent, "ida", ""),
                "status": getattr(parent, "status", ""),
            })
            current = parent
        except Exception:
            parents.append({
                "model": parent_model,
                "id": parent_id,
                "ida": "",
                "status": "not_found",
            })
            break

    parents.reverse()  # oldest ancestor first

    # Walk down — find children that reference this record as parent
    children = []
    child_types = ["quote", "order", "invoice", "purchase"]
    for child_type in child_types:
        try:
            ChildModel = _get_model(child_type)
            child_records = ChildModel.objects.filter(
                parent_id=transaction_id,
                parent_model=model_name,
            )
            for child in child_records:
                children.append({
                    "model": child_type,
                    "id": child.pk,
                    "ida": getattr(child, "ida", ""),
                    "status": getattr(child, "status", ""),
                })
        except Exception:
            continue

    return {
        "self": self_info,
        "parents": parents,
        "children": children,
    }


# ---------------------------------------------------------------------------
# Bulk conversion
# ---------------------------------------------------------------------------


def register() -> None:
    from apps.core.services.verbs import register_command
    for source in {s for s, _t in PAIRS}:
        register_command(source, "convert", convert_command)
