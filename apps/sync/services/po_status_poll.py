"""
PO Status Poll — Buyer queries vendor for SO status updates.

The buyer calls this to poll the vendor's WC3 instance for the
current status of the SO that was created from their PO bundle.
Updates the local PO's refs.links.bundle[] entry with latest status.
"""
from __future__ import annotations

import copy
import logging
from typing import Any, Dict

import requests as http_requests

from apps.sync.models.bundle import Bundle
from apps.sync.models.connection import Connection
from apps.transactions.models import Purchase

logger = logging.getLogger(__name__)


def poll_bundle_status(
    purchase_id: int,
    bundle_uuid: str,
) -> Dict[str, Any]:
    """Poll the vendor for current SO status and update local PO.

    Args:
        purchase_id: Local Purchase record PK
        bundle_uuid: The bundle UUID used as tracking reference

    Returns:
        The vendor's status response, or error dict
    """
    try:
        purchase = Purchase.objects.get(pk=purchase_id)
    except Purchase.DoesNotExist:
        raise ValueError(f"Purchase #{purchase_id} not found")

    # Find the outbound bundle
    bundle = Bundle.objects.filter(
        config__bundle_uuid=bundle_uuid,
        direction="push",
    ).first()

    if not bundle:
        raise ValueError(f"Bundle {bundle_uuid} not found locally")

    connection = bundle.connection
    conn_config = connection.config if isinstance(connection.config, dict) else {}
    endpoint = conn_config.get("endpoint", "")
    key = conn_config.get("key", "")

    if not endpoint or not key:
        raise ValueError("Connection has no endpoint or key configured")

    # Build the status URL from the base endpoint
    # endpoint is typically https://vendor.example.com/wcapi/sync/receive/
    # We need https://vendor.example.com/wcapi/sync/bundle/<uuid>/status/
    base = endpoint.rstrip("/")
    if base.endswith("/receive"):
        base = base[:-len("/receive")]
    status_url = f"{base}/bundle/{bundle_uuid}/status/"

    headers = {
        "X-Sync-Key": key,
    }

    try:
        resp = http_requests.get(status_url, headers=headers, timeout=15)
    except http_requests.RequestException as e:
        raise ValueError(f"Connection error polling vendor: {e}")

    if resp.status_code != 200:
        raise ValueError(f"Vendor returned HTTP {resp.status_code}: {resp.text[:200]}")

    status_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

    # Update local PO refs.links.bundle[] with latest status
    refs = copy.deepcopy(purchase.refs) if isinstance(purchase.refs, dict) else {}
    bundle_links = refs.get("links", {}).get("bundle", [])
    for bl in bundle_links:
        if bl.get("bundle_uuid") == bundle_uuid:
            bl["remote_order_id"] = status_data.get("order_id")
            bl["remote_order_ida"] = status_data.get("order_ida", "")
            bl["status"] = status_data.get("status", bl.get("status"))
            if status_data.get("dt_approved"):
                bl["dt_approved"] = status_data["dt_approved"]
    refs.setdefault("links", {})["bundle"] = bundle_links
    purchase.refs = refs
    purchase.save(update_fields=["refs", "dt_modified", "version"])

    logger.info(
        "PO status poll: purchase=%s uuid=%s vendor_status=%s",
        purchase.pk, bundle_uuid, status_data.get("status"),
    )

    return status_data
