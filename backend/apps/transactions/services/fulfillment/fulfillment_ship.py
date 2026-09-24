"""
Shipping / Packing Workflow Service
====================================

Pick list generation, pack confirmation, shipment completion, and status tracking.

Ship completion uses the conversion chain (order -> invoice) so that inventory
impacts, commission carry-forward, and parent/child linkage are handled by the
ONE PATH. Shipping metadata is stored on both the order and the resulting invoice.

Design rules:
  - All inventory changes go through Pending (try_apply on save).
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

    Checks item.metadata.warehouse first, then Warehouse records linked via refs.
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
        remaining = float(qty_data.get("remaining", 0) or 0)
        if remaining == 0:
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

        # No quantity mutation here — shipped qty lives on the invoice
        # line (invoice_line.quantity.active) after order→invoice conversion.
        # Packing records what goes in which box; conversion is the ship event.

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
    *,
    actor,
) -> Dict[str, Any]:
    """Ship what was packed: invoice exactly those lines and quantities.

    Bill, 2026-09-23 (gap 4): a shipment invoices exactly the lines and quantities
    shipped, through the one conversion engine, carrying terms, price level and rep like
    any order→invoice. No line-less invoices.

    What was shipped is what ``confirm_pack`` recorded and no shipment has invoiced yet
    (order.metadata.shipping.packed_lines without an invoice_id). The one engine
    (``convert_record``) builds the invoice from the order as ``actor``; the shipped
    quantity replaces each line's remaining, and the invoice is saved once with its
    lines and shipping record — so the invoice lines name their order lines and each
    order line's remaining is recomputed from its children.

    This used to convert every remaining line whatever was packed, never saved the lines
    the engine returns for review (an invoice with no lines), and read result keys the
    engine does not return.

    Args:
        order_id: PK of the source Order
        shipping_data: {carrier, tracking_number, ship_date, freight_cost}
        contact_id: optional contact override on the invoice
        actor: who is shipping (apps.core.services.door.Actor)

    Returns:
        {invoice_id, invoice_ida, lines_shipped, lines_remaining, order_status}
    """
    from collections import defaultdict

    from apps.transactions.services.convert.convert import convert_record

    order = _get_order(order_id)
    order_meta = copy.deepcopy(getattr(order, "metadata", None) or {})
    order_shipping = order_meta.setdefault("shipping", {})
    packed = order_shipping.get("packed_lines") or []
    to_ship = [pl for pl in packed if isinstance(pl, dict) and not pl.get("invoice_id")]
    if not to_ship:
        raise ValueError(f"Order #{order_id} has nothing packed that is not already "
                         f"invoiced. Confirm the pack first; a shipment invoices what was packed.")

    shipped_qty: Dict[int, float] = defaultdict(float)
    for pl in to_ship:
        shipped_qty[int(pl["line_id"])] += float(pl.get("qty_packed", 0) or 0)

    shipped_lines: list = []

    def take(review_lines):
        lines = shipped_lines
        for review in review_lines:
            source_line_id = ((review.get("refs") or {}).get("source") or {}).get("order_line_id")
            qty = shipped_qty.pop(source_line_id, 0)
            if not qty:
                continue
            remaining = float((review.get("quantity") or {}).get("remaining", 0) or 0)
            if qty > remaining:
                raise ValueError(f"Order line {source_line_id}: {qty} packed, but only "
                                 f"{remaining} is left to invoice. Correct the pack before "
                                 f"shipping.")
            review["quantity"] = {**review["quantity"], "active": qty, "staged": qty,
                                  "remaining": qty}
            lines.append(review)
        if shipped_qty:
            raise ValueError(f"Order #{order_id}: packed line(s) {sorted(shipped_qty)} have "
                             f"nothing left to invoice. Correct the pack before shipping.")
        return lines

    # One save: the invoice, its shipped lines and its shipping record together — the
    # invoice's hooks run once, and the transfer check sees the lines (plan §14a.5).
    result = convert_record(actor, "order", order_id, "invoice", line_ids=list(shipped_qty),
                            contact_id=contact_id, take=take, stamp={"metadata": {"shipping": {
                                "carrier": shipping_data.get("carrier", ""),
                                "tracking_number": shipping_data.get("tracking_number", ""),
                                "ship_date": shipping_data.get("ship_date", ""),
                                "freight_cost": float(shipping_data.get("freight_cost", 0) or 0),
                                "dt_shipped": _now_ms(),
                            }}})
    invoice_id = result["invoice_id"]

    order = _get_order(order_id)            # its lines' remaining moved with the invoice
    order_meta = copy.deepcopy(getattr(order, "metadata", None) or {})
    order_shipping = order_meta.setdefault("shipping", {})
    for pl in order_shipping.get("packed_lines") or []:
        if isinstance(pl, dict) and not pl.get("invoice_id"):
            pl["invoice_id"] = invoice_id
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
    order.metadata = order_meta
    order.save(update_fields=["metadata", "dt_modified", "version"])

    remaining_lines = sum(
        1 for line in _get_order_lines(order)
        if float(((getattr(line, "quantity", None) or {}).get("remaining", 0)) or 0) > 0)
    return {
        "invoice_id": invoice_id,
        "invoice_ida": result.get("invoice_ida", ""),
        "lines_shipped": len(shipped_lines),
        "lines_remaining": remaining_lines,
        "order_status": getattr(order, "status", ""),
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

        if active == 0:
            continue

        total_lines += 1
        if remaining == 0:
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
