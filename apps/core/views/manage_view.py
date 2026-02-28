"""
WCAPI Manage endpoint — administrative operations.

POST /wcapi/manage/
Body: { "action": "<action_name>", "params": { ... } }

Actions:
  generate_kanban_projects  — bulk-create Project records with sequential kanban dates
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone as dt_tz
from typing import Any, Dict

from rest_framework import status
from rest_framework.views import APIView

from common.api_responses import api_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action registry
# ---------------------------------------------------------------------------

def _generate_kanban_projects(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create N Project records with evenly-spaced dt_kanban dates.

    params:
        count        – number of projects to create (required, 1-100)
        start_date   – ISO date string for the first project, e.g. "2026-03-01" (required)
        interval_days – days between each project's dt_kanban (default 7)
    """
    from apps.transactions.models.project import Project
    from django.utils.dateparse import parse_date

    count = int(params.get("count", 0))
    if not (1 <= count <= 100):
        raise ValueError("count must be 1-100")

    start_str = params.get("start_date")
    if not start_str:
        raise ValueError("start_date is required (ISO format, e.g. '2026-03-01')")

    start = parse_date(start_str)
    if start is None:
        raise ValueError(f"Invalid start_date: {start_str}")

    interval = int(params.get("interval_days", 7))
    if interval < 1:
        raise ValueError("interval_days must be >= 1")

    created_ids = []
    for i in range(count):
        dt = datetime(
            start.year, start.month, start.day,
            tzinfo=dt_tz.utc,
        ) + timedelta(days=i * interval)

        name = f"kanban-{dt.strftime('%Y-%m-%d')}"

        project = Project(
            name=name,
            dt_kanban=dt,
            status="active",
            attention="normal",
            priority=3,
        )
        project.save()
        created_ids.append(project.pk)
        logger.info("Created project %s (id=%s, dt_kanban=%s)", name, project.pk, dt.isoformat())

    return {
        "created": len(created_ids),
        "ids": created_ids,
        "start_date": start_str,
        "interval_days": interval,
    }


_ACTION_DISPATCH = {
    "generate_kanban_projects": _generate_kanban_projects,
}


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

class ManageWcapiView(APIView):
    """Administrative operations via POST { action, params }."""

    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        action_name = body.get("action")
        params = body.get("params") or {}

        if not action_name:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="missing 'action' field",
                error={"code": "missing_action"},
            )

        handler = _ACTION_DISPATCH.get(action_name)
        if handler is None:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"unknown action: {action_name}",
                error={"code": "unknown_action", "details": {"action": action_name}},
            )

        try:
            result = handler(params)
        except (ValueError, TypeError) as exc:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(exc),
                error={"code": "invalid_params", "details": {"action": action_name}},
            )
        except Exception:
            logger.exception("manage action %s failed", action_name)
            return api_response(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"action '{action_name}' failed",
                error={"code": "action_failed", "details": {"action": action_name}},
            )

        return api_response(
            data=result,
            message=f"action '{action_name}' completed",
        )
