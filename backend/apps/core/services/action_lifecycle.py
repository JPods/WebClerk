"""Feature lifecycle tracking — built → tested → reworked → approved.

Alice owns the record. Allie owns the synthesis.
Claude writes built events. Bill or Claude writes tested/approved.
The Action record tracks the full lifecycle with dated transitions.

See: ~/Allie/readmes/wisdom/lifecycle-tracking.md

Established 2026-08-05.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

VALID_STATES = ("built", "tested", "reworked", "approved")


def lifecycle_record(params: dict) -> dict:
    """Create or update an Action record for a feature lifecycle event.

    Called from:
      - alice-lifecycle.py (CLI/script) via POST /wcapi/manage/
      - Claude Code sessions at session end
      - Bill via CLI

    Params:
        ida:      str — action identifier (LIFE-FEATURE-NAME)
        feature:  str — human-readable feature name
        state:    str — built, tested, reworked, approved
        by:       str — who performed this (claude, bill, alice, allie)
        details:  str — what was done
        session:  str — session identifier or date
        dt:       str — UTC timestamp
    """
    from apps.core.models import Action

    ida = params.get("ida", "")
    feature = params.get("feature", "")
    state = params.get("state", "")
    by = params.get("by", "claude")
    details = params.get("details", "")
    session = params.get("session", "")
    dt = params.get("dt", timezone.now().isoformat())

    if state not in VALID_STATES:
        raise ValueError(f"Invalid lifecycle state '{state}'. Valid: {', '.join(VALID_STATES)}")
    if not feature:
        raise ValueError("Feature name is required")
    if not ida:
        ida = f"LIFE-{feature[:60].upper().replace(' ', '-')}"

    # Find or create
    action, created = Action.objects.get_or_create(
        ida=ida,
        defaults={
            "action": {"en": f"Lifecycle: {feature}"},
            "description": f"{state} — {details}" if details else state,
            "status": _state_to_status(state),
            "config": {
                "lifecycle": {
                    "feature": feature,
                    "current_state": state,
                    "transitions": [
                        {"state": state, "by": by, "dt": dt,
                         "session": session, "details": details},
                    ],
                },
            },
        },
    )

    if not created:
        # Update existing — append transition
        config = action.config or {}
        lc = config.setdefault("lifecycle", {
            "feature": feature,
            "current_state": state,
            "transitions": [],
        })
        lc["current_state"] = state
        lc["transitions"].append({
            "state": state, "by": by, "dt": dt,
            "session": session, "details": details,
        })
        action.config = config
        action.status = _state_to_status(state)
        action.description = f"{state} — {details}" if details else state
        action.save(update_fields=["config", "status", "description"])

    logger.info(f"Lifecycle: {ida} → {state} by {by}")

    return {
        "id": action.id,
        "ida": action.ida,
        "feature": feature,
        "state": state,
        "created": created,
        "transitions": (action.config or {}).get("lifecycle", {}).get("transitions", []),
    }


def _state_to_status(state: str) -> str:
    """Map lifecycle state to Action status."""
    return {
        "built": "in_progress",
        "tested": "in_progress",
        "reworked": "in_progress",
        "approved": "completed",
    }.get(state, "in_progress")
