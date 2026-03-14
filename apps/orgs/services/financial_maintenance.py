from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.apps import apps as dj_apps
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.ledger_balance import update_org_balances
from apps.core.models.pending import Pending
from apps.orgs.models import OrgBase
from apps.orgs.models.constants import default_financial

PENDING_PURPOSE_ORG_FINANCIAL = "org_financial_maintenance"


@dataclass
class OrgFinancialUpdateResult:
    org_id: int
    status: str
    queued_pending_id: int | None = None
    error: str | None = None


def _normalize_org_type(value: str | None) -> str:
    return (value or "other").lower()


def _pending_payload(org: OrgBase, mode: str, reason: str | None = None) -> dict[str, Any]:
    now_ms = int(timezone.now().timestamp() * 1000)
    return {
        "mode": mode,
        "org_id": org.pk,
        "org_type": (org.org_type or "").lower(),
        "reason": reason or "",
        "dt_queued": now_ms,
    }


def queue_financial_maintenance_pending(org: OrgBase, mode: str, reason: str | None = None) -> Pending:
    existing = Pending.objects.filter(
        model_name="org",
        record_id=str(org.pk),
        purpose=PENDING_PURPOSE_ORG_FINANCIAL,
        dt_processed=0,
    ).first()
    if existing:
        return existing

    return Pending.objects.create(
        model_name="org",
        record_id=str(org.pk),
        purpose=PENDING_PURPOSE_ORG_FINANCIAL,
        name=f"org:{org.pk}:{mode}",
        data=_pending_payload(org=org, mode=mode, reason=reason),
    )


def _normalize_financial_defaults(org: OrgBase) -> None:
    merged = default_financial()
    raw = org.financial if isinstance(org.financial, dict) else {}

    # Minimal recursive merge to backfill default keys while preserving values.
    def merge_node(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        out = dict(base)
        for key, value in overlay.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key] = merge_node(out[key], value)
            else:
                out[key] = value
        return out

    org.financial = merge_node(merged, raw)


def update_org_financial(
    org: OrgBase,
    *,
    mode: str,
    lock_aware: bool = True,
    allow_pending_override: bool = False,
    queue_if_locked: bool = True,
    dry_run: bool = False,
    reason: str | None = None,
) -> OrgFinancialUpdateResult:
    if lock_aware and org.is_locked and not allow_pending_override:
        if queue_if_locked and not dry_run:
            pending = queue_financial_maintenance_pending(org=org, mode=mode, reason=reason)
            return OrgFinancialUpdateResult(
                org_id=org.pk,
                status="queued_locked",
                queued_pending_id=pending.pk,
            )
        return OrgFinancialUpdateResult(org_id=org.pk, status="skipped_locked")

    try:
        _normalize_financial_defaults(org)

        # Ledger-derived balances are canonical for customer/vendor orgs.
        if (org.org_type or "").lower() in {"customer", "vendor"}:
            update_org_balances(org, save=False)

        if not dry_run:
            org.save(update_fields=["financial", "dt_modified"])
        return OrgFinancialUpdateResult(org_id=org.pk, status="updated")
    except Exception as exc:  # pragma: no cover - guardrail for batch runs
        return OrgFinancialUpdateResult(org_id=org.pk, status="error", error=str(exc))


def populate_existing_org_financials(
    *,
    org_id: int | None = None,
    org_type: str | None = None,
    dry_run: bool = False,
    lock_aware: bool = True,
    queue_if_locked: bool = True,
) -> dict[str, Any]:
    qs = OrgBase.objects.all()
    if org_id:
        qs = qs.filter(pk=org_id)
    if org_type:
        qs = qs.filter(org_type=org_type)

    summary = {
        "mode": "populate",
        "total": qs.count(),
        "updated": 0,
        "updated_by_org_type": {},
        "receivables_aged": 0,
        "queued_locked": 0,
        "skipped_locked": 0,
        "errors": 0,
        "error_ids": [],
    }

    for org in qs.iterator():
        result = update_org_financial(
            org,
            mode="populate",
            lock_aware=lock_aware,
            allow_pending_override=False,
            queue_if_locked=queue_if_locked,
            dry_run=dry_run,
            reason="populate_existing_org_financials",
        )
        if result.status == "updated":
            summary["updated"] += 1
            org_type_key = _normalize_org_type(org.org_type)
            by_type = summary["updated_by_org_type"]
            by_type[org_type_key] = by_type.get(org_type_key, 0) + 1
            if org_type_key in {"customer", "vendor"}:
                summary["receivables_aged"] += 1
        elif result.status == "queued_locked":
            summary["queued_locked"] += 1
        elif result.status == "skipped_locked":
            summary["skipped_locked"] += 1
        else:
            summary["errors"] += 1
            summary["error_ids"].append(result.org_id)

    return summary


