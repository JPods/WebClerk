"""
Alice Notes — Alice's persistent memory.

Two categories:
    pending   Short-term action items (keyword gaps, zero-result
              searches, data-quality flags): Setting purpose alice_pending.
              ``is_active=True`` means unresolved; set ``is_active=False`` to close.

    log       What Alice observed (queries handled, config changes,
              health-check snapshots, user interactions): the one Log,
              purpose alice, action = role (Bill, 2026-10-28: logs go in the log
              model; Setting holds only the structure of the application).

Usage from any backend code::

    from apps.ai_assistant.services.notes import create_note, get_report

    create_note("pending", role="keyword_gap", parent_model="customer",
                name="Missing keyword field: phone",
                details={"field": "phone", "suggestion": "add to refs_setup"})

    report = get_report(category="pending", days=30, parent_model="customer")
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db.models import Count, Q
from django.utils import timezone

from apps.core.models import Log, Setting

logger = logging.getLogger(__name__)

CATEGORY_PURPOSE_MAP = {
    "pending": "alice_pending",   # Setting
    "log": "alice",               # Log
}

# ── Allowed role values (sub-types) per category ────────────────────
PENDING_ROLES = frozenset({
    "keyword_gap",         # keyword config missing or incomplete
    "zero_result",         # search returned 0 results
    "data_quality",        # data inconsistency detected
    "config_suggestion",   # Alice recommends a config change
    "action_required",     # general human-action-needed
})

LOG_ROLES = frozenset({
    "search",              # search query executed
    "search_feedback",     # user rated a search result
    "config_change",       # keyword / denorm config changed
    "health_check",        # health scoring run
    "user_interaction",    # chat / ask interaction
    "system",              # internal system event
})

VALID_ROLES = {
    "pending": PENDING_ROLES,
    "log": LOG_ROLES,
}


# ── Create ──────────────────────────────────────────────────────────

def create_note(
    category: str,
    *,
    role: str,
    name: str,
    parent_model: str | None = None,
    details: dict[str, Any] | None = None,
) -> Setting | Log:
    """Create a pending Setting (``alice_pending``) or a Log (purpose ``alice``).

    Parameters
    ----------
    category
        ``"pending"`` or ``"log"``.
    role
        Sub-type within the category (e.g. ``"keyword_gap"``,
        ``"search"``).  Must be in the allow-list for the category.
    name
        Human-readable summary (stored in ``Setting.name``).
    parent_model
        Optional canonical model key (e.g. ``"customer"``).
    details
        Arbitrary JSON payload stored in ``Setting.data``.
    """
    purpose = CATEGORY_PURPOSE_MAP.get(category)
    if purpose is None:
        raise ValueError(
            f"Invalid category '{category}'. "
            f"Choose from: {sorted(CATEGORY_PURPOSE_MAP)}"
        )

    allowed = VALID_ROLES.get(category, frozenset())
    if role not in allowed:
        raise ValueError(
            f"Invalid role '{role}' for category '{category}'. "
            f"Choose from: {sorted(allowed)}"
        )

    data = dict(details) if details else {}
    data.setdefault("created_by", "alice")

    if category == "log":
        entry = Log.write("alice", role, model_name=parent_model or "", name=name, details=data)
        logger.info("Alice log written: pk=%s role=%s", entry.pk, role)
        return entry

    data.setdefault("category", category)

    # Settings refuse creation without authorization; a note is Alice's own record. Until
    # 2026-09-27 this save was refused on every call and each caller swallowed the refusal,
    # so no note reached Alice (found building R3's over-receipt flag).
    setting = Setting.authorized_create(
        name=name,
        purpose=purpose,
        role=role,
        parent_model=parent_model or "",
        config=data,
        is_active=True,
    )
    logger.info("Alice %s note created: pk=%s role=%s", category, setting.pk, role)
    return setting


# ── Resolve ─────────────────────────────────────────────────────────

def resolve_pending(setting_id: int) -> Setting:
    """Mark an ``alice_pending`` record as resolved (``is_active=False``)."""
    setting = Setting.objects.get(pk=setting_id, purpose="alice_pending")
    setting.is_active = False
    if setting.config is None:
        setting.config = {}
    setting.config["resolved_at"] = timezone.now().isoformat()
    setting.save(update_fields=["is_active", "config", "dt_modified"])
    logger.info("Alice pending resolved: pk=%s", setting.pk)
    return setting


# ── Report ──────────────────────────────────────────────────────────

def get_report(
    category: str | None = None,
    *,
    days: int = 30,
    parent_model: str | None = None,
    role: str | None = None,
    include_resolved: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Build a summary report of Alice's notes.

    Returns a dict with ``summary`` (counts by role) and ``items``
    (the most recent records, newest first).
    """
    if category and category not in CATEGORY_PURPOSE_MAP:
        raise ValueError(f"Invalid category '{category}'.")
    cutoff_ms = int((timezone.now() - timedelta(days=days)).timestamp() * 1000)
    summary: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    total = 0

    if category in (None, "pending"):
        qs = Setting.objects.filter(purpose="alice_pending", dt_created__gte=cutoff_ms)
        if parent_model:
            qs = qs.filter(parent_model=parent_model)
        if role:
            qs = qs.filter(role=role)
        if not include_resolved:
            qs = qs.filter(is_active=True)
        summary += [{"category": "pending", "role": r["role"], "count": r["count"]}
                    for r in qs.values("role").annotate(count=Count("id")).order_by("role")]
        items += [{"category": "pending", "model": "setting", "id": r["id"], "name": r["name"],
                   "role": r["role"], "parent_model": r["parent_model"], "data": r["config"],
                   "is_active": r["is_active"], "dt_created": r["dt_created"]}
                  for r in qs.order_by("-dt_created")[:limit].values(
                      "id", "name", "role", "parent_model", "config", "is_active", "dt_created")]
        total += qs.count()

    if category in (None, "log"):
        qs = Log.objects.filter(purpose="alice", dt_created__gte=cutoff_ms)
        if parent_model:
            qs = qs.filter(model_name=parent_model)
        if role:
            qs = qs.filter(action=role)
        summary += [{"category": "log", "role": r["action"], "count": r["count"]}
                    for r in qs.values("action").annotate(count=Count("id")).order_by("action")]
        items += [{"category": "log", "model": "log", "id": r["id"], "name": (r["config"] or {}).get("name", ""),
                   "role": r["action"], "parent_model": r["model_name"],
                   "data": (r["config"] or {}).get("details", {}),
                   "is_active": True, "dt_created": r["dt_created"]}
                  for r in qs.order_by("-dt_created")[:limit].values(
                      "id", "action", "model_name", "config", "dt_created")]
        total += qs.count()

    items = sorted(items, key=lambda i: i["dt_created"] or 0, reverse=True)[:limit]

    return {
        "summary": summary,
        "items": items,
        "total": total,
        "days": days,
        "filters": {
            "category": category,
            "parent_model": parent_model,
            "role": role,
            "include_resolved": include_resolved,
        },
    }


