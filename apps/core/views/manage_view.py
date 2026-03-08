"""
WCAPI Manage endpoint — administrative operations.

POST /wcapi/manage/
Body: { "action": "<action_name>", "params": { ... } }

Actions:
  generate_kanban_projects  — bulk-create Project records with sequential kanban dates
  get_receivable_aging      — return per-customer aging summary for open AR ledgers
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone as dt_tz
from decimal import Decimal
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


def _get_receivable_aging(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return per-customer aging summary for all open AR ledger records.

    params (all optional):
        as_of_date  – ISO date string (default: today)
        min_balance – Minimum absolute balance to include (default 0)

    Returns:
        { as_of_date, totals: {...}, rows: [ { org_id, org_name, ... } ] }
    """
    from django.apps import apps as dj_apps
    from django.db import models as dj_models
    from apps.accounts.services.ledger_balance import AGING_PERIODS

    Ledger = dj_apps.get_model('accounts', 'Ledger')
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')

    # Parse optional as_of_date
    as_of_str = params.get('as_of_date')
    if as_of_str:
        from django.utils.dateparse import parse_date
        as_of = parse_date(as_of_str)
        if as_of is None:
            raise ValueError(f"Invalid as_of_date: {as_of_str}")
    else:
        as_of = date.today()

    min_balance = Decimal(str(params.get('min_balance', 0)))

    # ── Fetch all open AR ledgers with org FK ──────────────────────────
    ledgers = (
        Ledger.objects
        .filter(source='AR', is_settled=False)
        .exclude(value_available=0)
        .exclude(value_available__isnull=True)
        .values('org_id', 'dt_due', 'value_available', 'parent_id', 'model_name')
    )

    # ── Build per-org buckets ──────────────────────────────────────────
    org_data: Dict[int, Dict[str, Any]] = {}

    for rec in ledgers:
        oid = rec['org_id']
        if oid is None:
            continue

        if oid not in org_data:
            org_data[oid] = {
                'future': Decimal('0'),
                'current': Decimal('0'),
                'period_1': Decimal('0'),
                'period_2': Decimal('0'),
                'period_3': Decimal('0'),
                'total': Decimal('0'),
                'count': 0,
            }

        bucket = org_data[oid]
        value = Decimal(str(rec['value_available'] or 0))
        bucket['total'] += value
        bucket['count'] += 1

        dt_due = rec['dt_due']
        if dt_due is None:
            bucket['current'] += value
            continue

        if isinstance(dt_due, datetime):
            due_date = dt_due.date()
        else:
            due_date = dt_due

        days = (as_of - due_date).days
        if days < -30:
            bucket['future'] += value
        elif days < 0:
            bucket['current'] += value
        elif days < 30:
            bucket['period_1'] += value
        elif days < 60:
            bucket['period_2'] += value
        else:
            bucket['period_3'] += value

    # ── Resolve org names in bulk ──────────────────────────────────────
    org_ids = list(org_data.keys())
    org_names: Dict[int, str] = {}
    if org_ids:
        for o in OrgBase.objects.filter(id__in=org_ids).values('id', 'name'):
            org_names[o['id']] = o['name'] or f"Org #{o['id']}"

    # ── Build result rows ──────────────────────────────────────────────
    rows = []
    grand = {
        'future': Decimal('0'), 'current': Decimal('0'),
        'period_1': Decimal('0'), 'period_2': Decimal('0'),
        'period_3': Decimal('0'), 'total': Decimal('0'), 'count': 0,
    }

    for oid, bucket in org_data.items():
        if abs(bucket['total']) < min_balance:
            continue
        row = {
            'org_id': oid,
            'org_name': org_names.get(oid, f"Org #{oid}"),
            'future': float(bucket['future']),
            'current': float(bucket['current']),
            'period_1': float(bucket['period_1']),
            'period_2': float(bucket['period_2']),
            'period_3': float(bucket['period_3']),
            'total': float(bucket['total']),
            'count': bucket['count'],
        }
        rows.append(row)
        for k in ('future', 'current', 'period_1', 'period_2', 'period_3', 'total'):
            grand[k] += bucket[k]
        grand['count'] += bucket['count']

    # Sort by total descending (biggest balances first)
    rows.sort(key=lambda r: r['total'], reverse=True)

    return {
        'as_of_date': as_of.isoformat(),
        'totals': {k: float(v) for k, v in grand.items()},
        'rows': rows,
    }


_ACTION_DISPATCH = {
    "generate_kanban_projects": _generate_kanban_projects,
    "get_receivable_aging": _get_receivable_aging,
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
