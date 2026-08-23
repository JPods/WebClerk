"""Incident signaling helpers.

Creates Bundles using the seeded safety alert Connection (name='alert', type='safety_alert')
to notify webclerk.com (or equivalent) of local assaults/incidents. Review/ack flow applies.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import time
from django.apps import apps

from .email_verification import _mask_config  # reuse masking helper
from .standards import normalize_severity, alert_category_for_event, ALERT_CATEGORY_SETTINGS


def trigger_safety_alert(event_type: str, details: Dict[str, Any] | None = None, severity: str = "info") -> Dict[str, Any]:
    """Create an Bundle using the alert Connection with a pending review response.

    Returns { ok, bundle_id, error? }.
    """
    Connection = apps.get_model("sync", "Connection")
    Bundle = apps.get_model("sync", "Bundle")

    conn = Connection.objects.filter(name="alert", type="safety_alert").first()
    if not conn:
        return {"ok": False, "error": "no_alert_connection"}

    started = time.perf_counter()
    sev = normalize_severity(severity)
    category = alert_category_for_event(event_type)
    payload = {
        "event": event_type,
        "category": category,
        "severity": sev,
        "dedupe_ms": ALERT_CATEGORY_SETTINGS.get(category, {}).get("dedupe_ms", 60000),
        "details": details or {},
    }
    cfg = getattr(conn, "config", {}) or {}
    masked_cfg = _mask_config(cfg)
    resp = {
        "provider": "safety_alert",
        "status": "raised",
        "review": {"status": "pending"},
    }
    try:
        ex = Bundle.objects.create(
            connection=conn,
            direction="outbound",
            config=masked_cfg,
            status="ok",
            response=resp,
            duration=int((time.perf_counter() - started) * 1000),
            payload=payload,
            size=len(str(payload)),
        )
        return {"ok": True, "bundle_id": getattr(ex, "id", None)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
