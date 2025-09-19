"""Provider-agnostic Email Verification service.

This module resolves a Connection configured for email verification, performs
the verification (stubbed by default; no external I/O), and records an
Bundle containing request/response metadata.

Connection expectations:
- Connection.type == 'email_verification'
- Connection.name (optional) selects a specific provider config. If not
  provided, the first active/available connection is used.
- Connection.config example:
    {
      "provider": "zerobounce",   # or "neverbounce", "kickbox", "stub"
      "api_key": "...",           # not used by stub
      "mode": "stub"              # forces no network I/O
    }

Bundle fields recorded:
- direction: 'outbound'
- payload: { "email": <email> }
- config: shallow copy of Connection.config with secrets masked
- response: normalized result: { provider, status, deliverability, reason, raw? }
- status: 'ok' | 'error'
- duration: milliseconds
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, cast

from django.apps import apps
from .standards import normalize_email_result


def _mask_config(cfg: dict) -> dict:
    if not isinstance(cfg, dict):
        return {}
    masked = dict(cfg)
    for k in ("api_key", "token", "secret", "password", "key"):
        if k in masked and masked[k]:
            masked[k] = "***"
    return masked


def _normalize_result(provider: str, raw: dict | None = None) -> Dict[str, Any]:
    return normalize_email_result(provider or "stub", raw or {"status": "unknown"})


def get_verification_connection(name: str | None = None):
    """Resolve a Connection for email verification.

    Strategy: prefer exact name if provided, else first Connection with
    type == 'email_verification'.
    """
    Connection = apps.get_model("sync", "Connection")
    qs = Connection.objects.filter(type="email_verification")
    if name:
        return qs.filter(name=name).first() or qs.first()
    return qs.first()


def verify_email_via_connection(email: str, connection_name: str | None = None) -> Dict[str, Any]:
    """Verify an email address via the configured Connection.

    No network calls are made in stub mode. An Bundle row is recorded with
    payload, masked config, response, status, and duration.
    """
    Bundle = apps.get_model("sync", "Bundle")

    conn = get_verification_connection(connection_name)
    if not conn:
        # Record a synthetic bundle so the attempt is visible
        return {
            "ok": False,
            "error": "no_connection",
            "result": _normalize_result("stub", {"status": "error", "reason": "no_connection"}),
        }

    cfg = getattr(conn, "config", {}) or {}
    provider = str(cfg.get("provider")) if cfg else "stub"

    started = time.perf_counter()
    payload = {"email": email}
    masked_cfg = _mask_config(cfg)
    status = "ok"

    # Stubbed provider behavior (no network I/O)
    raw_result: dict = {"status": "stubbed", "deliverability": "unknown", "reason": "stub_mode"}
    normalized = _normalize_result(provider or "stub", raw_result)

    duration_ms = int((time.perf_counter() - started) * 1000)

    bundle_id = None
    try:
        e = Bundle.objects.create(
            connection_id=cast(Any, conn),
            direction="outbound",
            config=masked_cfg,
            status=status,
            response={**normalized, "review": {"status": "pending"}},
            duration=duration_ms,
            payload=payload,
            size=len(str(payload)) + len(str(normalized)),
        )
        bundle_id = getattr(e, "id", None)
    except Exception:
        # Do not fail the call if logging fails
        pass

    return {"ok": True, "result": normalized, "bundle_id": bundle_id}
