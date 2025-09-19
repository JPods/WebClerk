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
    """
    Normalize a quantity dict into a generic line quantity for targets.

    - Base = placed if present; else ordered; else remaining; else 0
    - Preserve precision/is_fixed when present
    - Set invoiced=0 by default (safe for non-invoice targets)
    - Attach converted_from_<src_label> with original keys
    """
    q = src_qty or {}
    base = q.get("placed")
    used_key = "placed"
    if base is None:
        base = q.get("ordered")
        used_key = "ordered"
    if base is None:
        base = q.get("remaining", 0)
        used_key = "remaining"

    converted_key = f"converted_from_{src_label}"
    converted = {
        "is_blanket": q.get("is_blanket", False),
        "increment": q.get("increment", 0),
        "original_remaining": q.get("remaining", 0),
    }
    if used_key == "placed":
        converted["original_placed"] = q.get("placed", 0)
    elif used_key == "ordered":
        converted["original_ordered"] = q.get("ordered", 0)
    else:
        converted["original_remaining"] = q.get("remaining", 0)

    out = {
        "remaining": base or 0,
        "invoiced": 0,
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

def _to_decimal_safe(val: Any, default: Decimal = Decimal(0)) -> Decimal:
    try:
        if val is None:
            return default
        return Decimal(str(val))
    except Exception:
        return default

def build_line_payload(src_line, src_kind: str) -> List[Dict[str, Any]]:
    """
    Build a normalized payload array for a source line, to be embedded into refs['xfer'].

    Structure (versioned):
    [
      {
        'version': 1,
        'source': { 'kind': 'proposal'|'sales_order'|'purchase_order'|'invoice', 'parent_id': int, 'line_id': int },
        'item':   { 'id': int|None, 'sku': str|None, 'name': str|None, 'uom': str|None },
        'qty':    { 'base': Decimal, 'placed': any, 'ordered': any, 'remaining': any, 'precision': int|None },
        'price':  { 'unit': Decimal, 'extended': Decimal, 'currency': str|None, 'precision': int|None },
        'cost':   { 'unit': Decimal, 'extended': Decimal, 'currency': str|None },
        'meta':   { 'status': str|None, 'tags': list|None }
      }
    ]
    """
    price = getattr(src_line, "price", None) or {}
    cost = getattr(src_line, "cost", None) or {}
    qty = getattr(src_line, "quantity", None) or {}
    refs = getattr(src_line, "refs", None) or {}

    base_qty = qty.get("placed")
    if base_qty is None:
        base_qty = qty.get("ordered")
    if base_qty is None:
        base_qty = qty.get("remaining", 0)

    payload_item = {
        "version": PAYLOAD_VERSION,
        "source": {
            "kind": src_kind,
            "parent_id": getattr(src_line, "parent_id", None) or getattr(getattr(src_line, "parent", None), "id", None),
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
            "placed": qty.get("placed"),
            "ordered": qty.get("ordered"),
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