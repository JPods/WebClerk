from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from django.db import transaction
from django.db.models import Model

PAYLOAD_VERSION = 1

def sum_price_extended(lines: Iterable[Model]) -> float:
    total = Decimal(0)
    for ln in lines:
        p = (getattr(ln, "price", None) or {})
        try:
            total += Decimal(str(p.get("extended", 0) or 0))
        except Exception:
            total += Decimal(0)
    return float(total)

def convert_quantity_from_source(src_qty: Optional[Dict], src_label: str) -> Dict:
    """Normalize a source line's quantity dict into a generic target-line quantity.

    The result dict always has canonical keys:
      staged:     base value (qty being transferred)
      active:     0 (nothing processed on new target yet)
      remaining:  base value (full qty available)
      precision, is_fixed:  preserved from source when present
      converted_from_<src_label>: audit trail with original keys

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    q = src_qty or {}
    base = q.get("staged", 0) or 0

    converted_key = f"converted_from_{src_label}"
    converted = {
        "is_blanket": q.get("is_blanket", False),
        "increment": q.get("increment", 0),
        "original_remaining": q.get("remaining", 0),
        "original_staged": base,
    }

    out = {
        "staged": base,
        "active": 0,
        "remaining": base,
        converted_key: converted,
    }
    if "precision" in q:
        out["precision"] = q["precision"]
    if "is_fixed" in q:
        out["is_fixed"] = q["is_fixed"]
    return out

def select_lines(qs, line_ids: Optional[List[int]], transfer_all: bool):
    if transfer_all:
        selected = list(qs)
        if not selected:
            raise ValueError("No lines to transfer")
        return selected
    if not line_ids:
        raise ValueError("Must specify line_ids when transfer_all is False")
    selected = list(qs.filter(id__in=line_ids))
    if not selected:
        raise ValueError("Line IDs not found")
    return selected

from common.decimals import safe_decimal as _to_decimal_safe  # noqa: E302

def _resolve_line_parent_id(src_line: Any) -> Any:
    if hasattr(src_line, 'parent_id_value'):
        try:
            return src_line.parent_id_value
        except Exception:
            pass
    parent_obj = getattr(src_line, 'parent', None)
    if parent_obj is not None:
        return getattr(parent_obj, 'id', None)
    for field_name in (
        'proposal_id', 'order_id', 'invoice_id', 'purchase_id',
        'workorder_id', 'receipt_id', 'requisition_id'
    ):
        if hasattr(src_line, field_name):
            return getattr(src_line, field_name)
    return None

def build_line_payload(src_line, src_kind: str) -> List[Dict[str, Any]]:
    """Build a normalized transfer-audit payload for a source line.

    Embedded into the target line's refs['xfer'] so the full provenance
    (source header, line, item, quantity, price, cost) is captured at
    transfer time.  This enables debugging and reconciliation without
    querying back to the source transaction.

    The payload is versioned (PAYLOAD_VERSION) and returned as a list to
    support future multi-source merges.

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    price = getattr(src_line, "price", None) or {}
    cost = getattr(src_line, "cost", None) or {}
    qty = getattr(src_line, "quantity", None) or {}
    refs = getattr(src_line, "refs", None) or {}

    base_qty = qty.get("staged")
    if base_qty is None:
        base_qty = qty.get("active")
    if base_qty is None:
        base_qty = qty.get("remaining", 0)

    payload_item = {
        "version": PAYLOAD_VERSION,
        "source": {
            "kind": src_kind,
            "parent_id": _resolve_line_parent_id(src_line),
            "line_id": getattr(src_line, "id", None),
        },
        "item": {
            "id": getattr(src_line, "item_id", None),
            "sku": getattr(src_line, "sku", None) or getattr(getattr(src_line, "item", None), "sku", None),
            "name": getattr(src_line, "name", None) or getattr(getattr(src_line, "item", None), "name", None),
            "uom": qty.get("uom") if isinstance(qty, dict) else None,
        },
        "qty": {
            "base": _to_decimal_safe(base_qty),
            "staged": qty.get("staged"),
            "active": qty.get("active"),
            "remaining": qty.get("remaining"),
            "precision": qty.get("precision"),
        },
        "price": {
            "unit": _to_decimal_safe(price.get("unit")),
            "extended": _to_decimal_safe(price.get("extended")),
            "currency": price.get("currency"),
            "precision": price.get("precision"),
        },
        "cost": {
            "unit": _to_decimal_safe(cost.get("unit")),
            "extended": _to_decimal_safe(cost.get("extended")),
            "currency": cost.get("currency"),
        },
        "meta": {
            "status": getattr(src_line, "status", None),
            "tags": refs.get("tags") if isinstance(refs, dict) else None,
        },
    }
    return [payload_item]