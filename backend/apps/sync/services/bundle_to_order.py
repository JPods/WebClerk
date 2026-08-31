"""
Bundle → Order — Receiving side of PO→SO cross-instance commerce.

When a vendor's WC3 instance receives a po_to_so bundle, this service
unpacks it into a pending Order (Sales Order) with lines.

The bundle's cost→price mapping has already been applied by the sender.
The lines arrive with price populated. The receiving sales team reviews
and approves the Order.

On approval, the vendor sends back the SO id to the buyer via the
bundle approve endpoint.
"""
from __future__ import annotations

import copy
import logging
import time
from typing import Any, Dict

from django.db import transaction

from apps.sync.models.bundle import Bundle
from apps.sync.models.connection import Connection
from apps.transactions.models import Order, OrderLine

logger = logging.getLogger(__name__)


@transaction.atomic
def unpack_po_to_so_bundle(bundle: Bundle) -> Dict[str, Any]:
    """Unpack a po_to_so bundle into a pending Order.

    Args:
        bundle: The Bundle record with payload containing the PO data

    Returns:
        {order_id, order_ida, line_count, bundle_uuid}
    """
    payload = bundle.get_payload()
    if not isinstance(payload, dict):
        raise ValueError("Bundle payload is empty or invalid")

    bundle_type = payload.get("type")
    if bundle_type != "po_to_so":
        raise ValueError(f"Expected po_to_so bundle, got: {bundle_type}")

    bundle_uuid = payload.get("bundle_uuid", "")
    header_data = payload.get("header", {})
    lines_data = payload.get("lines", [])
    sender = payload.get("sender", {})

    if not lines_data:
        raise ValueError("Bundle contains no lines")

    dt_now = int(time.time() * 1000)

    # Create Order header
    order = Order()
    order.status = "planned"  # pending approval by sales team

    # Copy header fields from bundle
    for field in ("attention", "address_full", "email", "phone",
                  "ship_via", "price_level", "terms", "dt_needed"):
        val = header_data.get(field)
        if val is not None and hasattr(order, field):
            setattr(order, field, val)

    # Set refs with bundle tracking
    order.refs = {
        "keywords": [],
        "tags": ["po_to_so"],
        "links": {
            "contact": [],
            "item": [],
            "bundle": [{
                "bundle_uuid": bundle_uuid,
                "bundle_id": bundle.pk,
                "connection_id": bundle.connection_id,
                "connection_name": bundle.connection.name if bundle.connection else "",
                "direction": "received",
                "type": "po_to_so",
                "dt_received": dt_now,
                "sender_purchase_id": sender.get("purchase_id"),
                "sender_purchase_ida": sender.get("purchase_ida", ""),
                "status": "pending_approval",
            }],
        },
        "parents": [],
    }

    # Flow: trace origin to bundle
    order.flow = {
        "source": [{
            "type": "bundle",
            "id": bundle.pk,
            "bundle_uuid": bundle_uuid,
        }],
        "children": [],
    }

    order.save()

    # Create lines
    lines_created = 0
    for line_data in lines_data:
        ol = OrderLine()
        ol.order = order
        ol.line_number = line_data.get("line_number", 0)
        ol.line_type = line_data.get("line_type", "product")
        ol.status = "planned"

        # Item data
        ol.item = copy.deepcopy(line_data.get("item", {}))

        # Quantity
        ol.quantity = copy.deepcopy(line_data.get("quantity", {}))

        # Price comes from sender's cost→price mapping
        ol.price = copy.deepcopy(line_data.get("price", {}))

        # Cost is empty — vendor calculates their own
        ol.cost = {}

        # Tax and physical
        ol.tax = copy.deepcopy(line_data.get("tax", {}))
        ol.physical = copy.deepcopy(line_data.get("physical", {}))

        ol._pending_created = True  # suppress signal
        ol.save()
        lines_created += 1

    # Update bundle record
    bundle.status = "success"
    bundle.response = {
        "order_id": order.pk,
        "order_ida": getattr(order, "ida", ""),
        "lines_created": lines_created,
        "dt_unpacked": dt_now,
    }
    bundle.dt_processed = dt_now
    bundle.save(update_fields=["status", "response", "dt_processed", "dt_modified", "version"])

    # Recalculate totals
    try:
        order.refresh_from_db()
        order.update_sell_cost_totals(persist=True)
    except Exception:
        pass

    logger.info(
        "PO→SO bundle unpacked: bundle=%s uuid=%s → order=%s lines=%d",
        bundle.pk, bundle_uuid, order.pk, lines_created,
    )

    return {
        "order_id": order.pk,
        "order_ida": getattr(order, "ida", ""),
        "line_count": lines_created,
        "bundle_uuid": bundle_uuid,
        "bundle_id": bundle.pk,
    }


@transaction.atomic
def approve_bundle_order(
    bundle_uuid: str,
) -> Dict[str, Any]:
    """Approve the Order created from a po_to_so bundle.

    Called by the vendor's sales team. Updates the Order status
    and returns the SO id for callback to the buyer.

    Args:
        bundle_uuid: The bundle UUID that created this Order

    Returns:
        {order_id, order_ida, bundle_uuid, status, connection_id}
    """
    # Find the bundle by UUID in config
    bundle = Bundle.objects.filter(
        config__bundle_uuid=bundle_uuid,
        direction="pull",
    ).first()

    if not bundle:
        raise ValueError(f"Bundle with uuid {bundle_uuid} not found")

    response = bundle.response or {}
    order_id = response.get("order_id")
    if not order_id:
        raise ValueError(f"Bundle {bundle_uuid} has no associated order")

    try:
        order = Order.objects.select_for_update().get(pk=order_id)
    except Order.DoesNotExist:
        raise ValueError(f"Order #{order_id} from bundle {bundle_uuid} not found")

    dt_now = int(time.time() * 1000)

    # Update order status
    order.status = "released"

    # Update bundle link status in refs
    refs = copy.deepcopy(order.refs) if isinstance(order.refs, dict) else {}
    bundle_links = refs.get("links", {}).get("bundle", [])
    for bl in bundle_links:
        if bl.get("bundle_uuid") == bundle_uuid:
            bl["status"] = "approved"
            bl["dt_approved"] = dt_now
    refs.setdefault("links", {})["bundle"] = bundle_links
    order.refs = refs
    order.save(update_fields=["status", "refs", "dt_modified", "version"])

    # Update bundle response with approval
    response["approved"] = True
    response["dt_approved"] = dt_now
    bundle.response = response
    bundle.save(update_fields=["response", "dt_modified", "version"])

    logger.info(
        "PO→SO bundle approved: uuid=%s order=%s ida=%s",
        bundle_uuid, order.pk, getattr(order, "ida", ""),
    )

    return {
        "order_id": order.pk,
        "order_ida": getattr(order, "ida", ""),
        "bundle_uuid": bundle_uuid,
        "status": "approved",
        "connection_id": bundle.connection_id,
    }
