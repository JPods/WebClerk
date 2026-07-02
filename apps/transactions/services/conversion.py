"""
Document Conversion Chain — the fundamental commerce workflow.

    Proposal → Order → Invoice → Payment
                Order → Purchase (procurement / drop-ship)
    Proposal → Invoice (over-the-counter, skip order)

This module is the public API for all document conversions.  It delegates
to the existing transfer infrastructure (transfer.py, proposal_to_order.py,
order_to_invoice.py, order_to_purchase.py) where possible, and adds:

  - Commission carry-forward (set at earliest point, flows downstream)
  - Inventory impacts through adjust_item_quantity (ONE PATH)
  - Partial conversion support via line_ids
  - Conversion history tracing (walk parent_id/parent_model chain)
  - Bulk conversion

Design rules (from Bill):
  1. Commission populates at the earliest chain point and flows forward.
     Never recalculated downstream unless manually overridden.
  2. Lines copy forward with ALL their data.
  3. parent_id / parent_model link child to parent.
  4. Partial conversions are supported (convert N of M lines).
  5. Source transaction status updates after conversion.
  6. All inventory changes go through adjust_item_quantity — no direct writes.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db import transaction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fields copied from source header to target header
_HEADER_COPY_FIELDS = (
    "customer_id", "vendor_id", "manufacturer_id",
    "contact_id", "price_level", "terms", "terms_fk_id",
    "attention", "address_full", "email", "phone",
    "is_commission", "conditions_id", "conditions_description",
    "source",
)

# Fields copied from source line to target line (sell-side)
_SELL_LINE_COPY_FIELDS = (
    "item", "item_fk_id", "price", "cost", "commission",
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
        "proposal": "Proposal",
        "order": "Order",
        "invoice": "Invoice",
        "purchase": "Purchase",
    }
    cls_name = name_map.get(model_name)
    if not cls_name:
        raise ConversionError(f"Unknown model: {model_name}")
    return dj_apps.get_model("transactions", cls_name)


def _get_line_model(model_name: str):
    """Resolve a transaction line model by lowercase name."""
    name_map = {
        "proposal": "ProposalLine",
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
    return model_name  # proposal, order, invoice, purchase


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


def _copy_header_fields(source, target, extra_fields: tuple = ()) -> None:
    """Copy header-level fields from source to target."""
    for field in _HEADER_COPY_FIELDS + extra_fields:
        val = getattr(source, field, None)
        if val is not None and hasattr(target, field):
            setattr(target, field, val)


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


def _copy_line(
    source_line,
    target_header,
    target_fk_field: str,
    TargetLineModel,
    is_sell_side: bool = True,
    qty_override: Optional[float] = None,
) -> Any:
    """Copy a line from source to target transaction.

    Args:
        source_line: the source line instance
        target_header: the target header instance
        target_fk_field: FK field name on the target line (e.g. "order")
        TargetLineModel: the target line model class
        is_sell_side: True for proposal/order/invoice, False for purchase
        qty_override: if set, use this qty instead of source remaining

    Returns:
        The created target line instance.
    """
    target = TargetLineModel()
    setattr(target, target_fk_field, target_header)

    # Copy data fields
    copy_fields = _SELL_LINE_COPY_FIELDS if is_sell_side else _EXEC_LINE_COPY_FIELDS
    for field in copy_fields:
        if hasattr(source_line, field):
            val = getattr(source_line, field)
            if val is not None:
                # Deep copy dicts to avoid shared references
                if isinstance(val, dict):
                    import copy
                    val = copy.deepcopy(val)
                setattr(target, field, val)

    # Commission flows forward unchanged
    source_comm = getattr(source_line, "commission", None)
    if source_comm:
        target.commission = _copy_commission(source_comm)

    # Quantity: use remaining from source (or qty_override for partial)
    src_qty = getattr(source_line, "quantity", None) or {}
    remaining = float(src_qty.get("remaining", 0) or src_qty.get("active", 0) or 0)
    transfer_qty = qty_override if qty_override is not None else remaining

    if transfer_qty <= 0:
        return None  # nothing to convert

    precision = src_qty.get("precision", 2)
    target.quantity = {
        "staged": transfer_qty,
        "active": transfer_qty,
        "remaining": transfer_qty,
        "is_fixed": src_qty.get("is_fixed", False),
        "precision": precision,
    }

    # Line number from source
    target.line_number = getattr(source_line, "line_number", 0)

    # Refs: trace lineage
    src_refs = getattr(source_line, "refs", None) or {}
    import copy
    target.refs = copy.deepcopy(src_refs)
    target.refs.setdefault("source", {})["converted_from_line_id"] = source_line.pk

    # Metadata: conversion audit
    src_meta = getattr(source_line, "metadata", None) or {}
    target.metadata = copy.deepcopy(src_meta)
    target.metadata.setdefault("conversion", {})["source_line_id"] = source_line.pk
    target.metadata["conversion"]["transfer_qty"] = transfer_qty

    target.save()
    return target


def _decrement_source_remaining(
    source_line, transfer_qty: float, child_line_id: int
) -> None:
    """Update source line's children_active tracker and remaining after conversion.

    remaining = active - sum(children_active)
    """
    q = dict(getattr(source_line, "quantity", None) or {})
    active = float(q.get("active", 0) or 0)

    children = q.get("children_active", {"sum": 0, "lines": []})
    if not isinstance(children, dict):
        children = {"sum": 0, "lines": []}
    lines_list = children.get("lines", [])
    if not isinstance(lines_list, list):
        lines_list = []

    lines_list.append({"id": child_line_id, "active": transfer_qty})
    children_sum = sum(float(c.get("active", 0) or 0) for c in lines_list)
    children["sum"] = children_sum
    children["lines"] = lines_list
    q["children_active"] = children
    q["remaining"] = max(0.0, active - children_sum)

    source_line.quantity = q
    fields = ["quantity", "dt_modified", "version"]
    if q["remaining"] <= 0:
        source_line.status = "transferred"
        fields.append("status")
    source_line._pending_created = True  # suppress post_save signal
    source_line.save(update_fields=fields)


def _apply_inventory_adjustments(
    line_deltas: List[Dict[str, Any]],
    source_type: str,
    target_type: str,
) -> List[Dict]:
    """Apply inventory adjustments through the ONE PATH (adjust_item_quantity).

    Inventory bucket semantics:
      on_p    = proposal forecast
      on_so   = sales order commitment
      on_po   = purchase order commitment
      on_hand = physical inventory
      on_in   = invoiced (shipped)

    Conversion impacts:
      proposal → order:   on_p -= qty,  on_so += qty
      order → invoice:    on_so -= qty, on_hand -= qty
      order → purchase:   on_po += qty
      proposal → invoice: on_p -= qty,  on_hand -= qty
    """
    from apps.products.services.inventory_pending import adjust_item_quantity

    results = []
    # Define the bucket changes for each conversion type
    adjustments_map = {
        ("proposal", "order"): [
            {"field": "on_p", "sign": -1},
            {"field": "on_so", "sign": 1},
        ],
        ("order", "invoice"): [
            {"field": "on_so", "sign": -1},
            {"field": "on_hand", "sign": -1},
        ],
        ("order", "purchase"): [
            {"field": "on_po", "sign": 1},
        ],
        ("proposal", "invoice"): [
            {"field": "on_p", "sign": -1},
            {"field": "on_hand", "sign": -1},
        ],
    }

    adjustments = adjustments_map.get((source_type, target_type), [])
    if not adjustments:
        logger.warning(
            "No inventory adjustment rules for %s → %s", source_type, target_type
        )
        return results

    for delta in line_deltas:
        item_id = delta.get("item_id")
        if not item_id:
            continue

        qty = float(delta.get("quantity", 0))
        if qty <= 0:
            continue

        for adj in adjustments:
            try:
                result = adjust_item_quantity(
                    item_id=item_id,
                    field=adj["field"],
                    delta=adj["sign"] * qty,
                    reason=f"{source_type}_to_{target_type}_conversion",
                    source_type=target_type,
                    source_id=delta.get("target_header_id"),
                    source_line_id=delta.get("target_line_id"),
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "Inventory adjustment failed: item=%s field=%s delta=%s: %s",
                    item_id, adj["field"], adj["sign"] * qty, e,
                )
                # Don't fail the conversion for inventory errors —
                # the pending record is created either way
                results.append({
                    "item_id": item_id,
                    "field": adj["field"],
                    "error": str(e),
                    "applied": False,
                })

    return results


def _extract_item_id(line) -> Optional[int]:
    """Extract item_id from a line's item_fk or item JSON."""
    # FK first (source of truth)
    fk_id = getattr(line, "item_fk_id", None)
    if fk_id:
        return int(fk_id)
    # Fall back to item JSON
    item_data = getattr(line, "item", None) or {}
    if isinstance(item_data, dict):
        return item_data.get("item_id") or item_data.get("id")
    return None


