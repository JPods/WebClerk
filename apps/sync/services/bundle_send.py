"""
Bundle send handler — processes Pending records with purpose=sync.bundle_out.

Called by the Celery pending processor. Sends the payload to the Connection's
endpoint, stamps dt_processed on acknowledgment.

Features:
  - Idempotency: sends pending.uuid so receiver deduplicates
  - Encryption: payload encrypted with connection's shared key
  - Sequence: sends pending.sequence for ordered processing
  - Large payloads: separated into encrypted files with path+key
"""

import time
import requests

from apps.sync.models.connection import Connection
from apps.sync.models.bundle import Bundle
from apps.core.models.pending import Pending
from apps.sync.services.bundle_crypto import encrypt_payload


def handle_bundle_out(pending: Pending) -> bool:
    """Send a bundle to the connected system.

    Returns True if acknowledged, False if delivery failed.
    """
    config = pending.config or {}
    connection_id = config.get("connection_id")
    if not connection_id:
        _log_attempt(pending, "no connection_id in config")
        return False

    try:
        connection = Connection.objects.get(id=connection_id, is_active=True)
    except Connection.DoesNotExist:
        _log_attempt(pending, f"connection {connection_id} not found")
        return False

    conn_config = connection.config or {}
    endpoint = conn_config.get("endpoint")
    key = conn_config.get("key")

    if not endpoint:
        _log_attempt(pending, "no endpoint in connection config")
        return False
    if not key:
        _log_attempt(pending, "no key in connection config")
        return False

    # Build the outgoing payload
    payload = config.get("payload", {})
    echo = config.get("echo", "")
    is_test = config.get("test", False)

    # Encrypt the payload
    encrypted_envelope = encrypt_payload(payload, key)

    body = {
        "idempotency_key": str(pending.uuid),
        "sequence": pending.sequence,
        "encrypted_payload": encrypted_envelope,
        "echo": echo,
        "test": is_test,
        "dt_sent": int(time.time() * 1000),
    }

    headers = {
        "Content-Type": "application/json",
        "X-Sync-Key": key,
    }

    try:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=30)
    except requests.RequestException as e:
        _log_attempt(pending, f"connection error: {e}")
        return False

    if resp.status_code != 200:
        _log_attempt(pending, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return False

    resp_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

    # Check for ack — may be at top level or inside wcapi data envelope
    ack_data = resp_data
    if "data" in resp_data and isinstance(resp_data["data"], dict):
        ack_data = resp_data["data"]
    if not ack_data.get("ack"):
        _log_attempt(pending, f"no ack in response: {resp_data}")
        return False

    # Success — create Bundle record and stamp pending
    Bundle.objects.create(
        connection=connection,
        direction="push",
        config={"idempotency_key": str(pending.uuid), "sequence": pending.sequence},
        status="success",
        payload=payload,
        response=resp_data,
    )

    pending.mark_processed()
    _log_attempt(pending, "delivered", success=True)
    return True


def _log_attempt(pending: Pending, message: str, success: bool = False):
    """Append attempt to pending.changes and increment attempts."""
    pending.attempts = (pending.attempts or 0) + 1

    changes = pending.changes if isinstance(pending.changes, list) else []
    changes.append({
        "dt": int(time.time() * 1000),
        "attempt": pending.attempts,
        "result": "success" if success else "failed",
        "message": message,
    })
    pending.changes = changes

    fields = ["attempts", "changes", "dt_modified", "version"]
    pending.save(update_fields=fields)
