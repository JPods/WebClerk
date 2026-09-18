"""
PO → SO Cross-Instance Bundle API Endpoints

Three endpoints for the complete buyer↔vendor cycle:

1. POST /wcapi/sync/po-to-so/<purchase_id>/
   Buyer creates and sends a bundle from their PO to the vendor.

2. POST /wcapi/sync/bundle/<bundle_uuid>/approve/
   Vendor approves the received SO. Sends SO id back to buyer.

3. GET /wcapi/sync/bundle/<bundle_uuid>/status/
   Buyer polls vendor for current SO status and delivery updates.
"""
from __future__ import annotations

import copy
import logging
import time

import requests as http_requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import allow_write
from apps.sync.models.bundle import Bundle
from apps.sync.models.connection import Connection
from apps.sync.services.bundle_crypto import encrypt_payload
from apps.sync.services.po_to_so_bundle import create_po_so_bundle
from apps.sync.services.bundle_to_order import unpack_po_to_so_bundle, approve_bundle_order
from apps.transactions.models import Purchase, Order

logger = logging.getLogger(__name__)


@allow_write
class POToSOSendView(APIView):
    """Buyer: create bundle from PO and send to vendor's WC3 instance.

    POST /wcapi/sync/po-to-so/<purchase_id>/
    Body: {"connection_id": <int>}

    Flow:
      1. Create bundle payload (cost→price mapping)
      2. POST to vendor's /wcapi/sync/receive/ endpoint
      3. Vendor's receive handler calls unpack_po_to_so_bundle
      4. Return bundle_uuid as tracking reference
    """

    def post(self, request, pk=None):
        purchase_id = pk
        connection_id = (request.data or {}).get("connection_id")
        if not connection_id:
            return Response(
                {"detail": "connection_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the bundle
        try:
            result = create_po_so_bundle(
                purchase_id=int(purchase_id),
                connection_id=int(connection_id),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Send to vendor
        bundle = Bundle.objects.get(pk=result["bundle_id"])
        connection = Connection.objects.get(pk=connection_id)
        conn_config = connection.config if isinstance(connection.config, dict) else {}
        endpoint = conn_config.get("endpoint")
        key = conn_config.get("key")

        if not endpoint or not key:
            # Bundle created but not sent — vendor can pull later
            bundle.status = "queued"
            bundle.save(update_fields=["status", "dt_modified", "version"])
            result["sent"] = False
            result["detail"] = "Bundle created but connection has no endpoint/key configured"
            return Response(result, status=status.HTTP_201_CREATED)

        # Encrypt and send
        payload = bundle.get_payload()
        encrypted = encrypt_payload(payload, key)
        dt_now = int(time.time() * 1000)

        body = {
            "idempotency_key": result["bundle_uuid"],
            "sequence": 0,
            "encrypted_payload": encrypted,
            "dt_sent": dt_now,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Sync-Key": key,
        }

        try:
            resp = http_requests.post(
                endpoint, json=body, headers=headers, timeout=30,
            )
        except http_requests.RequestException as e:
            bundle.status = "error"
            bundle.response = {"error": str(e), "dt_attempted": dt_now}
            bundle.save(update_fields=["status", "response", "dt_modified", "version"])
            result["sent"] = False
            result["detail"] = f"Connection error: {e}"
            return Response(result, status=status.HTTP_201_CREATED)

        if resp.status_code != 200:
            bundle.status = "error"
            bundle.response = {"http_status": resp.status_code, "body": resp.text[:500]}
            bundle.save(update_fields=["status", "response", "dt_modified", "version"])
            result["sent"] = False
            result["detail"] = f"Vendor returned HTTP {resp.status_code}"
            return Response(result, status=status.HTTP_201_CREATED)

        resp_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        ack_data = resp_data.get("data", resp_data) if isinstance(resp_data, dict) else {}

        if not ack_data.get("ack"):
            bundle.status = "warning"
            bundle.response = resp_data
            bundle.save(update_fields=["status", "response", "dt_modified", "version"])
            result["sent"] = False
            result["detail"] = "Vendor did not acknowledge"
            return Response(result, status=status.HTTP_201_CREATED)

        # Success
        bundle.status = "success"
        bundle.response = resp_data
        bundle.dt_processed = dt_now
        bundle.save(update_fields=["status", "response", "dt_processed", "dt_modified", "version"])

        result["sent"] = True
        result["remote_bundle_id"] = ack_data.get("bundle_id")
        return Response(result, status=status.HTTP_201_CREATED)


@allow_write
class BundleApproveView(APIView):
    """Vendor: approve the SO created from a received bundle.

    POST /wcapi/sync/bundle/<bundle_uuid>/approve/

    On approval:
      - Order status → released
      - If the sending Connection has a callback endpoint, POST the
        SO id back to the buyer's WC3 instance
    """

    def post(self, request, bundle_uuid=None):
        try:
            result = approve_bundle_order(bundle_uuid)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Attempt callback to buyer with SO id
        connection_id = result.get("connection_id")
        if connection_id:
            try:
                connection = Connection.objects.get(pk=connection_id)
                conn_config = connection.config if isinstance(connection.config, dict) else {}
                callback_url = conn_config.get("callback_endpoint")
                key = conn_config.get("key")

                if callback_url and key:
                    callback_body = {
                        "bundle_uuid": bundle_uuid,
                        "order_id": result["order_id"],
                        "order_ida": result["order_ida"],
                        "status": "approved",
                        "dt_approved": int(time.time() * 1000),
                    }
                    callback_headers = {
                        "Content-Type": "application/json",
                        "X-Sync-Key": key,
                    }
                    try:
                        resp = http_requests.post(
                            callback_url, json=callback_body,
                            headers=callback_headers, timeout=15,
                        )
                        result["callback_sent"] = resp.status_code == 200
                    except http_requests.RequestException:
                        result["callback_sent"] = False
            except Connection.DoesNotExist:
                pass

        return Response(result, status=status.HTTP_200_OK)


class BundleStatusView(APIView):
    """Buyer: poll vendor for current status of the SO.

    GET /wcapi/sync/bundle/<bundle_uuid>/status/

    Returns the Order's current status, delivery info, and any
    updates since the bundle was sent.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, bundle_uuid=None):
        # Check X-Sync-Key
        key = request.headers.get("X-Sync-Key", "")
        if not key:
            return Response(
                {"detail": "missing X-Sync-Key"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Find the bundle
        bundle = Bundle.objects.filter(
            config__bundle_uuid=bundle_uuid,
            direction="pull",
        ).first()

        if not bundle:
            return Response(
                {"detail": "bundle not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify key matches connection
        connection = bundle.connection
        conn_config = connection.config if isinstance(connection.config, dict) else {}
        if conn_config.get("key") != key:
            return Response(
                {"detail": "invalid key"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get the Order
        response = bundle.response or {}
        order_id = response.get("order_id")

        if not order_id:
            return Response({
                "bundle_uuid": bundle_uuid,
                "status": "pending",
                "detail": "Order not yet created from bundle",
            })

        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            return Response({
                "bundle_uuid": bundle_uuid,
                "status": "error",
                "detail": f"Order #{order_id} not found",
            })

        # Build status response
        totals = order.totals if isinstance(order.totals, dict) else {}
        flow = order.flow if isinstance(order.flow, dict) else {}

        status_data = {
            "bundle_uuid": bundle_uuid,
            "order_id": order.pk,
            "order_ida": getattr(order, "ida", ""),
            "status": order.status,
            "dt_needed": order.dt_needed,
            "ship_via": order.ship_via,
            "totals": {
                "subtotal": totals.get("subtotal", 0),
                "tax": totals.get("tax", 0),
                "shipping": totals.get("shipping", 0),
                "total": totals.get("total", 0),
            },
            "approved": response.get("approved", False),
            "dt_approved": response.get("dt_approved"),
            "flow_children": flow.get("children", []),
        }

        return Response(status_data, status=status.HTTP_200_OK)


@allow_write
class BundleCallbackView(APIView):
    """Buyer: receive callback from vendor with SO approval/status update.

    POST /wcapi/sync/bundle/callback/

    Body: {bundle_uuid, order_id, order_ida, status, dt_approved}
    Updates the local Purchase's refs.links.bundle[] entry.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        key = request.headers.get("X-Sync-Key", "")
        if not key:
            return Response(
                {"detail": "missing X-Sync-Key"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = request.data or {}
        bundle_uuid = data.get("bundle_uuid")
        if not bundle_uuid:
            return Response(
                {"detail": "bundle_uuid required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find our outbound bundle
        bundle = Bundle.objects.filter(
            config__bundle_uuid=bundle_uuid,
            direction="push",
        ).first()

        if not bundle:
            return Response(
                {"detail": "bundle not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify key
        connection = bundle.connection
        conn_config = connection.config if isinstance(connection.config, dict) else {}
        if conn_config.get("key") != key:
            return Response(
                {"detail": "invalid key"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Update the Purchase's refs.links.bundle[] entry
        config = bundle.config or {}
        purchase_id = config.get("purchase_id")
        if purchase_id:
            try:
                purchase = Purchase.objects.get(pk=purchase_id)
                refs = copy.deepcopy(purchase.refs) if isinstance(purchase.refs, dict) else {}
                bundle_links = refs.get("links", {}).get("bundle", [])
                for bl in bundle_links:
                    if bl.get("bundle_uuid") == bundle_uuid:
                        bl["remote_order_id"] = data.get("order_id")
                        bl["remote_order_ida"] = data.get("order_ida", "")
                        bl["status"] = data.get("status", "approved")
                        bl["dt_approved"] = data.get("dt_approved")
                refs.setdefault("links", {})["bundle"] = bundle_links
                purchase.refs = refs
                purchase.save(update_fields=["refs", "dt_modified", "version"])
            except Purchase.DoesNotExist:
                logger.warning("Callback: purchase %s not found", purchase_id)

        return Response({"ack": True, "bundle_uuid": bundle_uuid})


class POStatusPollView(APIView):
    """Buyer: poll vendor for SO status and update local PO.

    GET /wcapi/sync/po-status/<purchase_id>/<bundle_uuid>/

    Calls the vendor's status endpoint, updates PO refs.links.bundle[].
    """

    def get(self, request, pk=None, bundle_uuid=None):
        from apps.sync.services.po_status_poll import poll_bundle_status
        try:
            result = poll_bundle_status(
                purchase_id=int(pk),
                bundle_uuid=bundle_uuid,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