def _update_source_status(source, source_type: str) -> None:
    """Update source status based on remaining quantities across all lines."""
    LineModel = _get_line_model(source_type)
    fk_field = _get_line_fk_field(source_type)
    all_lines = LineModel.objects.filter(**{fk_field: source})

    total_remaining = sum(
        float((ln.quantity or {}).get("remaining", 0) or 0)
        for ln in all_lines
    )

    if total_remaining <= 0:
        source.status = "converted"
    else:
        source.status = "in_progress"

    source.save(update_fields=["status", "dt_modified", "version"])


def _update_source_flow(source, target_type: str, target_id: int) -> None:
    """Append target to source's flow.children."""
    flow = dict(getattr(source, "flow", None) or {})
    children = list(flow.get("children", []))
    children.append({"type": target_type, "id": target_id})
    flow["children"] = children
    source.flow = flow
    source.save(update_fields=["flow", "dt_modified", "version"])


def _do_convert(
    *,
    source_type: str,
    target_type: str,
    source_id: int,
    line_ids: Optional[List[int]] = None,
    contact_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    is_sell_side: bool = True,
) -> Dict[str, Any]:
    """Core conversion logic shared by all public conversion functions.

    Runs inside a transaction.atomic() block. Creates the target header,
    copies lines, decrements source remaining, and applies inventory.
    """
    SourceModel = _get_model(source_type)
    TargetModel = _get_model(target_type)
    TargetLineModel = _get_line_model(target_type)
    target_fk_field = _get_line_fk_field(target_type)

    # Fetch source with lock
    try:
        source = SourceModel.objects.select_for_update().get(pk=source_id)
    except SourceModel.DoesNotExist:
        raise ConversionError(f"{source_type} #{source_id} not found")

    # Check not locked
    if getattr(source, "is_locked", False):
        raise ConversionError(
            f"{source_type} #{source_id} is locked — cannot convert"
        )

    # Select lines
    source_lines = _get_lines(source, source_type, line_ids)

    # Create target header
    target = TargetModel()
    target.status = "planned"
    target.parent_id = source.pk
    target.parent_model = source_type
    _copy_header_fields(source, target)

    # Commission flows forward at header level
    source_comm = getattr(source, "commission", None)
    if source_comm:
        target.commission = _copy_commission(source_comm)

    # Override contact if specified
    if contact_id is not None:
        target.contact_id = contact_id

    # For purchase conversions, set vendor
    if vendor_id is not None:
        target.vendor_id = vendor_id

    target.save()

    # Copy lines
    line_mapping: Dict[int, int] = {}
    inventory_deltas: List[Dict[str, Any]] = []
    lines_converted = 0
    lines_skipped = 0

    for src_line in source_lines:
        src_qty = getattr(src_line, "quantity", None) or {}
        remaining = float(src_qty.get("remaining", 0) or 0)

        if remaining <= 0:
            lines_skipped += 1
            continue

        target_line = _copy_line(
            source_line=src_line,
            target_header=target,
            target_fk_field=target_fk_field,
            TargetLineModel=TargetLineModel,
            is_sell_side=is_sell_side,
        )

        if target_line is None:
            lines_skipped += 1
            continue

        line_mapping[src_line.pk] = target_line.pk
        lines_converted += 1

        # Decrement source line remaining
        _decrement_source_remaining(src_line, remaining, target_line.pk)

        # Collect inventory delta
        item_id = _extract_item_id(src_line)
        if item_id:
            inventory_deltas.append({
                "item_id": item_id,
                "quantity": remaining,
                "target_header_id": target.pk,
                "target_line_id": target_line.pk,
                "source_line_id": src_line.pk,
            })

    if lines_converted == 0:
        raise ConversionError(
            f"No convertible lines (all have remaining <= 0)"
        )

    # Apply inventory adjustments (ONE PATH)
    _apply_inventory_adjustments(inventory_deltas, source_type, target_type)

    # Update source status and flow
    _update_source_status(source, source_type)
    _update_source_flow(source, target_type, target.pk)

    # Recalculate totals on target
    try:
        target.refresh_from_db()
        target.update_sell_cost_totals(persist=True)
    except Exception:
        pass  # best-effort

    # Recalculate totals on source
    try:
        source.refresh_from_db()
        source.update_sell_cost_totals(persist=True)
    except Exception:
        pass

    # Count remaining lines on source
    source_lines_remaining = 0
    LineModel = _get_line_model(source_type)
    fk_field = _get_line_fk_field(source_type)
    for ln in LineModel.objects.filter(**{fk_field: source}):
        r = float((ln.quantity or {}).get("remaining", 0) or 0)
        if r > 0:
            source_lines_remaining += 1

    return {
        f"{target_type}_id": target.pk,
        f"{target_type}_ida": getattr(target, "ida", ""),
        "lines_converted": lines_converted,
        "lines_remaining": source_lines_remaining,
        "line_mapping": line_mapping,
        "source_status": source.status,
    }


