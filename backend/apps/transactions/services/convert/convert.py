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
carries them forward. Lines come back for review; the reviewed save creates them (or the
caller passes them, as shipping does, and the target is saved once with them).

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
    "price_level", "terms", "terms_fk_id",
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
    """The line's item cost at the company unit_cost_default."""
    from apps.products.services.inventory.inventory_layers import item_unit_cost
    item = getattr(src_line, "item_fk", None)
    return item_unit_cost(getattr(item, "cost", None) if item else None)


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
    header["refs"] = {**copy.deepcopy(header.get("refs") or {}),
                      "source": {"converted_from": source_type, f"{source_type}_id": source.pk}}
    return header


def _review_lines(source_lines, source_type: str, is_sell_side: bool) -> List[Dict[str, Any]]:
    """What the target's lines would be — returned for review, not saved here."""
    lines = []
    for src_line in source_lines:
        src_qty = getattr(src_line, "quantity", None) or {}
        remaining = float(src_qty.get("remaining", 0) or 0)
        if remaining == 0:
            continue
        # A document discount line moved into allocations; it travels there, not as a line.
        if isinstance(getattr(src_line, "metadata", None), dict) and src_line.metadata.get("document_discount"):
            continue
        target_qty = {"active": remaining, "staged": remaining, "remaining": remaining}
        for key in ("precision", "is_fixed"):
            if key in src_qty:
                target_qty[key] = src_qty[key]
        cost = copy.deepcopy(getattr(src_line, "cost", None) or {})
        if not is_sell_side:
            # A purchase is what we pay the vendor: the item's cost at the company default,
            # never the sell line's estimate.
            cost["unit"] = float(_item_unit_cost_for_line(src_line))
        lines.append({
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
            "comments": getattr(src_line, "comments", None) or {},
            "config": getattr(src_line, "config", None) or {},
            "commission": _copy_commission(getattr(src_line, "commission", None)),
            "refs": {"source": {f"{source_type}_line_id": src_line.pk}},
            "_dirty": True,
        })
    return lines


@transaction.atomic
def convert_record(actor, source_type: str, source_id: int, target_type: str, *,
                   line_ids: Optional[List[int]] = None, contact_id: Optional[int] = None,
                   vendor_id: Optional[int] = None,
                   take: Optional[Callable[[List[dict]], List[dict]]] = None,
                   stamp: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convert ``source_type`` #``source_id`` to a new ``target_type``, as ``actor``.

    Without ``take`` the lines come back for review. With it, ``take(review_lines)`` names
    the lines to keep and the target is saved once with them — one save, its hooks once,
    the transfer check in the same unit (shipping). ``stamp`` is more of the header the
    server authors (a shipping record), carried like the rest.
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
    if getattr(source, "is_locked", False):
        from apps.core.services.door import Refused
        raise Refused(409, "locked", f"{source_type} {source_id} is locked; it cannot be converted.")
    try:
        source_lines = _get_lines(source, source_type, line_ids)
    except ConversionError as e:
        raise _refuse("no_lines", str(e)) from e

    if target_type == "purchase" and vendor_id is None:
        vendor_id = getattr(source, "vendor_id", None)     # the user may set it in review
    header = _header(source, source_type, target_type, is_sell_side, contact_id, vendor_id)
    review = _review_lines(source_lines, source_type, is_sell_side)
    if not review:
        raise _refuse("nothing_to_convert", "No convertible lines (every line has remaining 0).")

    header.update(copy.deepcopy(stamp or {}))
    payload = {"lines": take(copy.deepcopy(review))} if take is not None else {}
    result = save_record(actor, payload, model_key=target_type, server_set=header)

    forwarded = 0
    if (source_type, target_type) == ("order", "invoice"):
        from apps.transactions.services.cash.cash_door import relink_deposits
        forwarded = relink_deposits(source, result.obj)

    return {
        f"{target_type}_id": result.obj_id,
        f"{target_type}_ida": getattr(result.obj, "ida", ""),
        "lines_for_review": len(review),
        "lines": review,
        "cash_entries_forwarded": forwarded,
    }


def convert_command(ctx) -> Dict[str, Any]:
    """POST /wcapi/<source>/<id>/convert/ {to, line_ids?, vendor_id?, contact_id?}."""
    to = (ctx.data.get("to") or "").lower()
    if not to:
        raise _refuse("to_required", f"Name what the {ctx.model_key} converts to: {{\"to\": ...}}.")
    return convert_record(ctx.actor, ctx.model_key, ctx.obj.pk, to,
                          line_ids=ctx.data.get("line_ids"), contact_id=ctx.data.get("contact_id"),
                          vendor_id=ctx.data.get("vendor_id"))


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
