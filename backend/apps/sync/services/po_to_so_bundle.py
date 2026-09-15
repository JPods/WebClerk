"""
PO → SO Cross-Instance Bundle — Trading Partner Commerce

Converts a Purchase Order into a bundle payload for transmission to a
vendor's WC3 instance, where it becomes a pending Sales Order.

The purchase agent is responsible for correct costs on the PO.
Cost values on the PO map to price values on the SO. The Connection's
config.schema_map can override the default field mapping.

Default mapping (PO cost → SO price):
    line.cost.unit         → line.price.unit
    line.cost.unit_base    → line.price.unit_base
    line.cost.discount_percent → line.price.discount_percent
    line.cost.discount_amount  → line.price.discount_amount
    line.cost.extended     → line.price.extended

The bundle UUID becomes the cross-system tracking reference, stored
in record.refs.links.bundle[] on both sides.
"""
from __future__ import annotations

import copy
import logging
import time
import uuid as uuid_mod
from typing import Any, Dict, List, Optional

from django.db import transaction

from apps.sync.models.connection import Connection
from apps.sync.models.bundle import Bundle
from apps.transactions.models import Purchase, PurchaseLine

logger = logging.getLogger(__name__)


# ── Default field mapping: PO cost → SO price ────────────────────────
DEFAULT_COST_TO_PRICE_MAP = {
    "unit": "unit",
    "unit_base": "unit_base",
    "discount_percent": "discount_percent",
    "discount_amount": "discount_amount",
    "extended": "extended",
    "precision": "precision",
}

# Header fields carried from PO to SO bundle
_HEADER_FIELDS = (
    "ida", "attention", "address_full", "email", "phone",
    "ship_via", "price_level", "terms",
    "dt_needed",
)


def _get_field_map(connection: Connection) -> Dict[str, str]:
    """Resolve the cost→price field mapping from connection config or default."""
    config = connection.config if isinstance(connection.config, dict) else {}
    schema_map = config.get("schema_map", {})
    cost_to_price = schema_map.get("cost_to_price")
    if isinstance(cost_to_price, dict) and cost_to_price:
        return cost_to_price
    return dict(DEFAULT_COST_TO_PRICE_MAP)


def _map_cost_to_price(cost: Dict[str, Any], field_map: Dict[str, str]) -> Dict[str, Any]:
    """Transform a PO line cost envelope into an SO line price envelope."""
    price = {}
    for cost_key, price_key in field_map.items():
        if cost_key in cost:
            price[price_key] = cost[cost_key]
    # Ensure is_fixed carries through
    if "is_fixed" in cost:
        price["is_fixed"] = cost["is_fixed"]
    return price


def _serialize_line(line: PurchaseLine, field_map: Dict[str, str]) -> Dict[str, Any]:
    """Serialize a PurchaseLine into the bundle line payload."""
    cost_data = line.cost if isinstance(line.cost, dict) else {}
    return {
        "line_number": line.line_number,
        "item": copy.deepcopy(line.item) if isinstance(line.item, dict) else {},
        "quantity": copy.deepcopy(line.quantity) if isinstance(line.quantity, dict) else {},
        "price": _map_cost_to_price(cost_data, field_map),
        "cost": {},  # SO receiver calculates their own cost
        "tax": copy.deepcopy(line.tax) if isinstance(line.tax, dict) else {},
        "physical": copy.deepcopy(line.physical) if isinstance(line.physical, dict) else {},
        "line_type": line.line_type or "product",
        "status": "planned",
    }


def _serialize_header(purchase: Purchase) -> Dict[str, Any]:
    """Serialize PO header fields for the bundle."""
    header = {}
    for field in _HEADER_FIELDS:
        val = getattr(purchase, field, None)
        if val is not None:
            header[field] = val
    # Vendor on PO becomes customer context on SO (the buyer's identity)
    header["status"] = "planned"
    return header


@transaction.atomic
def create_po_so_bundle(
    purchase_id: int,
    connection_id: int,
) -> Dict[str, Any]:
    """Create a bundle from a Purchase Order for transmission to a vendor.

    Args:
        purchase_id: PK of the local Purchase record
        connection_id: PK of the Connection to the vendor

    Returns:
        {bundle_id, bundle_uuid, purchase_id, line_count, payload_summary}
    """
    try:
        purchase = Purchase.objects.select_for_update().get(pk=purchase_id)
    except Purchase.DoesNotExist:
        raise ValueError(f"Purchase #{purchase_id} not found")

    try:
        connection = Connection.objects.get(pk=connection_id, is_active=True)
    except Connection.DoesNotExist:
        raise ValueError(f"Connection #{connection_id} not found or inactive")

    lines = list(PurchaseLine.objects.filter(purchase=purchase))
    if not lines:
        raise ValueError(f"Purchase #{purchase_id} has no lines")

    field_map = _get_field_map(connection)

    # Build payload
    bundle_uuid = str(uuid_mod.uuid4())
    dt_now = int(time.time() * 1000)

    payload = {
        "type": "po_to_so",
        "version": "1.0",
        "bundle_uuid": bundle_uuid,
        "dt_created": dt_now,
        "sender": {
            "purchase_id": purchase.pk,
            "purchase_ida": getattr(purchase, "ida", ""),
            "connection_id": connection.pk,
            "connection_name": connection.name,
        },
        "header": _serialize_header(purchase),
        "lines": [_serialize_line(ln, field_map) for ln in lines],
        "field_map_used": field_map,
    }

    # Create Bundle record
    bundle = Bundle.objects.create(
        connection=connection,
        direction="push",
        model_name="purchase",
        status="queued",
        config={
            "bundle_uuid": bundle_uuid,
            "purchase_id": purchase.pk,
            "type": "po_to_so",
        },
        maps=field_map,
    )
    bundle.save_payload_to_disk(payload)

    # Stamp the PO with the bundle reference in refs.links.bundle[]
    refs = copy.deepcopy(purchase.refs) if isinstance(purchase.refs, dict) else {}
    links = refs.setdefault("links", {})
    bundle_links = links.setdefault("bundle", [])
    bundle_links.append({
        "bundle_uuid": bundle_uuid,
        "bundle_id": bundle.pk,
        "connection_id": connection.pk,
        "connection_name": connection.name,
        "direction": "sent",
        "type": "po_to_so",
        "dt_sent": dt_now,
        "remote_order_id": None,
        "remote_order_ida": "",
        "status": "queued",
    })
    refs["links"] = links
    purchase.refs = refs
    purchase.save(update_fields=["refs", "dt_modified", "version"])

    logger.info(
        "PO→SO bundle created: purchase=%s bundle=%s uuid=%s lines=%d",
        purchase.pk, bundle.pk, bundle_uuid, len(lines),
    )

    return {
        "bundle_id": bundle.pk,
        "bundle_uuid": bundle_uuid,
        "purchase_id": purchase.pk,
        "purchase_ida": getattr(purchase, "ida", ""),
        "connection_id": connection.pk,
        "line_count": len(lines),
    }
