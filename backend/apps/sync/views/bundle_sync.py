"""
Bundle sync endpoints — receive incoming bundles, validate keys.

POST /wcapi/sync/receive/
  Header: X-Sync-Key: <shared key>
  Body: {"idempotency_key": "uuid", "sequence": N, "encrypted_payload": {...}, ...}
  Returns: {"ack": true, "echo": "...", "dt_received": <ms>}

Features:
  - Idempotency: rejects duplicate bundles by idempotency_key
  - Encryption: decrypts payload using connection's shared key
  - Sequence: records sequence for ordered processing
"""

import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.sync.models.connection import Connection
from apps.sync.models.bundle import Bundle
from apps.sync.services.bundle_crypto import decrypt_payload


class BundleReceiveView(APIView):
    """Accept an incoming bundle from a connected system.

    Authentication is via X-Sync-Key header matched against the
    Connection's config.key field.  No Django user auth required —
    this is machine-to-machine.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        key = request.headers.get("X-Sync-Key", "")
        if not key:
            return Response(
                {"ack": False, "error": "missing X-Sync-Key header"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Find connection with this key
        connections = Connection.objects.filter(
            status="active",
            is_active=True,
        )
        matched = None
        for conn in connections:
            if isinstance(conn.config, dict) and conn.config.get("key") == key:
                matched = conn
                break

        if not matched:
            return Response(
                {"ack": False, "error": "invalid key"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data or {}
        dt_received = int(time.time() * 1000)
        is_test = data.get("test", False)
        idempotency_key = data.get("idempotency_key", "")
        sequence = data.get("sequence", 0)

        # Idempotency check — if we already received this bundle, re-ack
        if idempotency_key:
            existing = Bundle.objects.filter(
                connection=matched,
                config__idempotency_key=idempotency_key,
            ).first()
            if existing:
                return Response({
                    "ack": True,
                    "echo": data.get("echo", ""),
                    "dt_received": dt_received,
                    "bundle_id": str(existing.id),
                    "test": is_test,
                    "duplicate": True,
                })

        # Decrypt payload
        encrypted_envelope = data.get("encrypted_payload")
        if encrypted_envelope and isinstance(encrypted_envelope, dict):
            try:
                payload = decrypt_payload(encrypted_envelope, key)
            except Exception as e:
                return Response(
                    {"ack": False, "error": f"decryption failed: {e}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Unencrypted fallback (legacy or test)
            payload = data.get("payload", data)

        # Detect bundle_uuid in payload for po_to_so tracking
        bundle_uuid = ""
        if isinstance(payload, dict):
            bundle_uuid = payload.get("bundle_uuid", "")

        # Detect model_name from payload
        bundle_model = ""
        if isinstance(payload, dict):
            bundle_model = payload.get("model_name", payload.get("type", ""))

        # Create a Bundle record for the incoming data
        bundle_config = {
            "idempotency_key": idempotency_key,
            "sequence": sequence,
        }
        if bundle_uuid:
            bundle_config["bundle_uuid"] = bundle_uuid

        bundle = Bundle.objects.create(
            connection=matched,
            direction="pull",
            model_name=bundle_model,
            config=bundle_config,
            status="success",
            response={"dt_received": dt_received, "test": is_test},
        )
        bundle.save_payload_to_disk(payload)

        # Auto-unpack po_to_so bundles into pending Orders
        unpack_result = None
        if isinstance(payload, dict) and payload.get("type") == "po_to_so" and not is_test:
            try:
                from apps.sync.services.bundle_to_order import unpack_po_to_so_bundle
                unpack_result = unpack_po_to_so_bundle(bundle)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    "Failed to unpack po_to_so bundle %s: %s", bundle.id, e
                )

        # Auto-upsert episode bundles
        episode_result = None
        if isinstance(payload, dict) and payload.get("type") == "episode" and not is_test:
            try:
                from apps.sync.services.episode_bundle import receive_episodes
                episode_result = receive_episodes(payload)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    "Failed to process episode bundle %s: %s", bundle.id, e
                )

        # Auto-process coaching feedback bundles
        coaching_result = None
        if isinstance(payload, dict) and payload.get("type") == "coaching_feedback" and not is_test:
            try:
                from apps.ai_assistant.services.support_feed import submit_coaching_feedback
                coaching_result = submit_coaching_feedback(payload.get("feedback", []))
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    "Failed to process coaching feedback bundle %s: %s", bundle.id, e
                )

        resp_data = {
            "ack": True,
            "echo": data.get("echo", ""),
            "dt_received": dt_received,
            "bundle_id": str(bundle.id),
            "test": is_test,
        }
        if unpack_result:
            resp_data["order_id"] = unpack_result.get("order_id")
            resp_data["order_ida"] = unpack_result.get("order_ida")
        if episode_result:
            resp_data["episodes"] = episode_result
        if coaching_result:
            resp_data["coaching_feedback"] = coaching_result

        return Response(resp_data)