# ── Search Feedback ─────────────────────────────────────────────────

def log_search_feedback(
    *,
    rating: int,
    query: str,
    parent_model: str,
    result_count: int = 0,
    coaching: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """Log user feedback on a search and optionally flag a keyword gap.

    Parameters
    ----------
    rating
        1 (found it) or -1 (didn't find it).
    query
        The raw search string the user typed.
    parent_model
        The model being searched (e.g. ``"customer"``).
    result_count
        Number of results the search returned.
    coaching
        Optional free-text hint from the user about what would help.
    user_id
        The requesting user's pk (for per-user analytics).

    Returns
    -------
    dict with ``log_id`` and optional ``pending_id``.
    """
    details: dict[str, Any] = {
        "rating": rating,
        "query": query,
        "result_count": result_count,
        "created_by": "user",
    }
    if coaching:
        details["coaching"] = coaching
    if user_id is not None:
        details["user_id"] = user_id

    label = "positive" if rating > 0 else "negative"
    log_note = create_note(
        "log",
        role="search_feedback",
        name=f"Search feedback ({label}): {query[:80]}",
        parent_model=parent_model,
        details=details,
    )

    result: dict[str, Any] = {"log_id": log_note.pk}

    # Negative feedback → auto-create a keyword_gap pending item
    if rating < 0:
        gap_details: dict[str, Any] = {
            "query": query,
            "result_count": result_count,
            "source": "user_feedback",
            "feedback_log_id": log_note.pk,
        }
        if coaching:
            gap_details["user_coaching"] = coaching

        pending = create_note(
            "pending",
            role="keyword_gap",
            name=f"User couldn't find results: {query[:80]}",
            parent_model=parent_model,
            details=gap_details,
        )
        result["pending_id"] = pending.pk

    return result
