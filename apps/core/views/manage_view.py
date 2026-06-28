"""
WCAPI Manage endpoint — administrative operations.

POST /wcapi/manage/
Body: { "action": "<action_name>", "params": { ... } }

Actions:
  post_gl_entries            — post staged GL journal entries for invoice/payment; locks record
  generate_kanban_projects  — bulk-create Project records with sequential kanban dates
  get_receivable_aging      — return per-customer aging summary for open AR ledgers
    get_tally_summary_by_period — return period totals across core transaction models
    get_tally_sales_by_customer_month — sales grouped by customer and month
    get_tally_sales_by_manufacturer_month — sales grouped by manufacturer and month
    get_tally_sales_by_customer_year — year-over-year sales grouped by customer and year
    get_tally_inventory_usage_by_month — inventory movement grouped by item and month
    get_tally_inventory_yearly_summary — yearly inventory usage and valuation summary
    get_tally_report_registry — list named tally report registry entries
    execute_tally_report — execute a report by report_key and params
    export_tally_report — export report output as csv/json content
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


def _log_tally_observation(request, action_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Persist a lightweight alice_log observation for tally usage."""
    try:
        from apps.ai_assistant.services.alice_notes import create_note

        rows = result.get("rows") if isinstance(result, dict) else []
        totals = result.get("totals") if isinstance(result, dict) else {}
        details = {
            "action": action_name,
            "start_date": params.get("start_date") or result.get("start_date"),
            "end_date": params.get("end_date") or result.get("end_date"),
            "row_count": len(rows) if isinstance(rows, list) else 0,
            "total_count": (totals or {}).get("count", 0) if isinstance(totals, dict) else 0,
            "total_amount": (totals or {}).get("total", 0) if isinstance(totals, dict) else 0,
            "missing_models": result.get("missing_models", []),
            "source": "wcapi.manage",
        }
        if getattr(request, "user", None) and request.user.is_authenticated:
            details["user_id"] = request.user.pk

        create_note(
            "log",
            role="user_interaction",
            name=f"{action_name} viewed",
            parent_model="report",
            details=details,
        )
    except Exception:
        logger.exception("Failed to write alice_log for tally action %s", action_name)


# ---------------------------------------------------------------------------
# Action registry
# ---------------------------------------------------------------------------

