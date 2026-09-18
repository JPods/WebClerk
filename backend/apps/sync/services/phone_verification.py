"""Provider-agnostic Phone Verification service (stub).

Similar to email verification, this resolves a Connection configured for
phone verification and records a Bundle with a normalized response.

Connection expectations:
- Connection.type == 'phone_verification'

Bundle payload example:
  { "phone": "+15551234567" }
"""

from __future__ import annotations

import time
from typing import Any, Dict, cast

from django.apps import apps
from .email_verification import _mask_config


def _normalize_result(provider: str, raw: dict | None = None) -> Dict[str, Any]:
    raw = raw or {"status": "stubbed", "reason": "stub_mode"}
    # Minimal normalization (extend later):
    return {
        "provider": provider or "stub",
        "status": raw.get("status", "unknown"),
        "valid": raw.get("valid", None),
        "reason": raw.get("reason", ""),
    }


def get_verification_connection(name: str | None = None):
    Connection = apps.get_model("sync", "Connection")
    qs = Connection.objects.filter(type="phone_verification")
    if name:
        return qs.filter(name=name).first() or qs.first()
    return qs.first()


def verify_phone_via_connection(phone: str, connection_name: str | None = None) -> Dict[str, Any]:
    Bundle = apps.get_model("sync", "Bundle")

    conn = get_verification_connection(connection_name)
    if not conn:
        return {
            "ok": False,
            "error": "no_connection",
            "result": _normalize_result("stub", {"status": "error", "reason": "no_connection"}),
        }

    cfg = getattr(conn, "config", {}) or {}
    provider = str(cfg.get("provider")) if cfg else "stub"

    started = time.perf_counter()
    payload = {"phone": phone}
    masked_cfg = _mask_config(cfg)
    status = "ok"

    raw_result: dict = {"status": "stubbed", "valid": None, "reason": "stub_mode"}
    normalized = _normalize_result(provider or "stub", raw_result)

    duration_ms = int((time.perf_counter() - started) * 1000)

    bundle_id = None
    try:
        e = Bundle.objects.create(
            connection=cast(Any, conn),
            direction="outbound",
            model_name="contact",
            config=masked_cfg,
            status=status,
            response={**normalized, "review": {"status": "pending"}},
            duration=duration_ms,
            size=len(str(payload)) + len(str(normalized)),
        )
        e.save_payload_to_disk(payload)
        bundle_id = getattr(e, "id", None)
    except Exception:
        pass

    return {"ok": True, "result": normalized, "bundle_id": bundle_id}
