"""Project standard dictionaries and normalization helpers.

Use these to keep consistent semantics while allowing provider-specific
details to evolve behind a stable shape.
"""

from __future__ import annotations

from typing import Any, Dict


# Severity taxonomy (lowest to highest); stable keys preferred across the project
ALERT_SEVERITY_ORDER: list[str] = [
    "info",
    "notice",
    "warning",
    "critical",
    "emergency",
]

# Default dedupe windows (milliseconds) for alert categories
ALERT_CATEGORY_SETTINGS: Dict[str, Dict[str, int]] = {
    # e.g., cluster of repeated login failures should compress noise
    "security.assault": {"dedupe_ms": 5 * 60 * 1000},
    "security.anomaly": {"dedupe_ms": 2 * 60 * 1000},
    "ops.outage": {"dedupe_ms": 60 * 1000},
    "ops.degradation": {"dedupe_ms": 60 * 1000},
    "generic": {"dedupe_ms": 60 * 1000},
}


def normalize_severity(severity: str | None) -> str:
    s = (severity or "info").lower().strip()
    return s if s in ALERT_SEVERITY_ORDER else "info"


def alert_category_for_event(event_type: str) -> str:
    et = (event_type or "").lower()
    if "assault" in et or "attack" in et:
        return "security.assault"
    if "anomaly" in et or "suspicious" in et:
        return "security.anomaly"
    if "outage" in et or "down" in et:
        return "ops.outage"
    if "slow" in et or "degrade" in et:
        return "ops.degradation"
    return "generic"


# Email verification normalization
# Map provider/raw statuses to canonical values
EMAIL_STATUS_MAP: Dict[str, str] = {
    # canonical -> same
    "valid": "valid",
    "invalid": "invalid",
    "risky": "risky",
    "unknown": "unknown",
    "deliverable": "valid",
    "undeliverable": "invalid",
    # common alternates
    "ok": "valid",
    "bad": "invalid",
    "catch_all": "risky",
}


def normalize_email_result(provider: str, raw: Dict[str, Any] | None) -> Dict[str, Any]:
    r = raw or {}
    status_raw = str(r.get("status", "unknown")).lower()
    deliverability_raw = str(r.get("deliverability", status_raw)).lower()
    status = EMAIL_STATUS_MAP.get(status_raw, status_raw if status_raw in EMAIL_STATUS_MAP.values() else "unknown")
    deliverability = EMAIL_STATUS_MAP.get(deliverability_raw, deliverability_raw if deliverability_raw in EMAIL_STATUS_MAP.values() else "unknown")
    # Choose the stronger signal between status and deliverability
    canonical = deliverability if deliverability != "unknown" else status
    return {
        "provider": provider or "stub",
        "status": canonical,
        "deliverability": canonical,
        "reason": r.get("reason", ""),
    }
