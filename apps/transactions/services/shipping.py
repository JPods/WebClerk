"""
Shipping / Packing Workflow Service
====================================

Pick list generation, pack confirmation, shipment completion, and status tracking.

Ship completion uses the conversion chain (order -> invoice) so that inventory
impacts, commission carry-forward, and parent/child linkage are handled by the
ONE PATH. Shipping metadata is stored on both the order and the resulting invoice.

Design rules:
  - All inventory changes go through the conversion chain (adjust_item_quantity).
  - Partial shipments create one invoice per shipment.
  - Tracking/carrier/weight data stored in metadata.shipping on both order and invoice.
  - All datetimes are UTC (Axiom 14).
"""
from __future__ import annotations

import copy
import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db import transaction

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _get_order(order_id: int):
    """Fetch an Order by PK or raise ValueError."""
    Order = dj_apps.get_model("transactions", "Order")
    try:
        return Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        raise ValueError(f"Order #{order_id} not found")


def _get_order_lines(order):
    """Return all lines for an order."""
    OrderLine = dj_apps.get_model("transactions", "OrderLine")
    return list(OrderLine.objects.filter(order=order).order_by("line_number", "pk"))


def _extract_item_id(line) -> Optional[int]:
    """Extract item_id from a line's item_fk or item JSON."""
    fk_id = getattr(line, "item_fk_id", None)
    if fk_id:
        return int(fk_id)
    item_data = getattr(line, "item", None) or {}
    if isinstance(item_data, dict):
        return item_data.get("item_id") or item_data.get("id")
    return None


def _get_item_warehouse_info(item_id: Optional[int]) -> Dict[str, str]:
    """Look up bin location and warehouse name for an item.

    Checks item.metadata.warehouse first, then falls back to OrgItem
    and Warehouse records linked via refs.
    """
    if not item_id:
        return {"bin_location": "", "warehouse": ""}

    try:
        Item = dj_apps.get_model("products", "Item")
        item = Item.objects.get(pk=item_id)
    except Exception:
        return {"bin_location": "", "warehouse": ""}

    # Check item metadata for warehouse info
    meta = getattr(item, "metadata", None) or {}
    wh_info = meta.get("warehouse", {})
    if isinstance(wh_info, dict) and (wh_info.get("bin") or wh_info.get("location")):
        return {
            "bin_location": wh_info.get("bin", "") or wh_info.get("location", ""),
            "warehouse": wh_info.get("name", ""),
        }

    # Check refs for warehouse link
    refs = getattr(item, "refs", None) or {}
    links = refs.get("links", {})
    warehouse_ids = links.get("warehouse", [])
    if warehouse_ids:
        wh_id = warehouse_ids[0] if isinstance(warehouse_ids, list) else warehouse_ids
        try:
            Warehouse = dj_apps.get_model("products", "Warehouse")
            wh = Warehouse.objects.get(pk=wh_id)
            count = wh.count or {}
            return {
                "bin_location": count.get("bin", "") or count.get("shelf", ""),
                "warehouse": wh.name or "",
            }
        except Exception:
            pass

    return {"bin_location": "", "warehouse": ""}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pick_list(order_id: int) -> List[Dict[str, Any]]:
    """Generate a pick list for an order.

    Returns lines with item bin locations, quantities to pick.

    Returns:
        [{item_id, item_ida, item_name, qty, bin_location, warehouse}]
    """
    order = _get_order(order_id)
    lines = _get_order_lines(order)
    pick_list = []

    for line in lines:
        qty_data = getattr(line, "quantity", None) or {}
        remaining = float(qty_data.get("remaining", 0) or qty_data.get("active", 0) or 0)
        if remaining <= 0:
            continue

        item_id = _extract_item_id(line)
        item_data = getattr(line, "item", None) or {}
        item_ida = item_data.get("ida_item", "")
        item_name = item_data.get("description", "") or item_data.get("description_text", "")

        # Get warehouse/bin info
        wh_info = _get_item_warehouse_info(item_id)

        pick_list.append({
            "line_id": line.pk,
            "item_id": item_id,
            "item_ida": item_ida,
            "item_name": item_name,
            "qty": remaining,
            "bin_location": wh_info["bin_location"],
            "warehouse": wh_info["warehouse"],
            "line_number": getattr(line, "line_number", 0),
        })

    # Sort by warehouse then bin for efficient picking
    pick_list.sort(key=lambda r: (r["warehouse"], r["bin_location"], r["line_number"]))

    return pick_list


