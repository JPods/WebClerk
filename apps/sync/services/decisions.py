"""Decision workflow helpers for Exchanges.

Adds simple accept/reject operations that update the target resource using the
normalized response on the Exchange.response and marks the review state.
"""

from __future__ import annotations

from typing import Any, Dict

from django.apps import apps
from django.utils import timezone


def _now_ms() -> int:
    from django.utils import timezone
    return int(timezone.now().timestamp() * 1000)


def accept_email_verification(exchange_id: int, actor_id: int | None = None) -> Dict[str, Any]:
    Exchange = apps.get_model("sync", "Exchange")
    Email = apps.get_model("communications", "Email")
    ex = Exchange.objects.filter(pk=exchange_id).first()
    if not ex:
        return {"ok": False, "error": "exchange_not_found"}
    resp = getattr(ex, "response", {}) or {}
    review = resp.setdefault("review", {})
    email_addr = (getattr(ex, "payload", {}) or {}).get("email")
    if not email_addr:
        return {"ok": False, "error": "payload_missing_email"}
    obj = Email.objects.filter(email=email_addr).first()
    if not obj:
        return {"ok": False, "error": "email_not_found"}
    # Mark verified based on deliverability; project-specific rule can be adjusted
    deliverability = resp.get("deliverability", "unknown")
    is_verified = deliverability in {"valid", "deliverable"}
    meta = getattr(obj, "metadata", {}) or {}
    ver = meta.setdefault("versioning", {}).setdefault("validation", {})
    ver.update({
        "provider": resp.get("provider", "stub"),
        "status": resp.get("status", "accepted"),
        "deliverability": deliverability,
        "reason": resp.get("reason", ""),
        "review": {"status": "accepted", "by": actor_id or 0, "dt": _now_ms(), "exchange_id": exchange_id},
    })
    obj.metadata = meta  # type: ignore[attr-defined]
    setattr(obj, "is_verified", is_verified)
    obj.save(update_fields=["metadata", "is_verified", "dt_modified", "version"])  # type: ignore[attr-defined]
    review.update({"status": "accepted", "by": actor_id or 0, "dt": _now_ms()})
    setattr(ex, "response", resp)
    setattr(ex, "status", "accepted")
    ex.save(update_fields=["response", "status"])  # type: ignore[attr-defined]
    return {"ok": True, "verified": is_verified}


def reject_exchange(exchange_id: int, reason: str = "", actor_id: int | None = None) -> Dict[str, Any]:
    Exchange = apps.get_model("sync", "Exchange")
    ex = Exchange.objects.filter(pk=exchange_id).first()
    if not ex:
        return {"ok": False, "error": "exchange_not_found"}
    resp = getattr(ex, "response", {}) or {}
    review = resp.setdefault("review", {})
    review.update({"status": "rejected", "reason": reason, "by": actor_id or 0, "dt": _now_ms()})
    setattr(ex, "response", resp)
    setattr(ex, "status", "rejected")
    ex.save(update_fields=["response", "status"])  # type: ignore[attr-defined]
    return {"ok": True}
