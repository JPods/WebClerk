"""Provider-agnostic Domain Verification service (stub).

Resolves a Connection of type 'domain_verification' and records an Exchange
with a normalized response. No network I/O in stub mode.
"""

from __future__ import annotations

import time
from typing import Any, Dict, cast

from django.apps import apps
from .email_verification import _mask_config


def _normalize_result(provider: str, raw: dict | None = None) -> Dict[str, Any]:
    raw = raw or {"status": "stubbed"}
    return {
        "provider": provider or "stub",
        "status": raw.get("status", "unknown"),
        "reachable": raw.get("reachable", None),
        "reason": raw.get("reason", ""),
    }


def get_verification_connection(name: str | None = None):
    Connection = apps.get_model("sync", "Connection")
    qs = Connection.objects.filter(type="domain_verification")
    if name:
        return qs.filter(name=name).first() or qs.first()
    return qs.first()


def verify_domain_via_connection(path: str, connection_name: str | None = None) -> Dict[str, Any]:
    Exchange = apps.get_model("sync", "Exchange")

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
    payload = {"path": path}
    masked_cfg = _mask_config(cfg)
    status = "ok"

    raw_result: dict = {"status": "stubbed", "reachable": None, "reason": "stub_mode"}
    normalized = _normalize_result(provider or "stub", raw_result)

    duration_ms = int((time.perf_counter() - started) * 1000)

    exchange_id = None
    try:
        e = Exchange.objects.create(
            connection_id=cast(Any, conn),
            direction="outbound",
            config=masked_cfg,
            status=status,
            response={**normalized, "review": {"status": "pending"}},
            duration=duration_ms,
            payload=payload,
            size=len(str(payload)) + len(str(normalized)),
        )
        exchange_id = getattr(e, "id", None)
    except Exception:
        pass

    return {"ok": True, "result": normalized, "exchange_id": exchange_id}