# ---------------------------------------------------------------------------
# Public API — individual conversions
# ---------------------------------------------------------------------------

@transaction.atomic
def convert_proposal_to_order(
    proposal_id: int,
    line_ids: Optional[List[int]] = None,
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convert a Proposal (or selected lines) to an Order.

    Commission set on the proposal flows forward to the order unchanged.
    Inventory: on_p -= qty, on_so += qty per line.

    Args:
        proposal_id: PK of the source Proposal
        line_ids: specific line IDs to convert (None = all)
        contact_id: override contact on the new Order

    Returns:
        {order_id, order_ida, lines_converted, lines_remaining}
    """
    return _do_convert(
        source_type="proposal",
        target_type="order",
        source_id=proposal_id,
        line_ids=line_ids,
        contact_id=contact_id,
        is_sell_side=True,
    )


@transaction.atomic
def convert_order_to_invoice(
    order_id: int,
    line_ids: Optional[List[int]] = None,
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convert an Order (or selected lines) to an Invoice.

    Commission flows forward from the order unchanged.
    Inventory: on_so -= qty, on_hand -= qty per line.

    Args:
        order_id: PK of the source Order
        line_ids: specific line IDs to convert (None = all)
        contact_id: override contact on the new Invoice

    Returns:
        {invoice_id, invoice_ida, lines_converted, lines_remaining}
    """
    return _do_convert(
        source_type="order",
        target_type="invoice",
        source_id=order_id,
        line_ids=line_ids,
        contact_id=contact_id,
        is_sell_side=True,
    )


@transaction.atomic
def convert_order_to_purchase(
    order_id: int,
    line_ids: Optional[List[int]] = None,
    vendor_id: Optional[int] = None,
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convert Order lines to a Purchase Order (procurement / drop-ship).

    The vendor_id is required. If not provided, the order's vendor is used.
    If neither exists, an error is raised.
    Commission flows forward from the order.
    Inventory: on_po += qty per line.

    Args:
        order_id: PK of the source Order
        line_ids: specific line IDs to convert (None = all)
        vendor_id: vendor for the Purchase (required or from order)
        contact_id: override contact on the new Purchase

    Returns:
        {purchase_id, purchase_ida, lines_converted}
    """
    # Resolve vendor
    Order = _get_model("order")
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        raise ConversionError(f"Order #{order_id} not found")

    effective_vendor = vendor_id or getattr(order, "vendor_id", None)
    if not effective_vendor:
        raise ConversionError(
            "vendor_id is required for order-to-purchase conversion "
            "(no vendor on the source order)"
        )

    return _do_convert(
        source_type="order",
        target_type="purchase",
        source_id=order_id,
        line_ids=line_ids,
        contact_id=contact_id,
        vendor_id=effective_vendor,
        is_sell_side=False,
    )


@transaction.atomic
def convert_proposal_to_invoice(
    proposal_id: int,
    line_ids: Optional[List[int]] = None,
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convert a Proposal directly to an Invoice (over-the-counter sale).

    Skips the Order stage. Commission flows forward from proposal.
    Inventory: on_p -= qty, on_hand -= qty per line.

    Args:
        proposal_id: PK of the source Proposal
        line_ids: specific line IDs to convert (None = all)
        contact_id: override contact on the new Invoice

    Returns:
        {invoice_id, invoice_ida, lines_converted, lines_remaining}
    """
    return _do_convert(
        source_type="proposal",
        target_type="invoice",
        source_id=proposal_id,
        line_ids=line_ids,
        contact_id=contact_id,
        is_sell_side=True,
    )


# ---------------------------------------------------------------------------
# Conversion history
# ---------------------------------------------------------------------------

def get_conversion_history(
    transaction_id: int,
    model_name: str,
) -> Dict[str, Any]:
    """Trace the conversion chain — walk parent_id/parent_model up and children down.

    Args:
        transaction_id: PK of the transaction
        model_name: lowercase model name ("proposal", "order", "invoice", "purchase")

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
    child_types = ["proposal", "order", "invoice", "purchase"]
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

def bulk_convert(
    source_model: str,
    source_ids: List[int],
    target_model: str,
    contact_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convert multiple transactions at once.

    Calls the appropriate single conversion function for each source.

    Args:
        source_model: "proposal" or "order"
        source_ids: list of source PKs
        target_model: "order", "invoice", or "purchase"
        contact_id: optional contact override for all conversions
        vendor_id: optional vendor (required for purchase conversions)

    Returns:
        {converted: int, results: [...], errors: [{source_id, error}]}
    """
    # Resolve which conversion function to call
    conversion_key = (source_model, target_model)
    conversion_funcs = {
        ("proposal", "order"): convert_proposal_to_order,
        ("proposal", "invoice"): convert_proposal_to_invoice,
        ("order", "invoice"): convert_order_to_invoice,
        ("order", "purchase"): convert_order_to_purchase,
    }

    func = conversion_funcs.get(conversion_key)
    if func is None:
        return {
            "converted": 0,
            "results": [],
            "errors": [{"source_id": None, "error": f"Unsupported conversion: {source_model} -> {target_model}"}],
        }

    results = []
    errors = []
    converted = 0

    for source_id in source_ids:
        try:
            kwargs: Dict[str, Any] = {
                f"{source_model}_id": source_id,
                "contact_id": contact_id,
            }
            if target_model == "purchase" and vendor_id is not None:
                kwargs["vendor_id"] = vendor_id

            result = func(**kwargs)
            results.append(result)
            converted += 1
        except Exception as e:
            logger.error(
                "Bulk conversion failed for %s #%s -> %s: %s",
                source_model, source_id, target_model, e,
            )
            errors.append({"source_id": source_id, "error": str(e)})

    return {
        "converted": converted,
        "results": results,
        "errors": errors,
    }
