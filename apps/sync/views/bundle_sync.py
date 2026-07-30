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

        # Create a Bundle record for the incoming data
        bundle = Bundle.objects.create(
            connection=matched,
            direction="pull",
            config={
                "idempotency_key": idempotency_key,
                "sequence": sequence,
            },
            status="success",
            payload=payload,
            response={"dt_received": dt_received, "test": is_test},
        )

        return Response({
            "ack": True,
            "echo": data.get("echo", ""),
            "dt_received": dt_received,
            "bundle_id": str(bundle.id),
            "test": is_test,
        })
