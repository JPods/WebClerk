"""
Alice Notes — Alice's persistent memory.

Two categories:
    pending   Alice's to-dos (keyword gaps, zero-result searches, data-quality
              flags, questions): an Action, purpose alice, metadata.source_agent
              alice, config.alice = {role, model, details}; status open until
              resolved (Bill, 2026-10-28: Alice's to-do belongs in Action).

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

from apps.core.models import Action, Log

logger = logging.getLogger(__name__)

CATEGORY_PURPOSE_MAP = {
    "pending": "alice",   # Action
    "log": "alice",       # Log
}

# ── Allowed role values (sub-types) per category ────────────────────
PENDING_ROLES = frozenset({
    "keyword_gap",         # keyword config missing or incomplete
    "zero_result",         # search returned 0 results
    "data_quality",        # data inconsistency detected
    "config_suggestion",   # Alice recommends a config change
    "action_required",     # general human-action-needed
    "question",            # a person asked Alice something
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
    user=None,
) -> Action | Log:
    """Create an Alice to-do (Action, purpose ``alice``) or a Log (purpose ``alice``).

    ``user`` is who is responsible for the note: the person whose request raised it. With
    none named and no request acting, it is Alice's own login.

    Parameters
    ----------
    category
        ``"pending"`` or ``"log"``.
    role
        Sub-type within the category (e.g. ``"keyword_gap"``,
        ``"search"``).  Must be in the allow-list for the category.
    name
        Human-readable summary (the Action's title; the Log's config.name).
    parent_model
        Optional canonical model key (e.g. ``"customer"``).
    details
        Arbitrary JSON payload (config.alice.details / config.details).
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
    user = user if user is not None else _alice_unless_someone_acts()

    if category == "log":
        entry = Log.write("alice", role, user=user, model_name=parent_model or "", name=name,
                          details=data)
        logger.info("Alice log written: pk=%s role=%s", entry.pk, role)
        return entry

    # Through the door, acting as the person responsible (core.models audit, 2026-10-29): the
    # one named, else the person whose request raised it, else Alice's login. A role that may
    # not make Actions does not lose the note: it is saved under Alice's login, names who
    # raised it, and created_by stays the person whose request it was (Action.save).
    from apps.core.services.door import Actor, Refused, acting_actor
    from apps.core.services.save import save_record
    record = {
        "purpose": "alice",
        "action": {"en": name},
        "description": {"en": str(data.get("description", ""))} if data.get("description") else {},
        "status": "open",
        "kanban_column": "Backlog",
        "config": {"alice": {"role": role, "model": parent_model or "", "details": data}},
        "metadata": {"agent": True, "source_agent": "alice"},
    }
    outer = acting_actor()
    actor = (Actor(user=user, kind="user", source="alice") if user is not None
             else outer if outer is not None and outer.user_id
             else Actor.system(source="alice"))
    try:
        action = save_record(actor, record, model_key="action").obj
    except Refused as refused:
        alice = _alice_login()
        if refused.status != 403 or alice is None or actor.user == alice:
            raise
        record["config"]["alice"]["details"] = {**data, "raised_by": actor.user_id}
        action = save_record(Actor(user=alice, kind="user", source="alice"), record,
                             model_key="action").obj
    logger.info("Alice to-do created: action=%s role=%s", action.pk, role)
    return action


def _alice_unless_someone_acts():
    """Alice's login when no request is acting (a task, a command); else None, so the acting
    person is recorded."""
    from apps.core.services.door import acting_actor
    actor = acting_actor()
    if actor is not None and actor.user_id:
        return None
    return _alice_login()


def _alice_login():
    """Alice's login on this instance (ALICE_WC_EMAIL), or None when it has none."""
    from django.conf import settings
    email = (getattr(settings, "ALICE_WC_EMAIL", "") or "").strip().lower()
    if not email:
        return None
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(email__iexact=email).first()


def open_alice_actions(role: str | None = None, **details):
    """Alice's open to-dos, optionally one role and matching details keys."""
    qs = Action.objects.filter(purpose="alice", status="open")
    if role:
        qs = qs.filter(config__alice__role=role)
    for key, value in details.items():
        qs = qs.filter(**{f"config__alice__details__{key}": value})
    return qs


# ── Resolve ─────────────────────────────────────────────────────────

def resolve_pending(action_id: int) -> Action:
    """Mark an Alice to-do done."""
    action = Action.objects.get(pk=action_id, purpose="alice")
    action.status = "complete"
    action.kanban_column = "Complete"
    action.dt_completed = int(timezone.now().timestamp() * 1000)
    action.save(update_fields=["status", "kanban_column", "dt_completed", "dt_modified"])
    logger.info("Alice to-do resolved: action=%s", action.pk)
    return action


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
        qs = Action.objects.filter(purpose="alice", dt_created__gte=cutoff_ms)
        if parent_model:
            qs = qs.filter(config__alice__model=parent_model)
        if role:
            qs = qs.filter(config__alice__role=role)
        if not include_resolved:
            qs = qs.filter(status="open")
        rows = list(qs.order_by("-dt_created")[:limit].values(
            "id", "action", "status", "config", "dt_created"))
        roles: dict[str, int] = {}
        for r in qs.values_list("config__alice__role", flat=True):
            roles[r or ""] = roles.get(r or "", 0) + 1
        summary += [{"category": "pending", "role": k, "count": v} for k, v in sorted(roles.items())]
        items += [{"category": "pending", "model": "action", "id": r["id"],
                   "name": (r["action"] or {}).get("en", ""),
                   "role": ((r["config"] or {}).get("alice") or {}).get("role", ""),
                   "parent_model": ((r["config"] or {}).get("alice") or {}).get("model", ""),
                   "data": ((r["config"] or {}).get("alice") or {}).get("details", {}),
                   "is_active": r["status"] == "open", "dt_created": r["dt_created"]}
                  for r in rows]
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