def scrub_org_financials(
    *,
    org_id: int | None = None,
    org_type: str | None = None,
    dry_run: bool = False,
    lock_aware: bool = True,
    queue_if_locked: bool = True,
) -> dict[str, Any]:
    qs = OrgBase.objects.all()
    if org_id:
        qs = qs.filter(pk=org_id)
    if org_type:
        qs = qs.filter(org_type=org_type)

    summary = {
        "mode": "scrub",
        "total": qs.count(),
        "updated": 0,
        "updated_by_org_type": {},
        "receivables_aged": 0,
        "queued_locked": 0,
        "skipped_locked": 0,
        "errors": 0,
        "error_ids": [],
    }

    for org in qs.iterator():
        result = update_org_financial(
            org,
            mode="scrub",
            lock_aware=lock_aware,
            allow_pending_override=False,
            queue_if_locked=queue_if_locked,
            dry_run=dry_run,
            reason="scrub_org_financials",
        )
        if result.status == "updated":
            summary["updated"] += 1
            org_type_key = _normalize_org_type(org.org_type)
            by_type = summary["updated_by_org_type"]
            by_type[org_type_key] = by_type.get(org_type_key, 0) + 1
            if org_type_key in {"customer", "vendor"}:
                summary["receivables_aged"] += 1
        elif result.status == "queued_locked":
            summary["queued_locked"] += 1
        elif result.status == "skipped_locked":
            summary["skipped_locked"] += 1
        else:
            summary["errors"] += 1
            summary["error_ids"].append(result.org_id)

    return summary


def process_org_financial_pending(*, limit: int = 500, dry_run: bool = False) -> dict[str, Any]:
    qs = (
        Pending.objects.filter(
            model_name="org",
            purpose=PENDING_PURPOSE_ORG_FINANCIAL,
            dt_processed=0,
        )
        .order_by("dt_created")[:limit]
    )

    summary = {
        "mode": "process_pending",
        "total": len(qs),
        "updated": 0,
        "missing_org": 0,
        "errors": 0,
        "processed_pending": 0,
    }

    for pending in qs:
        org_pk = pending.data.get("org_id")
        mode = pending.data.get("mode") or "scrub"

        try:
            with transaction.atomic():
                org = OrgBase.objects.select_for_update().filter(pk=org_pk).first()
                if not org:
                    summary["missing_org"] += 1
                    if not dry_run:
                        pending.mark_processed(save=True)
                        summary["processed_pending"] += 1
                    continue

                result = update_org_financial(
                    org,
                    mode=mode,
                    lock_aware=True,
                    allow_pending_override=True,
                    queue_if_locked=False,
                    dry_run=dry_run,
                    reason=f"pending:{pending.pk}",
                )

                if result.status == "updated":
                    summary["updated"] += 1
                    if not dry_run:
                        pending.mark_processed(save=True)
                        summary["processed_pending"] += 1
                else:
                    summary["errors"] += 1
        except Exception:  # pragma: no cover - batch safety
            summary["errors"] += 1

    return summary


def recent_transaction_activity(*, hours: int = 24) -> dict[str, Any]:
    """Return transaction activity counts for a recent time window."""
    hours = max(1, int(hours))
    cutoff = timezone.now() - timedelta(hours=hours)
    cutoff_ms = int(cutoff.timestamp() * 1000)

    candidates = [
        ("invoice", "Invoice"),
        ("order", "Order"),
        ("purchase", "Purchase"),
        ("proposal", "Proposal"),
        ("payment", "Payment"),
        ("work_order", "WorkOrder"),
        ("workorder", "WorkOrder"),
        ("requisition", "Requisition"),
    ]

    seen_models: set[str] = set()
    by_model: dict[str, int] = {}
    total = 0

    for key, class_name in candidates:
        if class_name in seen_models:
            continue
        try:
            model = dj_apps.get_model("transactions", class_name)
        except LookupError:
            continue
        seen_models.add(class_name)
        count = model.objects.filter(dt_modified__gte=cutoff_ms).count()
        by_model[key] = count
        total += count

    return {
        "window_hours": hours,
        "total": total,
        "by_model": by_model,
    }


def write_daily_alice_observation(
    *,
    scrub_summary: dict[str, Any],
    pending_summary: dict[str, Any],
    transaction_activity: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Persist a daily maintenance observation into alice_log."""
    out = {
        "created": False,
        "setting_id": None,
    }
    if dry_run:
        return out

    unusual = {
        "locked_queued": int(scrub_summary.get("queued_locked", 0) or 0),
        "locked_skipped": int(scrub_summary.get("skipped_locked", 0) or 0),
        "scrub_errors": int(scrub_summary.get("errors", 0) or 0),
        "pending_errors": int(pending_summary.get("errors", 0) or 0),
        "missing_org": int(pending_summary.get("missing_org", 0) or 0),
    }

    needs_attention = any(v > 0 for v in unusual.values())
    attention_reasons = [k for k, v in unusual.items() if v > 0]

    details = {
        "event": "daily_org_financial_maintenance",
        "receivables_aged": {
            "updated_count": int(scrub_summary.get("receivables_aged", 0) or 0),
            "updated_by_org_type": scrub_summary.get("updated_by_org_type", {}),
        },
        "org_financial_scrub": scrub_summary,
        "org_financial_pending": pending_summary,
        "recent_transaction_activity": transaction_activity,
        "unusual": unusual,
        "needs_attention": needs_attention,
        "attention_reasons": attention_reasons,
    }

    try:
        from apps.ai_assistant.services.alice_notes import create_note

        note = create_note(
            "log",
            role="health_check",
            name="Daily org financial maintenance audit",
            parent_model="organization",
            details=details,
        )
        out["created"] = True
        out["setting_id"] = note.pk
    except Exception:
        # Logging must not block maintenance.
        out["created"] = False

    return out