@transaction.atomic
def confirm_pack(
    order_id: int,
    packed_lines: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Record what was packed for an order.

    Args:
        order_id: PK of the order
        packed_lines: [{line_id, qty_packed, tracking_number, carrier, weight}]

    Stores packing data in order.metadata.shipping.packed_lines.
    Updates line quantity.shipped on each line.

    Returns:
        {order_id, lines_packed, total_qty_packed}
    """
    order = _get_order(order_id)
    OrderLine = dj_apps.get_model("transactions", "OrderLine")

    meta = copy.deepcopy(getattr(order, "metadata", None) or {})
    shipping = meta.setdefault("shipping", {})
    existing_packed = shipping.get("packed_lines", [])
    if not isinstance(existing_packed, list):
        existing_packed = []

    total_qty = 0
    lines_packed = 0

    for pl in packed_lines:
        line_id = pl.get("line_id")
        qty_packed = float(pl.get("qty_packed", 0))
        if not line_id or qty_packed <= 0:
            continue

        try:
            line = OrderLine.objects.select_for_update().get(pk=line_id, order=order)
        except OrderLine.DoesNotExist:
            logger.warning("Pack: line %s not found on order %s", line_id, order_id)
            continue

        # Update line quantity.shipped
        q = copy.deepcopy(getattr(line, "quantity", None) or {})
        shipped_prev = float(q.get("shipped", 0) or 0)
        q["shipped"] = shipped_prev + qty_packed
        line.quantity = q
        line.save(update_fields=["quantity", "dt_modified", "version"])

        # Record in packed_lines
        existing_packed.append({
            "line_id": line_id,
            "qty_packed": qty_packed,
            "tracking_number": pl.get("tracking_number", ""),
            "carrier": pl.get("carrier", ""),
            "weight": pl.get("weight"),
            "dt_packed": _now_ms(),
        })

        total_qty += qty_packed
        lines_packed += 1

    shipping["packed_lines"] = existing_packed
    meta["shipping"] = shipping
    order.metadata = meta
    order.save(update_fields=["metadata", "dt_modified", "version"])

    return {
        "order_id": order_id,
        "lines_packed": lines_packed,
        "total_qty_packed": total_qty,
    }


@transaction.atomic
def ship_order(
    order_id: int,
    shipping_data: Dict[str, Any],
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Complete shipment — create invoice via conversion chain.

    Args:
        order_id: PK of the source Order
        shipping_data: {carrier, tracking_number, ship_date, freight_cost}
        contact_id: optional contact override on the invoice

    Uses convert_order_to_invoice from the conversion chain so inventory
    impacts (on_so -= qty, on_hand -= qty) are handled by the ONE PATH.

    Stores shipping details in invoice.metadata.shipping.
    Updates order status to 'complete' or 'in_progress' (partial ship).

    Returns:
        {invoice_id, invoice_ida, lines_shipped}
    """
    from apps.transactions.services.conversion import convert_order_to_invoice

    # Run conversion chain — handles inventory, commission, line copy, status
    result = convert_order_to_invoice(
        order_id=order_id,
        contact_id=contact_id,
    )

    invoice_id = result.get("invoice_id")
    if not invoice_id:
        raise ValueError("Conversion chain did not return invoice_id")

    # Store shipping details on the invoice
    Invoice = dj_apps.get_model("transactions", "Invoice")
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist:
        raise ValueError(f"Invoice #{invoice_id} created but not found")

    meta = copy.deepcopy(getattr(invoice, "metadata", None) or {})
    meta["shipping"] = {
        "carrier": shipping_data.get("carrier", ""),
        "tracking_number": shipping_data.get("tracking_number", ""),
        "ship_date": shipping_data.get("ship_date", ""),
        "freight_cost": float(shipping_data.get("freight_cost", 0) or 0),
        "dt_shipped": _now_ms(),
    }
    invoice.metadata = meta
    invoice.save(update_fields=["metadata", "dt_modified", "version"])

    # Also record on the order for cross-reference
    order = _get_order(order_id)
    order_meta = copy.deepcopy(getattr(order, "metadata", None) or {})
    order_shipping = order_meta.setdefault("shipping", {})
    shipments = order_shipping.get("shipments", [])
    if not isinstance(shipments, list):
        shipments = []
    shipments.append({
        "invoice_id": invoice_id,
        "invoice_ida": result.get("invoice_ida", ""),
        "carrier": shipping_data.get("carrier", ""),
        "tracking_number": shipping_data.get("tracking_number", ""),
        "ship_date": shipping_data.get("ship_date", ""),
        "dt_shipped": _now_ms(),
    })
    order_shipping["shipments"] = shipments
    order_meta["shipping"] = order_shipping
    order.metadata = order_meta
    order.save(update_fields=["metadata", "dt_modified", "version"])

    return {
        "invoice_id": invoice_id,
        "invoice_ida": result.get("invoice_ida", ""),
        "lines_shipped": result.get("lines_converted", 0),
        "lines_remaining": result.get("lines_remaining", 0),
        "order_status": result.get("source_status", ""),
    }


def get_shipment_status(order_id: int) -> Dict[str, Any]:
    """Show what has been shipped, what is pending.

    Returns:
        {
            total_lines, shipped_lines, pending_lines,
            shipments: [{invoice_id, tracking, carrier, dt_shipped}]
        }
    """
    order = _get_order(order_id)
    lines = _get_order_lines(order)

    total_lines = 0
    shipped_lines = 0
    pending_lines = 0

    for line in lines:
        qty_data = getattr(line, "quantity", None) or {}
        active = float(qty_data.get("active", 0) or 0)
        remaining = float(qty_data.get("remaining", 0) or 0)

        if active <= 0:
            continue

        total_lines += 1
        if remaining <= 0:
            shipped_lines += 1
        else:
            pending_lines += 1

    # Gather shipment records from order metadata
    meta = getattr(order, "metadata", None) or {}
    shipping = meta.get("shipping", {})
    shipments_raw = shipping.get("shipments", [])
    if not isinstance(shipments_raw, list):
        shipments_raw = []

    shipments = []
    for s in shipments_raw:
        shipments.append({
            "invoice_id": s.get("invoice_id"),
            "invoice_ida": s.get("invoice_ida", ""),
            "tracking": s.get("tracking_number", ""),
            "carrier": s.get("carrier", ""),
            "dt_shipped": s.get("dt_shipped"),
        })

    return {
        "order_id": order_id,
        "order_ida": getattr(order, "ida", ""),
        "order_status": getattr(order, "status", ""),
        "total_lines": total_lines,
        "shipped_lines": shipped_lines,
        "pending_lines": pending_lines,
        "shipments": shipments,
    }
