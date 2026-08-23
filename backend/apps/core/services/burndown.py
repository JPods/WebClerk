"""
Sprint burndown calculation.

Burndown = weighted remaining work across all actions in a sprint.
Weight = difficulty (1-5). Work = 100 - percent_complete.
Remaining = sum(difficulty × (100 - percent_complete)) for each action.

Usage:
    from apps.core.services.burndown import calculate_burndown
    data = calculate_burndown(project_id=50)
    # Returns: {
    #   "sprint": "MOA W31",
    #   "dt_start": 1785...,
    #   "dt_end": 1786...,
    #   "total_points": 2400,
    #   "remaining_points": 800,
    #   "percent_complete": 67,
    #   "ideal": [{"dt": "2026-07-29", "points": 2400}, ...],
    #   "actions": [{"id": 31044, "action": "...", "difficulty": 3, "percent_complete": 50, "points_remaining": 150}, ...]
    # }
"""

import datetime
import logging

logger = logging.getLogger("core.burndown")


def calculate_burndown(project_id: int) -> dict:
    """Calculate burndown data for a sprint project."""
    from apps.core.models.action import Action
    from apps.transactions.models.project import Project

    try:
        project = Project.objects.get(id=project_id, is_active=True)
    except Project.DoesNotExist:
        return {"error": f"Project {project_id} not found"}

    # Get all active actions for this project
    actions = Action.objects.filter(
        project_id=project_id,
        is_active=True,
        is_deleted=False,
    ).values(
        "id", "ida", "action", "difficulty", "percent_complete",
        "status", "dt_start", "dt_deadline", "duration", "assigned_to",
    )

    action_list = []
    total_points = 0
    remaining_points = 0

    for a in actions:
        difficulty = max(1, a["difficulty"] or 1)
        pct = min(100, max(0, a["percent_complete"] or 0))
        task_total = difficulty * 100
        task_remaining = difficulty * (100 - pct)

        total_points += task_total
        remaining_points += task_remaining

        action_name = ""
        if isinstance(a["action"], dict):
            action_name = a["action"].get("en", "")
        elif isinstance(a["action"], str):
            action_name = a["action"]

        assigned = ""
        at = a["assigned_to"]
        if isinstance(at, str):
            assigned = at
        elif isinstance(at, dict):
            assigned = at.get("lead", "")
        elif isinstance(at, list) and at:
            assigned = at[0].get("name", "") if isinstance(at[0], dict) else str(at[0])

        # Duration in days — from field or calculated from dates
        duration = a["duration"]
        if not duration and a["dt_start"] and a["dt_deadline"]:
            try:
                ds = a["dt_start"]
                de = a["dt_deadline"]
                if isinstance(ds, (int, float)) and isinstance(de, (int, float)):
                    duration = max(1, round((de - ds) / 86400000))
            except Exception:
                pass

        action_list.append({
            "id": a["id"],
            "ida": a["ida"],
            "action": action_name,
            "difficulty": difficulty,
            "percent_complete": pct,
            "duration": duration,
            "points_total": task_total,
            "points_remaining": task_remaining,
            "status": a["status"],
            "assigned_to": assigned,
        })

    # Sprint dates from project
    dt_start = _ms_to_date(project.dt_start if hasattr(project, 'dt_start') else None)
    dt_end = _ms_to_date(project.dt_deadline if hasattr(project, 'dt_deadline') else None)

    # If project doesn't have dates, try to derive from actions
    if not dt_start or not dt_end:
        action_starts = [a["dt_start"] for a in actions if a["dt_start"]]
        action_ends = [a["dt_deadline"] for a in actions if a["dt_deadline"]]
        if action_starts:
            dt_start = dt_start or _ms_to_date(min(action_starts))
        if action_ends:
            dt_end = dt_end or _ms_to_date(max(action_ends))

    # Build ideal burndown line (linear from total to 0)
    ideal = []
    if dt_start and dt_end and total_points > 0:
        days = max(1, (dt_end - dt_start).days)
        for i in range(days + 1):
            day = dt_start + datetime.timedelta(days=i)
            ideal_remaining = total_points * (1 - i / days)
            ideal.append({
                "dt": day.isoformat(),
                "points": round(ideal_remaining),
            })

    overall_pct = round((1 - remaining_points / total_points) * 100) if total_points > 0 else 0

    return {
        "project_id": project_id,
        "sprint": project.name or f"Project {project_id}",
        "dt_start": dt_start.isoformat() if dt_start else None,
        "dt_end": dt_end.isoformat() if dt_end else None,
        "total_points": total_points,
        "remaining_points": remaining_points,
        "percent_complete": overall_pct,
        "action_count": len(action_list),
        "ideal": ideal,
        "actions": sorted(action_list, key=lambda a: a["points_remaining"], reverse=True),
    }


def _ms_to_date(ms) -> datetime.date | None:
    """Convert millisecond timestamp to date."""
    if not ms or not isinstance(ms, (int, float)) or ms <= 0:
        return None
    try:
        return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).date()
    except (ValueError, OSError):
        return None
