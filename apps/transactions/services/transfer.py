"""Unified transaction transfer engine.

Routes all transfer scenarios through a single entry point and applies the
correct quantity / lineage rules for each source→target combination.

Three transfer modes:
  1. Clone      — Proposal→Proposal: copy with quantities reset
  2. Convert    — Proposal→Order/Invoice: increment-based partial transfer
  3. Cross-type — Sell↔Purchase: full quantity copy, no customer

See: readmes/topics/transactions/transaction_transfer.md
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from django.db import transaction
from django.db.models import Model

from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    WorkOrder, WorkOrderLine,
)
from .transfer_utils import build_line_payload, select_lines

from decimal import Decimal
import json


class TransferError(Exception):
    """Business-rule violation during transfer."""


def _sanitize_for_json(obj):
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# Registry — maps (source_type, target_type) to a transfer mode
# ---------------------------------------------------------------------------

SELL_TYPES = {"proposal", "order", "invoice"}
BUY_TYPES = {"purchase"}
EXEC_TYPES = {"workorder"}
ALL_TRANSFER_TYPES = SELL_TYPES | BUY_TYPES | EXEC_TYPES

HEADER_MODELS: Dict[str, Type[Model]] = {
    "proposal": Proposal,
    "order":    Order,
    "invoice":  Invoice,
    "purchase": Purchase,
    "workorder": WorkOrder,
}

LINE_MODELS: Dict[str, Type[Model]] = {
    "proposal": ProposalLine,
    "order":    OrderLine,
    "invoice":  InvoiceLine,
    "purchase": PurchaseLine,
    "workorder": WorkOrderLine,
}

# FK field name on the line model that points to the header
LINE_FK_FIELD: Dict[str, str] = {
    "proposal": "proposal",
    "order":    "order",
    "invoice":  "invoice",
    "purchase": "purchase",
    "workorder": "workorder",
}

DEFAULT_TARGET_STATUS: Dict[str, str] = {
    "proposal": "planned",
    "order":    "confirmed",
    "invoice":  "pending",
    "purchase": "open",
    "workorder": "open",
}


def _get_transfer_mode(source_type: str, target_type: str) -> str:
    """Determine the transfer mode for a source→target pair."""
    if source_type == "proposal" and target_type == "proposal":
        return "clone"
    # Same-type transfers (other than proposal clone) are not supported
    if source_type == target_type:
        raise TransferError(
            f"Unsupported transfer: {source_type} → {target_type}"
        )

    if source_type not in ALL_TRANSFER_TYPES or target_type not in ALL_TRANSFER_TYPES:
        raise TransferError(
            f"Unsupported transfer: {source_type} → {target_type}"
        )

    if source_type in SELL_TYPES and target_type in SELL_TYPES:
        return "convert"
    return "cross"


# ---------------------------------------------------------------------------
# Quantity helpers — canonical placed/actioned/remaining
# ---------------------------------------------------------------------------

def _clone_quantity(src_qty: Dict) -> Dict:
    """Clone mode: reset actioned, remaining = placed."""
    placed = src_qty.get("placed", 0)
    return {
        "placed":     placed,
        "actioned":   0,
        "remaining":  placed,
        "increment":  src_qty.get("increment", 0),
        "is_fixed":   src_qty.get("is_fixed", False),
        "is_blanket": src_qty.get("is_blanket", False),
        "precision":  src_qty.get("precision", 2),
    }


def _convert_quantity(src_qty: Dict) -> Dict:
    """Convert mode: apply increment logic and return the transfer qty dict.

    Returns:
        Target quantity dict with placed = transfer_qty.
        Also returns the decrement amount to apply to the source.
    """
    increment = src_qty.get("increment", 0)
    remaining = src_qty.get("remaining", 0)

    if remaining <= 0:
        return {}  # signal: skip this line

    if increment == 0 or increment >= remaining:
        transfer_qty = remaining
    else:
        transfer_qty = increment

    return {
        "placed":     transfer_qty,
        "actioned":   0,
        "remaining":  transfer_qty,
        "increment":  increment,
        "is_fixed":   src_qty.get("is_fixed", False),
        "is_blanket": src_qty.get("is_blanket", False),
        "precision":  src_qty.get("precision", 2),
        "_transfer_qty": transfer_qty,  # internal — stripped before save
    }


def _cross_quantity(src_qty: Dict) -> Dict:
    """Cross-type mode: full copy, reset actioned."""
    placed = src_qty.get("placed", 0)
    return {
        "placed":     placed,
        "actioned":   0,
        "remaining":  placed,
        "increment":  src_qty.get("increment", 0),
        "is_fixed":   src_qty.get("is_fixed", False),
        "is_blanket": src_qty.get("is_blanket", False),
        "precision":  src_qty.get("precision", 2),
    }


# ---------------------------------------------------------------------------
# Header / line builders
# ---------------------------------------------------------------------------

def _build_header_kwargs(
    source: Model,
    source_type: str,
    target_type: str,
    mode: str,
    target_status: str,
) -> Dict[str, Any]:
    """Build kwargs for creating the target header."""
    kwargs: Dict[str, Any] = {
        "status":       target_status,
        "parent_model": source_type,
        "parent_id":    source.pk,
        "refs":         {
            "source": {
                f"{source_type}_id": source.pk,
                "converted_from": source_type,
            }
        },
        "flow":         {
            "source":   [{"type": source_type, "id": source.pk}],
            "children": [],
        },
    }

    if mode == "clone":
        # No customer, retail pricing
        kwargs["price_level"] = "retail"

    elif mode == "convert":
        # Copy customer / party info from source
        for field in (
            "customer_id", "vendor_id", "manufacturer_id",
            "contact_id", "price_level",
            "attention", "address_full", "email", "phone",
            "terms", "terms_fk_id", "conditions_id", "conditions_description",
        ):
            val = getattr(source, field, None)
            if val is not None:
                kwargs[field] = val

    # cross mode: no customer, no vendor — leave defaults (null)

    return kwargs


def _build_line_kwargs(
    src_line: Model,
    source_type: str,
    target_type: str,
    target_header: Model,
    mode: str,
) -> Optional[Dict[str, Any]]:
    """Build kwargs for creating one target line.

    Returns None if the line should be skipped.
    """
    src_qty = getattr(src_line, "quantity", None) or {}

    # Compute target quantity based on mode
    if mode == "clone":
        target_qty = _clone_quantity(src_qty)
    elif mode == "convert":
        target_qty = _convert_quantity(src_qty)
        if not target_qty:
            return None  # remaining was 0 — skip
    else:
        target_qty = _cross_quantity(src_qty)

    # Strip internal key before persisting
    transfer_qty = target_qty.pop("_transfer_qty", None)

    fk_field = LINE_FK_FIELD[target_type]

    kwargs: Dict[str, Any] = {
        fk_field:      target_header,
        "status":      "pending",
        "price_level": getattr(src_line, "price_level", "") or "",
        "quantity":    target_qty,
        "cost":        dict(getattr(src_line, "cost", None) or {}),
        "tax":         dict(getattr(src_line, "tax", None) or {}),
        "physical":    dict(getattr(src_line, "physical", None) or {}),
        "item":        dict(getattr(src_line, "item", None) or {}),
        "refs":        {
            "source": {
                f"{source_type}_line_id": src_line.pk,
                f"{source_type}_id": getattr(src_line, f"{source_type}_id", None),
            },
            "xfer": _sanitize_for_json(build_line_payload(src_line, source_type)),
        },
        "metadata":    _build_line_metadata(src_line, source_type, target_qty),
    }

    # item_fk (FK to Item) — copy if present
    item_fk_id = getattr(src_line, "item_fk_id", None) or getattr(src_line, "item_id_fk", None)
    if item_fk_id:
        kwargs["item_fk_id"] = item_fk_id

    # Price — only for sell-side target lines (BaseSellLineModel)
    if target_type in SELL_TYPES:
        kwargs["price"] = dict(getattr(src_line, "price", None) or {})

    return kwargs


def _build_line_metadata(
    src_line: Model, source_type: str, target_qty: Dict
) -> Dict:
    """Inject parent_link into line metadata."""
    md = dict(getattr(src_line, "metadata", None) or {})
    src_qty = getattr(src_line, "quantity", None) or {}
    md["parent_link"] = {
        "parent_id": getattr(src_line, f"{source_type}_id", None),
        "parent_model": source_type,
        "quantity_at_parent": {
            "placed":    src_qty.get("placed", 0),
            "remaining": src_qty.get("remaining", 0),
        },
    }
    return md


# ---------------------------------------------------------------------------
# Source line updater (convert mode only)
# ---------------------------------------------------------------------------

def _decrement_source_line(src_line: Model, transfer_qty: float) -> None:
    """Decrease source remaining and bump actioned after convert transfer."""
    q = dict(getattr(src_line, "quantity", None) or {})
    q["actioned"] = q.get("actioned", 0) + transfer_qty
    q["remaining"] = max(0, q.get("remaining", 0) - transfer_qty)
    src_line.quantity = q
    fields = ["quantity", "dt_modified", "version"]
    if q["remaining"] <= 0:
        src_line.status = "transferred"
        fields.append("status")
    src_line.save(update_fields=fields)


def _update_source_flow(source: Model, target_type: str, target_id: int) -> None:
    """Append target to source's flow.children."""
    flow = dict(getattr(source, "flow", None) or {})
    children = list(flow.get("children", []))
    children.append({"type": target_type, "id": target_id})
    flow["children"] = children
    source.flow = flow
    source.save(update_fields=["flow", "dt_modified", "version"])


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