def _generate_kanban_projects(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create N Project records with Wednesday-aligned dt_kanban dates.

    params:
        count        – number of projects to create (required, 1-100)
        start_date   – ISO date string used to find the first Wednesday on or after it
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

    # Normalize to the first Wednesday on or after the requested start date.
    days_until_wednesday = (2 - start.weekday()) % 7
    first_wednesday = start + timedelta(days=days_until_wednesday)

    interval = int(params.get("interval_days", 7))
    if interval < 1:
        raise ValueError("interval_days must be >= 1")

    created_ids = []
    for i in range(count):
        dt = datetime(
            first_wednesday.year, first_wednesday.month, first_wednesday.day,
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
        "requested_start_date": start_str,
        "start_date": first_wednesday.isoformat(),
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


def _get_tally_summary_by_period(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return period totals across core transaction families."""
    from apps.core.services.tally_reports import get_tally_summary_by_period

    return get_tally_summary_by_period(params)


def _get_tally_sales_by_customer_month(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return sales grouped by customer and month."""
    from apps.core.services.tally_reports import get_tally_sales_by_customer_month

    return get_tally_sales_by_customer_month(params)


def _get_tally_sales_by_manufacturer_month(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return sales grouped by manufacturer and month."""
    from apps.core.services.tally_reports import get_tally_sales_by_manufacturer_month

    return get_tally_sales_by_manufacturer_month(params)


def _get_tally_sales_by_customer_year(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return year-over-year sales grouped by customer and year."""
    from apps.core.services.tally_reports import get_tally_sales_by_customer_year

    return get_tally_sales_by_customer_year(params)


def _get_tally_inventory_usage_by_month(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return inventory usage grouped by item and month."""
    from apps.core.services.tally_reports import get_tally_inventory_usage_by_month

    return get_tally_inventory_usage_by_month(params)


def _get_tally_inventory_yearly_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return yearly inventory usage summary and valuation metrics."""
    from apps.core.services.tally_reports import get_tally_inventory_yearly_summary

    return get_tally_inventory_yearly_summary(params)


def _get_tally_report_registry(params: Dict[str, Any]) -> Dict[str, Any]:
    """List registered tally report keys and metadata."""
    from apps.core.services.tally_registry import list_tally_reports

    return list_tally_reports()


def _execute_tally_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tally report by key via registry."""
    from apps.core.services.tally_registry import execute_tally_report

    return execute_tally_report(params)


def _export_tally_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Export tally report output as csv/json string content."""
    from apps.core.services.tally_registry import export_tally_report

    return export_tally_report(params)


def _post_gl_entries(params: dict) -> dict:
    """Post staged GL journal entries for an invoice or payment.

    User-initiated action — records stay editable until this is called.
    After posting, the record should be locked (is_locked=True) to prevent
    edits. Corrections require reversing transactions.

    Params:
        model_name: 'invoice' or 'payment'
        id: record primary key
    """
    from django.apps import apps as dj_apps
    from apps.accounts.services.ledger_balance import post_staged_gl_entries

    model_name = params.get('model_name', '').lower()
    record_id = params.get('id')
    if not model_name or not record_id:
        raise ValueError("model_name and id are required")
    if model_name not in ('invoice', 'payment'):
        raise ValueError("model_name must be 'invoice' or 'payment'")

    # Resolve model
    app_label = 'transactions'
    Model = dj_apps.get_model(app_label, model_name.capitalize())
    try:
        instance = Model.objects.get(pk=record_id)
    except Model.DoesNotExist:
        raise ValueError(f"{model_name} #{record_id} not found")

    # Check not already locked
    if getattr(instance, 'is_locked', False):
        raise ValueError(f"{model_name} #{record_id} is already journalized (locked)")

    # Post GL entries
    count = post_staged_gl_entries(instance)
    if count == 0:
        return {
            'posted': 0,
            'message': f"No GL entries to post (already posted or no staged data)",
        }

    # Lock the record — no further edits without reversal
    Model.objects.filter(pk=record_id).update(is_locked=True)

    return {
        'posted': count,
        'model_name': model_name,
        'id': record_id,
        'locked': True,
        'message': f"Posted {count} GL entries for {model_name} #{record_id}. Record is now locked.",
    }


def _reverse_gl_entries(params: dict) -> dict:
    """Reverse GL journal entries for a journalized invoice or payment.

    Creates contra entries (debit↔credit swapped). Original entries remain
    as permanent record. Record is unlocked after reversal so it can be
    edited and re-journalized.

    Params:
        model_name: 'invoice' or 'payment'
        id: record primary key
        reason: optional reason for reversal
    """
    from django.apps import apps as dj_apps
    from apps.accounts.services.ledger_balance import reverse_gl_entries

    model_name = params.get('model_name', '').lower()
    record_id = params.get('id')
    reason = params.get('reason', '')
    if not model_name or not record_id:
        raise ValueError("model_name and id are required")
    if model_name not in ('invoice', 'payment'):
        raise ValueError("model_name must be 'invoice' or 'payment'")

    app_label = 'transactions'
    Model = dj_apps.get_model(app_label, model_name.capitalize())
    try:
        instance = Model.objects.get(pk=record_id)
    except Model.DoesNotExist:
        raise ValueError(f"{model_name} #{record_id} not found")

    if not getattr(instance, 'is_locked', False):
        raise ValueError(f"{model_name} #{record_id} is not journalized (not locked)")

    count = reverse_gl_entries(instance, reason=reason)
    if count == 0:
        return {
            'reversed': 0,
            'message': f"No entries to reverse (already reversed or no GL entries)",
        }

    return {
        'reversed': count,
        'model_name': model_name,
        'id': record_id,
        'unlocked': True,
        'message': f"Reversed {count} GL entries for {model_name} #{record_id}. Record unlocked for editing.",
    }


def _run_training_flow(params: dict) -> dict:
    """Alice: run a training/health-check transaction cycle.

    Creates proposal → order → invoice → payment → PO → receipt
    for a specific customer and item. All records flagged with
    metadata.training=True so reporting excludes them.

    Params:
        customer_id: customer org to use
        item_id: item to transact
        proposal_qty: (default 5)
        order_qty: (default 4)
        invoice_qty: (default 3)
        po_qty: (default 10)
        receive_qty: (default 8)
    """
    from apps.transactions.services.training_flow import TrainingFlow

    customer_id = params.get('customer_id')
    item_id = params.get('item_id')
    if not customer_id or not item_id:
        raise ValueError("customer_id and item_id are required")

    flow = TrainingFlow(customer_id=int(customer_id), item_id=int(item_id))
    return flow.run_full_cycle(
        proposal_qty=int(params.get('proposal_qty', 5)),
        order_qty=int(params.get('order_qty', 4)),
        invoice_qty=int(params.get('invoice_qty', 3)),
        po_qty=int(params.get('po_qty', 10)),
        receive_qty=int(params.get('receive_qty', 8)),
    )


def _cleanup_training(params: dict) -> dict:
    """Alice: clean up all training-flagged records."""
    from apps.transactions.services.training_flow import cleanup_training_records
    return cleanup_training_records()


def _get_orphan_counts(params: dict) -> dict:
    """Admin dashboard: orphan record counts by table.

    Returns list of models with null or dangling FK counts.
    Only includes relationships with orphans > 0.
    """
    from apps.core.services.orphan_detection import get_orphan_counts
    results = get_orphan_counts()
    return {
        'orphans': results,
        'total_orphans': sum(r['total_orphans'] for r in results),
        'tables_with_orphans': len(results),
    }


def _get_orphan_detail(params: dict) -> dict:
    """Admin dashboard: list actual orphan records for a model.

    Params:
        app: Django app label (e.g. 'transactions')
        model: model name (e.g. 'OrderLine')
        fk_field: FK field name (e.g. 'order_id')
        type: 'null', 'dangling', or 'all' (default 'all')
        limit: max records (default 100)
        offset: pagination offset (default 0)
    """
    from apps.core.services.orphan_detection import get_orphan_detail

    app = params.get('app', '')
    model = params.get('model', '')
    fk_field = params.get('fk_field', '')
    if not app or not model or not fk_field:
        raise ValueError("app, model, and fk_field are required")

    return get_orphan_detail(
        child_app=app,
        child_model_name=model,
        fk_field=fk_field,
        orphan_type=params.get('type', 'all'),
        limit=int(params.get('limit', 100)),
        offset=int(params.get('offset', 0)),
    )


_ACTION_DISPATCH = {
    "post_gl_entries": _post_gl_entries,
    "reverse_gl_entries": _reverse_gl_entries,
    "run_training_flow": _run_training_flow,
    "cleanup_training": _cleanup_training,
    "get_orphan_counts": _get_orphan_counts,
    "get_orphan_detail": _get_orphan_detail,
    "get_accounting_dashboard": lambda params: __import__(
        'apps.accounts.services.accounting_dashboard',
        fromlist=['get_accounting_dashboard']
    ).get_accounting_dashboard(),
    "generate_kanban_projects": _generate_kanban_projects,
    "get_receivable_aging": _get_receivable_aging,
    "get_tally_summary_by_period": _get_tally_summary_by_period,
    "get_tally_sales_by_customer_month": _get_tally_sales_by_customer_month,
    "get_tally_sales_by_manufacturer_month": _get_tally_sales_by_manufacturer_month,
    "get_tally_sales_by_customer_year": _get_tally_sales_by_customer_year,
    "get_tally_inventory_usage_by_month": _get_tally_inventory_usage_by_month,
    "get_tally_inventory_yearly_summary": _get_tally_inventory_yearly_summary,
    "get_tally_report_registry": _get_tally_report_registry,
    "execute_tally_report": _execute_tally_report,
    "export_tally_report": _export_tally_report,
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

        if action_name.startswith("get_tally_"):
            _log_tally_observation(request, action_name, params, result)

        return api_response(
            data=result,
            message=f"action '{action_name}' completed",
        )