@transaction.atomic
def execute_transfer(
    *,
    source_type: str,
    source_id: int,
    target_type: str,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = True,
    preserve_source: bool = True,
    target_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a transaction transfer.

    Args:
        source_type:    "proposal", "order", "invoice", or "purchase"
        source_id:      PK of the source transaction
        target_type:    "proposal", "order", "invoice", or "purchase"
        line_ids:       Specific line IDs to transfer (None = all)
        transfer_all:   If True and line_ids is None, transfer all lines
        preserve_source: If False, mark source as converted/fulfilled
        target_status:  Override the default target status

    Returns:
        Dict with success, target_id, lines_transferred, line_mapping, etc.
    """
    # Validate types
    if source_type not in HEADER_MODELS:
        raise TransferError(f"Unknown source type: {source_type}")
    if target_type not in HEADER_MODELS:
        raise TransferError(f"Unknown target type: {target_type}")

    mode = _get_transfer_mode(source_type, target_type)

    # Resolve models
    HeaderModel = HEADER_MODELS[source_type]
    LineModel = LINE_MODELS[source_type]
    TargetHeaderModel = HEADER_MODELS[target_type]
    TargetLineModel = LINE_MODELS[target_type]
    fk_field = LINE_FK_FIELD[source_type]

    # Fetch source
    try:
        source = HeaderModel.objects.select_for_update().get(pk=source_id)
    except HeaderModel.DoesNotExist:
        raise TransferError(f"Source not found: {source_type} #{source_id}")

    # Select lines
    line_qs = LineModel.objects.select_for_update().filter(
        **{fk_field: source}
    )
    try:
        selected_lines = select_lines(line_qs, line_ids, transfer_all)
    except ValueError as exc:
        raise TransferError(str(exc))

    # Create target header
    status_val = target_status or DEFAULT_TARGET_STATUS.get(target_type, "planned")
    header_kwargs = _build_header_kwargs(
        source, source_type, target_type, mode, status_val
    )
    target_header = TargetHeaderModel.objects.create(**header_kwargs)

    # Create target lines
    line_mapping: Dict[int, int] = {}
    transferred = 0

    for src_line in selected_lines:
        line_kwargs = _build_line_kwargs(
            src_line, source_type, target_type, target_header, mode
        )
        if line_kwargs is None:
            continue  # skipped (e.g., remaining=0)

        target_line = TargetLineModel.objects.create(**line_kwargs)
        line_mapping[src_line.pk] = target_line.pk
        transferred += 1

        # Decrement source (convert mode only)
        if mode == "convert":
            src_qty = getattr(src_line, "quantity", None) or {}
            increment = src_qty.get("increment", 0)
            remaining = src_qty.get("remaining", 0)
            if increment == 0 or increment >= remaining:
                xfer_qty = remaining
            else:
                xfer_qty = increment
            _decrement_source_line(src_line, xfer_qty)

    if transferred == 0:
        raise TransferError("No lines to transfer")

    # Update source flow
    _update_source_flow(source, target_type, target_header.pk)

    # Mark source as converted if requested
    if not preserve_source and mode == "convert":
        all_remaining = sum(
            (getattr(ln, "quantity", None) or {}).get("remaining", 0)
            for ln in LineModel.objects.filter(**{fk_field: source})
        )
        if all_remaining <= 0:
            source.status = "converted"
            source.save(update_fields=["status", "dt_modified", "version"])

    return {
        "success":            True,
        "target_id":          target_header.pk,
        "target_type":        target_type,
        "source_id":          source.pk,
        "source_type":        source_type,
        "lines_transferred":  transferred,
        "line_mapping":       line_mapping,
        "source_preserved":   preserve_source,
        "target_status":      status_val,
    }
