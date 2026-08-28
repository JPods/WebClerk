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
  Pricing Engine:
    resolve_price              — resolve effective unit price for item (contract→level→base→floor)
    get_price_matrix           — return all price levels and qty breaks for UI grid
    apply_line_pricing         — resolve and update price on a transaction line
  Tax Calculation:
    calculate_line_tax         — compute tax for a single line extended price
    calculate_transaction_tax  — compute and update tax for all lines of a transaction
    get_tax_jurisdictions      — list active tax jurisdictions with rates
  Totals Recalculation:
    recalculate_totals         — recompute header totals from all lines
    recalculate_line           — recompute single line extended + update parent totals
  Document Conversion Chain:
    convert_proposal_to_order      — proposal lines to new order (partial supported)
    convert_order_to_invoice       — order lines to new invoice (partial supported)
    convert_order_to_purchase      — order lines to new PO (drop-ship / procurement)
    convert_proposal_to_invoice    — proposal direct to invoice (over-the-counter)
    get_conversion_history         — trace parent/child chain for a transaction
    bulk_convert                   — convert multiple source transactions at once
  Shipping / Packing Workflow:
    generate_pick_list             — pick list with bin locations for an order
    confirm_pack                   — record packed lines with tracking/carrier/weight
    ship_order                     — complete shipment via conversion chain (order -> invoice)
    get_shipment_status            — what has shipped vs pending for an order
  EOM (End of Month) Close:
    run_eom_close                  — aging, GL verify, summary, lock period
    get_eom_status                 — check if period is closed, what is pending
    reopen_period                  — unlock a closed period (requires reason + contact)
  Letter / Email Template (Mail Merge):
    merge_template                 — merge a Document template with a record
    preview_merge                  — preview merge without sending
    send_email                     — merge + send via Django email backend
    bulk_send                      — send to multiple records
    get_available_templates        — list available templates
  Report Parade (Alice onboarding):
    start_parade                   — build parade manifest with sample data URLs
    save_parade_feedback           — save Keep/Modify/Don't Need feedback on a report
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


# ── Allowlisted management commands for admin tools ──────────────────────
_ADMIN_TOOL_COMMANDS = {
    'audit_field_behaviors',
    'audit_select_lists',
    'seed_model_definitions',
    'seed_company_settings',
    'seed_select_lists',
    'seed_freshstart',
    'load_demo_data',
    'remove_demo_data',
    'pack_demo_bundle',
    'seed_demo',
    'seed_demo_transactions',
}


def _run_admin_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    """Run an allowlisted management command and capture its JSON output.

    Params:
        command: management command name (must be in allowlist)
        args: list of CLI arguments (e.g. ["--json", "--model", "order"])
    """
    import io
    import json
    from django.core.management import call_command

    command = params.get('command', '')
    args = params.get('args', [])

    if command not in _ADMIN_TOOL_COMMANDS:
        raise ValueError(f"Command '{command}' is not in the admin tool allowlist")

    # Capture stdout
    out = io.StringIO()
    call_command(command, *args, stdout=out)
    output = out.getvalue()

    # Try to parse as JSON; fall back to plain text
    try:
        result = json.loads(output)
    except (json.JSONDecodeError, ValueError):
        result = {'text': output}

    return {'command': command, 'args': args, 'result': result}


def _carrier_action(method_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a carrier API call via the Connection record.

    Params must include 'connection_id' (Connection PK with carrier config)
    plus method-specific fields. The Connection config.carrier_code selects
    the implementation (ups, fedex, usps, dhl).
    """
    from apps.sync.models.connection import Connection
    from apps.transactions.services.fulfillment.carriers.base import get_carrier, Address, Package
    from dataclasses import asdict

    conn_id = params.get('connection_id')
    if not conn_id:
        raise ValueError('connection_id required — the Connection record with carrier credentials')

    conn = Connection.objects.get(pk=conn_id, is_active=True)
    carrier = get_carrier(conn.config or {})

    if method_name == 'get_rates':
        rates = carrier.get_rates(
            origin=Address(**params.get('origin', {})),
            destination=Address(**params.get('destination', {})),
            packages=[Package(**p) for p in params.get('packages', [])],
        )
        return {'rates': [asdict(r) for r in rates]}

    elif method_name == 'create_shipment':
        shipment = carrier.create_shipment(
            origin=Address(**params.get('origin', {})),
            destination=Address(**params.get('destination', {})),
            packages=[Package(**p) for p in params.get('packages', [])],
            service_code=params.get('service_code', ''),
            reference=params.get('reference', ''),
        )
        result = asdict(shipment)
        # Don't send raw label bytes through JSON — base64 encode
        import base64
        if shipment.label_data:
            result['label_data'] = base64.b64encode(shipment.label_data).decode('ascii')
        return result

    elif method_name == 'track':
        tracking = carrier.track(params.get('tracking_number', ''))
        return asdict(tracking)

    elif method_name == 'validate_address':
        validation = carrier.validate_address(Address(**params.get('address', {})))
        result = {'valid': validation.valid, 'messages': validation.messages}
        if validation.corrected:
            result['corrected'] = asdict(validation.corrected)
        return result

    elif method_name == 'cancel_shipment':
        success = carrier.cancel_shipment(params.get('tracking_number', ''))
        return {'cancelled': success}

    raise ValueError(f'Unknown carrier method: {method_name}')


def _log_tally_observation(request, action_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Persist a lightweight alice_log observation for tally usage."""
    try:
        from apps.ai_assistant.services.notes import create_note

        rows = result.get("rows") if isinstance(result, dict) else []
        totals = result.get("totals") if isinstance(result, dict) else {}
        details = {
            "action": action_name,
            "start_date": params.get("start_date") or result.get("start_date"),
            "end_date": params.get("end_date") or result.get("end_date"),
            "row_count": len(rows) if isinstance(rows, list) else 0,
            "total_count": (totals or {}).get("count", 0) if isinstance(totals, dict) else 0,
            "total": (totals or {}).get("total", 0) if isinstance(totals, dict) else 0,
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
        .filter(source='AR', dt_applied__isnull=True)
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


def _get_training_activity(params: dict) -> dict:
    """Return transaction lines + pending records for a training item.

    Shows the user exactly what happened: every line record and every
    pending record for the given item ida, from today, in dt sequence.

    Params:
        item_ida: item ida to track (default 'zzitem')
    """
    from datetime import datetime, timezone as tz
    from apps.products.models import Item
    from apps.transactions.models import (
        ProposalLine, OrderLine, InvoiceLine, PurchaseLine,
    )
    from apps.core.models import Pending
    from apps.products.models.inventory_layer import InventoryLayer

    item_ida = params.get('item_ida', 'zz-fake-item')
    item = Item.objects.filter(ida=item_ida).first()
    if not item:
        return {'error': f'Item {item_ida} not found. Run: manage.py seed_training_data'}

    # Today's start (UTC)
    today_start = datetime.now(tz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_ms = int(today_start.timestamp() * 1000)

    # Collect transaction lines for this item
    rows = []
    line_models = [
        ('proposal', ProposalLine, 'proposal'),
        ('order', OrderLine, 'order'),
        ('invoice', InvoiceLine, 'invoice'),
        ('purchase', PurchaseLine, 'purchase'),
    ]
    for kind, Model, parent_field in line_models:
        qs = Model.objects.filter(
            item_fk=item,
            dt_created__gte=today_ms,
        ).select_related(parent_field).order_by('dt_created')
        for ln in qs:
            parent_obj = getattr(ln, parent_field, None)
            qty = ln.quantity or {}
            price = getattr(ln, 'price', None) or {}
            cost = ln.cost or {}
            rows.append({
                'dt': ln.dt_created,
                'type': kind,
                'record_type': 'line',
                'parent_ida': getattr(parent_obj, 'ida', '') if parent_obj else '',
                'parent_status': getattr(parent_obj, 'status', '') if parent_obj else '',
                'qty_staged': qty.get('staged') or qty.get('active', 0),
                'qty_remaining': qty.get('remaining', 0),
                'unit_price': price.get('unit', 0) if isinstance(price, dict) else 0,
                'unit_cost': cost.get('unit', 0),
                'extended': price.get('extended', 0) if isinstance(price, dict) else 0,
                'line_id': ln.pk,
                'line_status': getattr(ln, 'status', ''),
            })

    # Collect pending records for this item
    pending_qs = Pending.objects.filter(
        record_id=str(item.pk),
        dt_created__gte=today_ms,
    ).order_by('dt_created')
    for p in pending_qs:
        cfg = p.config or {}
        rows.append({
            'dt': p.dt_created,
            'type': 'pending',
            'record_type': 'pending',
            'parent_ida': p.purpose or p.name or '',
            'parent_status': 'processed' if p.is_processed() else 'pending',
            'detail': cfg.get('field', ''),
            'delta': cfg.get('delta', 0),
            'reason': cfg.get('reason', ''),
            'pending_id': p.pk,
        })

    # Sort everything by dt
    rows.sort(key=lambda r: r['dt'])

    # Item inventory summary
    inv = {'on_hand': 0, 'on_so': 0, 'on_po': 0, 'on_p': 0, 'available': 0}
    qty_field = getattr(item, 'quantity', None) or {}
    if isinstance(qty_field, dict):
        inv.update({k: qty_field.get(k, 0) for k in inv})

    # Also check inventory layers
    layers = InventoryLayer.objects.filter(item=item, is_active=True, is_deleted=False)
    if layers.exists():
        layer = layers.first()
        lq = layer.quantity if isinstance(layer.quantity, dict) else {}
        inv['on_hand'] = lq.get('on_hand', inv['on_hand'])
        inv['on_so'] = lq.get('on_so', inv['on_so'])
        inv['on_po'] = lq.get('on_po', inv['on_po'])

    return {
        'item': {'id': item.pk, 'ida': item.ida, 'description': item.description or ''},
        'inventory': inv,
        'activity': rows,
        'count': len(rows),
    }


def _get_orphan_counts(params: dict) -> dict:
    """Admin dashboard: orphan record counts by table.

    Returns list of models with null or dangling FK counts.
    Only includes relationships with orphans > 0.
    """
    from apps.core.services.record_orphans import get_orphan_counts
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
    from apps.core.services.record_orphans import get_orphan_detail

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


def _file_small_sting(params: dict) -> dict:
    """File a Small-Sting complaint. Alice logs it and reports to WCHQ.

    A Small-Sting is a customer-assessed fine for an unresolved problem.
    Creates an Action record (the complaint), logs to alice_log, and
    marks for WCHQ reporting so patterns of complaints improve the
    system for all installations.

    Params:
        complaint: text description of the problem
        severity: 1-5 (1=minor annoyance, 5=business-stopping)
        model_name: which model/area the complaint is about (optional)
        record_id: specific record ID if applicable (optional)
        contact_id: who is filing the complaint (optional, defaults to current user)
    """
    from django.utils import timezone
    from apps.core.models import Action, Setting, Pending

    complaint = params.get('complaint', '').strip()
    if not complaint:
        raise ValueError("complaint text is required")

    severity = int(params.get('severity', 3))
    model_name = params.get('model_name', '')
    record_id = params.get('record_id', '')
    contact_id = params.get('contact_id')

    ts = timezone.now()
    ts_str = ts.strftime('%Y%m%dT%H%M%S')

    # 1. Create Action record — the formal complaint
    action = Action.objects.create(
        ida=f'STING-{ts_str}',
        status='open',
        priority=min(severity, 5),
        task={'en': f'Small-Sting: {complaint[:100]}'},
        description={'en': complaint},
        metadata={
            'type': 'small_sting',
            'severity': severity,
            'model_name': model_name,
            'record_id': str(record_id) if record_id else '',
            'dt_filed': ts.isoformat(),
            'source': 'user_complaint',
        },
    )
    if contact_id:
        action.contact_id = int(contact_id)
        action.save(update_fields=['contact_id'])

    # 2. Log to alice_log via Pending (Alice's observation pipeline)
    Pending.objects.create(
        model_name='alice_log',
        record_id=str(action.pk),
        purpose='small_sting',
        name=f'STING: {complaint[:80]}',
        config={
            'event': 'small_sting',
            'severity': severity,
            'complaint': complaint,
            'model_name': model_name,
            'record_id': str(record_id) if record_id else '',
            'action_id': action.pk,
            'action_ida': action.ida,
            'dt_filed': ts.isoformat(),
            'wchq_report': True,  # flag for WCHQ sync
        },
    )

    return {
        'success': True,
        'action_id': action.pk,
        'action_ida': action.ida,
        'message': f'Small-Sting filed: {action.ida}. Alice is tracking this.',
    }


_ACTION_DISPATCH = {
    "post_gl_entries": _post_gl_entries,
    "reverse_gl_entries": _reverse_gl_entries,
    "run_training_flow": _run_training_flow,
    "cleanup_training": _cleanup_training,
    "get_training_activity": _get_training_activity,
    "file_small_sting": _file_small_sting,
    "get_orphan_counts": _get_orphan_counts,
    "get_orphan_detail": _get_orphan_detail,
    "get_accounting_dashboard": lambda params: __import__(
        'apps.accounts.services.accounting_dashboard',
        fromlist=['get_accounting_dashboard']
    ).get_accounting_dashboard(),
    "get_journal_exceptions": lambda params: __import__(
        'apps.accounts.services.accounting_dashboard',
        fromlist=['get_journal_exceptions']
    ).get_journal_exceptions(
        year=int(params['year']) if params.get('year') else None,
        month=int(params['month']) if params.get('month') else None,
    ),
    "force_to_balance": lambda params: __import__(
        'apps.accounts.services.journalize',
        fromlist=['force_to_balance']
    ).force_to_balance(
        source_id=int(params['source_id']),
        source_model=params['source_model'],
        user_statement=params['user_statement'],
        forced_by=int(params['forced_by']) if params.get('forced_by') else None,
        adjustment_account=params.get('adjustment_account', ''),
    ),
    "get_sales_pipeline": lambda params: __import__(
        'apps.transactions.services.pipeline_report',
        fromlist=['get_sales_pipeline']
    ).get_sales_pipeline(
        year=int(params['year']) if params.get('year') else None,
        month=int(params['month']) if params.get('month') else None,
        months=int(params.get('months', 1)),
        customer_id=int(params['customer_id']) if params.get('customer_id') else None,
    ),
    "get_cash_conversion": lambda params: __import__(
        'apps.accounts.services.cash_conversion',
        fromlist=['get_cash_conversion']
    ).get_cash_conversion(
        year=int(params['year']) if params.get('year') else None,
        month=int(params['month']) if params.get('month') else None,
    ),
    "get_inventory_velocity": lambda params: __import__(
        'apps.products.services.inventory.inventory_velocity',
        fromlist=['get_inventory_velocity']
    ).get_inventory_velocity(
        year=int(params['year']) if params.get('year') else None,
        month=int(params['month']) if params.get('month') else None,
        category=params.get('category'),
    ),
    "get_item_by_ida": lambda params: __import__(
        'apps.products.services.inventory.inventory_flight_sim',
        fromlist=['get_item_by_ida']
    ).get_item_by_ida(
        ida=params['ida'],
    ),
    "reset_flight_simulator": lambda params: __import__(
        'apps.products.services.inventory.inventory_flight_sim',
        fromlist=['reset_flight_simulator']
    ).reset_flight_simulator(
        item_ida=params['ida'],
    ),
    "get_item_flight_state": lambda params: __import__(
        'apps.products.services.inventory.inventory_flight_sim',
        fromlist=['get_item_flight_state']
    ).get_item_flight_state(
        item_id=int(params['item_id']),
    ),
    "get_flight_scenario": lambda params: __import__(
        'apps.products.services.inventory.inventory_flight_sim',
        fromlist=['get_flight_scenario']
    ).get_flight_scenario(),
    "get_payment_flight_scenario": lambda params: __import__(
        'apps.products.services.inventory.inventory_flight_sim',
        fromlist=['get_payment_flight_scenario']
    ).get_payment_flight_scenario(),
    "get_first_customer_scenario": lambda params: __import__(
        'apps.products.services.onboarding_flight_sim',
        fromlist=['get_first_customer_scenario']
    ).get_first_customer_scenario(),
    "get_first_item_scenario": lambda params: __import__(
        'apps.products.services.onboarding_flight_sim',
        fromlist=['get_first_item_scenario']
    ).get_first_item_scenario(),
    "get_first_sale_scenario": lambda params: __import__(
        'apps.products.services.onboarding_flight_sim',
        fromlist=['get_first_sale_scenario']
    ).get_first_sale_scenario(),
    "get_flight_transactions": lambda params: __import__(
        'apps.products.services.inventory.inventory_flight_sim',
        fromlist=['get_flight_transactions']
    ).get_flight_transactions(
        item_id=int(params['item_id']),
    ),
    "get_flight_by_invoice": lambda params: __import__(
        'apps.products.services.inventory.inventory_flight_sim',
        fromlist=['get_flight_by_invoice']
    ).get_flight_by_invoice(
        invoice_ida=str(params['invoice_ida']),
    ),
    "get_collections_dashboard": lambda params: __import__(
        'apps.accounts.services.collections_dashboard',
        fromlist=['get_collections_dashboard']
    ).get_collections_dashboard(),
    "get_customer_health": lambda params: __import__(
        'apps.accounts.services.collections_dashboard',
        fromlist=['get_customer_health']
    ).get_customer_health(params.get('customer_id')),
    "export_vcard": lambda params: __import__(
        'apps.core.services.contact_vcard',
        fromlist=['export_vcard']
    ).export_vcard(params),
    "export_vcards": lambda params: __import__(
        'apps.core.services.contact_vcard',
        fromlist=['export_vcards']
    ).export_vcards(params),
    "preview_vcard": lambda params: __import__(
        'apps.core.services.contact_vcard',
        fromlist=['preview_vcard']
    ).preview_vcard(params),
    "import_vcard": lambda params: __import__(
        'apps.core.services.contact_vcard',
        fromlist=['import_vcard']
    ).import_vcard(params),
    "check_collisions": lambda params: __import__(
        'apps.core.services.contact_vcard',
        fromlist=['check_collisions']
    ).check_collisions(params),
    "import_bundle": lambda params: __import__(
        'apps.core.services.contact_vcard',
        fromlist=['import_bundle']
    ).import_bundle(params),
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
    # ── Order Production (GAP-01) ──
    "spawn_workorder": lambda p: __import__('apps.transactions.services.production_fulfill', fromlist=['spawn_workorder']).spawn_workorder(p['order_id']),
    "record_production_action": lambda p: __import__('apps.transactions.services.production_fulfill', fromlist=['record_production_action']).record_production_action(p['order_id'], p['action_text'], p.get('assigned_to')),
    "partial_ship": lambda p: __import__('apps.transactions.services.production_fulfill', fromlist=['partial_ship']).partial_ship(p['order_id'], p['shipped_lines']),
    "complete_order": lambda p: __import__('apps.transactions.services.production_fulfill', fromlist=['complete_order']).complete_order(p['order_id']),
    # ── Backorder Management (GAP-04) ──
    "get_open_backorders": lambda p: __import__('apps.transactions.services.backorder', fromlist=['get_open_backorders']).get_open_backorders(p.get('item_id')),
    "fulfill_backorder": lambda p: __import__('apps.transactions.services.backorder', fromlist=['fulfill_backorder']).fulfill_backorder(p['action_id'], p['qty_fulfilled']),
    "get_backorder_summary": lambda p: __import__('apps.transactions.services.backorder', fromlist=['get_backorder_summary_by_item']).get_backorder_summary_by_item(),
    # ── Inventory Stacks FIFO/LIFO (GAP-02) ──
    "receive_inventory": lambda p: __import__('apps.products.services.inventory.inventory_stacks', fromlist=['receive_inventory']).receive_inventory(p['item_id'], p['warehouse_id'], p['qty_received'], __import__('decimal').Decimal(str(p['unit_cost'])), p.get('source_type', 'purchase'), p.get('source_id'), p.get('lot', ''), p.get('serial_numbers')),
    "consume_inventory": lambda p: __import__('apps.products.services.inventory.inventory_stacks', fromlist=['consume_inventory']).consume_inventory(p['item_id'], p['qty_to_consume'], p.get('method', 'fifo'), p.get('warehouse_id'), p.get('source_type', 'invoice'), p.get('source_id')),
    "get_inventory_summary": lambda p: __import__('apps.products.services.inventory.inventory_stacks', fromlist=['get_item_inventory_summary']).get_item_inventory_summary(p['item_id'], p.get('warehouse_id')),
    # ── Serial Lifecycle (GAP-03) ──
    "create_serial_on_receive": lambda p: __import__('apps.products.services.serial.serial_lifecycle', fromlist=['create_serial_on_receive']).create_serial_on_receive(p['item_id'], p['serial_number'], p.get('vendor_id'), p.get('purchase_id'), p.get('purchase_line_id'), p.get('unit_cost', '0'), p.get('warehouse_id'), p.get('model_ida', '')),
    "assign_serial_on_ship": lambda p: __import__('apps.products.services.serial.serial_lifecycle', fromlist=['assign_serial_on_ship']).assign_serial_on_ship(p['serial_id'], p['customer_id'], p.get('invoice_id'), p.get('invoice_line_id'), p.get('warranty_months', 12)),
    "return_serial": lambda p: __import__('apps.products.services.serial.serial_lifecycle', fromlist=['return_serial']).return_serial(p['serial_id'], p.get('reason', ''), p.get('warehouse_id')),
    "get_serial_history": lambda p: __import__('apps.products.services.serial.serial_lifecycle', fromlist=['get_serial_history']).get_serial_history(p['serial_id']),
    "find_serials_by_customer": lambda p: __import__('apps.products.services.serial.serial_lifecycle', fromlist=['find_serials_by_customer']).find_serials_by_customer(p['customer_id']),
    # ── Campaign ROI (GAP-10) ──
    "create_campaign": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['create_campaign']).create_campaign(p['name'], __import__('decimal').Decimal(str(p.get('budget', 0))), p.get('channel', ''), p.get('start_date'), p.get('end_date'), p.get('description', '')),
    "record_campaign_spend": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['record_campaign_spend']).record_campaign_spend(p['campaign_id'], __import__('decimal').Decimal(str(p['amount']))),
    "calculate_campaign_roi": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['calculate_campaign_roi']).calculate_campaign_roi(p['campaign_id']),
    "get_all_campaigns": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['get_all_campaigns']).get_all_campaigns(),
    "link_transaction_to_campaign": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['link_transaction_to_campaign']).link_transaction_to_campaign(p['model_name'], p['record_id'], p['campaign_id']),
    # ── Layout Pending (DataBrowser) ──
    "save_layout_pending": lambda p: __import__('apps.ai_assistant.services.layout_pending', fromlist=['save_layout_pending']).save_layout_pending(p),
    # ── Journalize (GL Posting) ──
    "journalize_invoice": lambda p: __import__('apps.accounts.services.journalize', fromlist=['journalize_invoice']).journalize_invoice(p['invoice_id'], p.get('ida_prefix', '')),
    "journalize_invoice_and_payments": lambda p: __import__('apps.accounts.services.journalize', fromlist=['journalize_invoice_and_payments']).journalize_invoice_and_payments(p['invoice_id'], p.get('ida_prefix', '')),
    "journalize_payment": lambda p: __import__('apps.accounts.services.journalize', fromlist=['journalize_payment']).journalize_payment(p['payment_id'], p.get('ida_prefix', '')),
    "journalize_purchase": lambda p: __import__('apps.accounts.services.journalize', fromlist=['journalize_purchase']).journalize_purchase(p['purchase_id'], p.get('ida_prefix', '')),
    "batch_journalize": lambda p: __import__('apps.accounts.services.journalize', fromlist=['batch_journalize']).batch_journalize(p.get('ida_prefix', 'zzz-')),
    # ── Payment Pending (One Path) ──
    "apply_payment_to_invoice": lambda p: __import__('apps.transactions.services.payment_pending', fromlist=['apply_payment_to_invoice']).apply_payment_to_invoice(p['payment_id'], p['invoice_id'], p['amount'], p.get('reason', ''), p.get('contact_id'), discount_pct=p.get('discount_pct', 0), discount_amt=p.get('discount_amt', 0), dismiss_balance=p.get('dismiss_balance', False), fx_difference=p.get('fx_difference', 0)),
    "apply_pending_payments": lambda p: __import__('apps.transactions.services.payment_pending', fromlist=['apply_pending_for_invoice']).apply_pending_for_invoice(p['invoice_id']),
    # ── Commission ──
    "populate_commission": lambda p: __import__('apps.transactions.services.pricing.commission_compute', fromlist=['populate_transaction_commission']).populate_transaction_commission(p['transaction_id'], p['model_name']),
    "accrue_commission": lambda p: __import__('apps.transactions.services.pricing.commission_compute', fromlist=['accrue_commission']).accrue_commission(p['transaction_id'], p['model_name'], p.get('ida_prefix', '')),
    "get_commission_report": lambda p: __import__('apps.transactions.services.pricing.commission_compute', fromlist=['get_commission_report']).get_commission_report(p['period_start'], p['period_end'], p.get('rep_id'), p.get('model_name', 'invoice')),
    # ── Vendor Scorecard ──
    "compute_vendor_scorecard": lambda p: __import__('apps.orgs.services.vendor_scorecard', fromlist=['compute_vendor_scorecard']).compute_vendor_scorecard(p['vendor_id'], p.get('period_days', 90)),
    "update_vendor_scorecard": lambda p: __import__('apps.orgs.services.vendor_scorecard', fromlist=['update_vendor_scorecard']).update_vendor_scorecard(p['vendor_id']),
    "get_all_vendor_scores": lambda p: __import__('apps.orgs.services.vendor_scorecard', fromlist=['get_all_vendor_scores']).get_all_vendor_scores(),
    # ── Suggest Purchase ──
    "get_items_below_reorder": lambda p: __import__('apps.products.services.suggest_purchase', fromlist=['get_items_below_reorder']).get_items_below_reorder(p.get('warehouse_id')),
    "suggest_purchase_orders": lambda p: __import__('apps.products.services.suggest_purchase', fromlist=['suggest_purchase_orders']).suggest_purchase_orders(p.get('warehouse_id')),
    "create_draft_purchase": lambda p: __import__('apps.products.services.suggest_purchase', fromlist=['create_draft_purchase']).create_draft_purchase(p['vendor_id'], p['items']),
    # ── Credit Check ──
    "check_credit_limit": lambda p: __import__('apps.transactions.services.validate_credit', fromlist=['check_credit_limit']).check_credit_limit(p['customer_id'], p.get('new_amount', 0)),
    "acknowledge_credit_override": lambda p: __import__('apps.transactions.services.validate_credit', fromlist=['acknowledge_credit_override']).acknowledge_credit_override(p['transaction_id'], p['model_name'], p['contact_id'], p.get('reason', '')),
    # ── Campaign Enhancement (ORG-06) ──
    "attribute_customer_campaign": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['attribute_customer_to_campaign']).attribute_customer_to_campaign(p['customer_id'], p['campaign_id']),
    "get_campaign_cac": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['get_campaign_cac']).get_campaign_cac(p['campaign_id']),
    "get_campaign_margin_velocity": lambda p: __import__('apps.transactions.services.campaign_report', fromlist=['get_campaign_margin_velocity']).get_campaign_margin_velocity(p['campaign_id']),
    # ── Manufacturer Rebate (ORG-07) ──
    "accrue_manufacturer_rebate": lambda p: __import__('apps.orgs.services.rebate_accrual', fromlist=['accrue_manufacturer_rebate']).accrue_manufacturer_rebate(p['manufacturer_id'], p.get('period_start_ms'), p.get('period_end_ms')),
    "get_rebate_summary": lambda p: __import__('apps.orgs.services.rebate_accrual', fromlist=['get_rebate_summary']).get_rebate_summary(),
    # ── MAP Enforcement (ORG-08) ──
    "check_map_violation": lambda p: __import__('apps.products.services.map_enforcement', fromlist=['check_map_violation']).check_map_violation(p['item_id'], p['sell_price']),
    "check_order_map_violations": lambda p: __import__('apps.products.services.map_enforcement', fromlist=['check_order_map_violations']).check_order_map_violations(p['order_id']),
    "get_map_violations_report": lambda p: __import__('apps.products.services.map_enforcement', fromlist=['get_map_violations_report']).get_map_violations_report(p.get('period_days', 30)),
    # ── Pricing Engine ──
    "resolve_price": lambda p: __import__('apps.products.services.price_resolver', fromlist=['resolve_price_legacy']).resolve_price_legacy(p['item_id'], p.get('customer_id'), p.get('qty', 1), p.get('price_level')),
    "get_price_matrix": lambda p: __import__('apps.products.services.price_resolver', fromlist=['get_price_matrix']).get_price_matrix(p['item_id']),
    "apply_line_pricing": lambda p: __import__('apps.products.services.price_resolver', fromlist=['apply_line_pricing']).apply_line_pricing(p['model_name'], p['line_id'], p.get('customer_id'), p.get('qty')),
    # ── Tax Calculation ──
    "calculate_line_tax": lambda p: __import__('apps.accounts.services.tax_calculation', fromlist=['calculate_line_tax']).calculate_line_tax(p['line_price_extended'], p.get('tax_jurisdiction_id'), p.get('tax_rate')),
    # calculate_transaction_tax removed — use recalculate_totals (single engine)
    "get_tax_jurisdictions": lambda p: __import__('apps.accounts.services.tax_calculation', fromlist=['get_tax_jurisdictions']).get_tax_jurisdictions(),
    # ── Totals Recalculation ──
    "recalculate_totals": lambda p: __import__('apps.transactions.services.pricing.totals_compute', fromlist=['recalculate_totals']).recalculate_totals(p['transaction_id'], p['model_name']),
    "recalculate_line": lambda p: __import__('apps.transactions.services.pricing.totals_compute', fromlist=['recalculate_line']).recalculate_line(p['line_id'], p['model_name']),
    # ── Agent Message Bus ──
    "send_agent_message": lambda p: __import__('apps.core.services.agent_bus', fromlist=['send_to_bus']).send_to_bus(p.get('from', 'alice'), p['to'], p['subject'], p.get('body', ''), p.get('priority', 0), p.get('category'), p.get('context')),
    "check_agent_inbox": lambda p: __import__('apps.core.services.agent_bus', fromlist=['check_inbox']).check_inbox(p.get('agent', 'alice'), p.get('unread_only', True)),
    # ── Report Generation ──
    "render_report": lambda p: __import__('apps.core.services.render_report', fromlist=['render_report_action']).render_report_action(p['report_name'], p['model_name'], p.get('record_id'), p.get('filters'), p.get('format', 'pdf')),
    "get_available_reports": lambda p: __import__('apps.core.services.render_report', fromlist=['get_available_reports']).get_available_reports(p.get('model_name')),
    # ── User Pattern Tracking (Alice coaching) ──
    "log_user_navigation": lambda p: __import__('apps.ai_assistant.services.user_patterns', fromlist=['log_user_navigation']).log_user_navigation(p['contact_id'], p['entries']),
    "analyze_user_patterns": lambda p: __import__('apps.ai_assistant.services.user_patterns', fromlist=['analyze_user_patterns']).analyze_user_patterns(p['contact_id']),
    "get_all_user_patterns": lambda p: __import__('apps.ai_assistant.services.user_patterns', fromlist=['get_all_user_patterns']).get_all_user_patterns(),
    "save_alice_observation": lambda p: __import__('apps.ai_assistant.services.user_patterns', fromlist=['save_alice_observation']).save_alice_observation(p['contact_id'], p['observation'], p.get('category', 'workflow')),
    "log_user_search": lambda p: __import__('apps.ai_assistant.services.user_patterns', fromlist=['log_user_search']).log_user_search(p['contact_id'], p['model'], p['search_term'], p.get('result_count', 0)),
    "analyze_search_patterns": lambda p: __import__('apps.ai_assistant.services.user_patterns', fromlist=['analyze_search_patterns']).analyze_search_patterns(),
    "promote_search_preset": lambda p: __import__('apps.ai_assistant.services.user_patterns', fromlist=['promote_search_preset']).promote_search_preset(p['model'], p['term'], p.get('label', '')),
    # ── Code Standards (Alice enforcement) ──
    "scan_code_standards": lambda p: __import__('apps.ai_assistant.services.watch_code', fromlist=['scan_directory']).scan_directory(p.get('directory'), p.get('file_type', '.tsx')),
    "scan_changed_files": lambda p: __import__('apps.ai_assistant.services.watch_code', fromlist=['scan_changed_files']).scan_changed_files(p['files']),
    "get_migration_report": lambda p: __import__('apps.ai_assistant.services.watch_code', fromlist=['get_migration_report']).get_migration_report(),
    # ── Document Conversion Chain ──
    "convert_proposal_to_order": lambda p: __import__('apps.transactions.services.conversion', fromlist=['convert_proposal_to_order']).convert_proposal_to_order(p['proposal_id'], p.get('line_ids'), p.get('contact_id')),
    "convert_order_to_invoice": lambda p: __import__('apps.transactions.services.conversion', fromlist=['convert_order_to_invoice']).convert_order_to_invoice(p['order_id'], p.get('line_ids'), p.get('contact_id')),
    "convert_order_to_purchase": lambda p: __import__('apps.transactions.services.conversion', fromlist=['convert_order_to_purchase']).convert_order_to_purchase(p['order_id'], p.get('line_ids'), p.get('vendor_id'), p.get('contact_id')),
    "convert_proposal_to_invoice": lambda p: __import__('apps.transactions.services.conversion', fromlist=['convert_proposal_to_invoice']).convert_proposal_to_invoice(p['proposal_id'], p.get('line_ids'), p.get('contact_id')),
    "get_conversion_history": lambda p: __import__('apps.transactions.services.conversion', fromlist=['get_conversion_history']).get_conversion_history(p['transaction_id'], p['model_name']),
    "bulk_convert": lambda p: __import__('apps.transactions.services.conversion', fromlist=['bulk_convert']).bulk_convert(p['source_model'], p['source_ids'], p['target_model'], p.get('contact_id'), p.get('vendor_id')),
    # ── Shipping / Packing Workflow ──
    "generate_pick_list": lambda p: __import__('apps.transactions.services.shipping', fromlist=['generate_pick_list']).generate_pick_list(p['order_id']),
    "confirm_pack": lambda p: __import__('apps.transactions.services.shipping', fromlist=['confirm_pack']).confirm_pack(p['order_id'], p['packed_lines']),
    "ship_order": lambda p: __import__('apps.transactions.services.shipping', fromlist=['ship_order']).ship_order(p['order_id'], p.get('shipping_data', {}), p.get('contact_id')),
    "get_shipment_status": lambda p: __import__('apps.transactions.services.shipping', fromlist=['get_shipment_status']).get_shipment_status(p['order_id']),
    # ── Carrier API (rates, labels, tracking) ──
    "get_shipping_rates": lambda p: _carrier_action('get_rates', p),
    "create_carrier_shipment": lambda p: _carrier_action('create_shipment', p),
    "track_shipment": lambda p: _carrier_action('track', p),
    "validate_ship_address": lambda p: _carrier_action('validate_address', p),
    "cancel_carrier_shipment": lambda p: _carrier_action('cancel_shipment', p),
    # ── EOM (End of Month) Close ──
    "run_eom_close": lambda p: __import__('apps.accounts.services.period_close', fromlist=['run_eom_close']).run_eom_close(p['period_year'], p['period_month'], p.get('contact_id')),
    "get_eom_status": lambda p: __import__('apps.accounts.services.period_close', fromlist=['get_eom_status']).get_eom_status(p['period_year'], p['period_month']),
    "reopen_period": lambda p: __import__('apps.accounts.services.period_close', fromlist=['reopen_period']).reopen_period(p['period_year'], p['period_month'], p['contact_id'], p['reason']),
    # ── Letter / Email Template (Mail Merge) ──
    "merge_template": lambda p: __import__('apps.communications.services.mail_merge', fromlist=['merge_template']).merge_template(p['template_id'], p['record_model'], p['record_id']),
    "preview_merge": lambda p: __import__('apps.communications.services.mail_merge', fromlist=['preview_merge']).preview_merge(p['template_id'], p['record_model'], p['record_id']),
    "send_email": lambda p: __import__('apps.communications.services.mail_merge', fromlist=['send_email']).send_email(p['template_id'], p['record_model'], p['record_id'], p.get('to_email'), p.get('contact_id')),
    "bulk_send": lambda p: __import__('apps.communications.services.mail_merge', fromlist=['bulk_send']).bulk_send(p['template_id'], p['record_model'], p['record_ids']),
    "get_available_templates": lambda p: __import__('apps.communications.services.mail_merge', fromlist=['get_available_templates']).get_available_templates(p.get('model_name')),
    # ── Clone / Duplicate ──
    "clone_record": lambda p: __import__('apps.core.services.clone', fromlist=['clone_record']).clone_record(p['model_name'], p['record_id'], p.get('include_children', True), p.get('contact_id')),
    # ── Inventory Pending (ONE PATH — Pending.try_apply on save) ──
    "adjust_item_quantity": lambda p: __import__('apps.products.services.inventory.inventory_layers', fromlist=['adjust_item_quantity_via_pending']).adjust_item_quantity_via_pending(p),
    "get_pending_for_item": lambda p: list(
        __import__('apps.core.models', fromlist=['Pending']).Pending.objects.filter(
            model_name='item', record_id=str(p['item_id']),
        ).order_by('-dt_created').values('id', 'purpose', 'changes', 'dt_processed', 'dt_created')[:50]
    ),
    # ── Field Change Requests ──
    "request_field_change": lambda p: __import__('apps.ai_assistant.services.field_change_requests', fromlist=['request_field_change']).request_field_change(p.get('model',''), p.get('field',''), p.get('change_type','select'), p.get('values_source','static'), p.get('options'), p.get('query_model',''), p.get('query_field',''), p.get('query_filter',''), p.get('setting_name',''), p.get('reason',''), p.get('field_label',''), p.get('contact_id')),
    "approve_field_change": lambda p: __import__('apps.ai_assistant.services.field_change_requests', fromlist=['approve_field_change']).approve_field_change(p['action_id'], p['contact_id']),
    # ── UI Configuration (config.ui on Contact) ──
    "save_ui_config": lambda p: __import__('apps.core.services.ui_config', fromlist=['save_ui_config']).save_ui_config(p.get('config_ui', {}), p.get('contact_id')),
    "get_ui_config": lambda p: __import__('apps.core.services.ui_config', fromlist=['get_ui_config']).get_ui_config(p.get('contact_id')),
    "save_wcui_prefs": lambda p: __import__('apps.core.services.ui_config', fromlist=['save_ui_config']).save_ui_config(p.get('prefs', {}), p.get('contact_id')),  # legacy alias
    # ── Dedup (any model) ──
    "find_duplicates": lambda p: __import__('apps.core.services.dedup', fromlist=['find_duplicates']).find_duplicates(p['model'], p.get('match_fields', ['name_first+name_last']), p.get('limit', 500)),
    "merge_records": lambda p: __import__('apps.core.services.dedup', fromlist=['merge_records']).merge_records(p['model'], p['winner_id'], p['loser_ids'], p.get('merge_strategy', 'fill_empty')),
    "journal_dedup_delete": lambda p: __import__('apps.core.services.dedup', fromlist=['journal_delete']).journal_delete(p['model'], p['record_ids']),
    # ── Feature Lifecycle (Alice + Allie + Andi) ──
    "lifecycle_record": lambda p: __import__('apps.core.services.action_lifecycle', fromlist=['lifecycle_record']).lifecycle_record(p),
    # ── Dashboard Batch Counts ──
    "get_dashboard_counts": lambda p: __import__('apps.core.services.dashboard.dashboard_counts', fromlist=['get_dashboard_counts']).get_dashboard_counts(p),
    # ── Report Parade (Alice onboarding) ──
    "start_parade": lambda p: __import__('apps.core.services.report_parade', fromlist=['build_parade_manifest']).build_parade_manifest(p.get('report_ids'), p.get('base_url', 'http://localhost:8000')),
    "save_parade_feedback": lambda p: __import__('apps.core.services.report_parade', fromlist=['save_parade_feedback']).save_parade_feedback(p['report_id'], p['feedback'], p.get('notes', ''), p.get('user_id')),
    # ── CodeMap Architecture API ──
    "get_architecture_node": lambda p: __import__('apps.core.services.codemap', fromlist=['get_architecture_node']).get_architecture_node(p),
    "get_architecture_map": lambda p: __import__('apps.core.services.codemap', fromlist=['get_architecture_map']).get_architecture_map(p),
    "get_architecture_svg": lambda p: __import__('apps.core.services.codemap', fromlist=['get_architecture_svg']).get_architecture_svg(p),
    "list_architecture_flowcharts": lambda p: __import__('apps.core.services.codemap', fromlist=['list_architecture_flowcharts']).list_architecture_flowcharts(p),
    # ── Address formatting/validation ──
    "format_address": lambda p: __import__('apps.core.services.format_address', fromlist=['format_address_full']).format_address_full(**p),
    "validate_address": lambda p: __import__('apps.core.services.format_address', fromlist=['validate_and_format']).validate_and_format(type('Addr', (), p)()),
    # ── Contact Health ──
    "get_contact_health": lambda p: __import__('apps.core.services.contact_health', fromlist=['get_contact_health']).get_contact_health(p),
    # ── Action Horizon ──
    "get_action_horizon": lambda p: __import__('apps.core.services.action_horizon', fromlist=['get_action_horizon']).get_action_horizon(p),
    # ── Dashboard card summaries ──
    "get_action_summary": lambda p: __import__('apps.core.services.action_report', fromlist=['get_action_summary']).get_action_summary(p),
    "get_item_summary": lambda p: __import__('apps.core.services.dashboard.dashboard_item', fromlist=['get_item_summary']).get_item_summary(p),
    "get_customer_summary": lambda p: __import__('apps.core.services.dashboard.dashboard_customer', fromlist=['get_customer_summary']).get_customer_summary(p),
    "get_vendor_summary": lambda p: __import__('apps.core.services.dashboard.dashboard_vendor', fromlist=['get_vendor_summary']).get_vendor_summary(p),
    "get_rep_summary": lambda p: __import__('apps.core.services.dashboard.dashboard_rep', fromlist=['get_rep_summary']).get_rep_summary(p),
    "get_pending_summary": lambda p: __import__('apps.core.services.dashboard.dashboard_pending', fromlist=['get_pending_summary']).get_pending_summary(p),
    "get_dbsr_health": lambda p: __import__('apps.core.services.dashboard.dashboard_dbsr', fromlist=['get_dbsr_health']).get_dbsr_health(p),
    # ── Commerce Dashboard ──
    "get_sales_dashboard": lambda p: __import__('apps.core.services.dashboard.dashboard_commerce', fromlist=['get_sales_dashboard']).get_sales_dashboard(p),
    "get_purchasing_dashboard": lambda p: __import__('apps.core.services.dashboard.dashboard_commerce', fromlist=['get_purchasing_dashboard']).get_purchasing_dashboard(p),
    "get_inventory_summary": lambda p: __import__('apps.core.services.dashboard.dashboard_commerce', fromlist=['get_inventory_summary']).get_inventory_summary(p),
    "get_velocity_report": lambda p: __import__('apps.core.services.dashboard.dashboard_commerce', fromlist=['get_velocity_report']).get_velocity_report(p),
    "get_accounting_dashboard": lambda p: __import__('apps.core.services.dashboard.dashboard_commerce', fromlist=['get_accounting_dashboard']).get_accounting_dashboard(p),
    # ── Admin Tools (management commands via Report records) ──
    "run_admin_tool": _run_admin_tool,
    # ── Support Q&A (search → ask → answer → score → escalate) ──
    "search_support_qa": lambda p: __import__('apps.ai_assistant.services.support_qa', fromlist=['search_qa']).search_qa(p),
    "ask_support_qa": lambda p: __import__('apps.ai_assistant.services.support_qa', fromlist=['ask_qa']).ask_qa(p),
    "answer_support_qa": lambda p: __import__('apps.ai_assistant.services.support_qa', fromlist=['answer_qa']).answer_qa(p),
    "score_support_qa": lambda p: __import__('apps.ai_assistant.services.support_qa', fromlist=['score_qa']).score_qa(p),
    "escalate_support_qa": lambda p: __import__('apps.ai_assistant.services.support_qa', fromlist=['escalate_qa']).escalate_qa(p),
    "post_qa_to_wchq": lambda p: __import__('apps.ai_assistant.services.support_qa', fromlist=['post_qa_to_wchq']).post_qa_to_wchq(p),
}

# Actions that require staff/superuser — commission data is internal-only
_STAFF_ONLY_ACTIONS = {
    "populate_commission",
    "accrue_commission",
    "get_commission_report",
    "run_admin_tool",
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

        # Staff-only gate — commission and other internal actions
        if action_name in _STAFF_ONLY_ACTIONS:
            user = getattr(request, 'user', None)
            if not user or not (user.is_staff or user.is_superuser):
                return api_response(
                    success=False,
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="staff access required",
                    error={"code": "staff_required", "details": {"action": action_name}},
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
        except Exception as exc:
            logger.exception("manage action %s failed", action_name)
            return api_response(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"action '{action_name}' failed: {exc}",
                error={"code": "action_failed", "details": {"action": action_name}},
            )

        if action_name.startswith("get_tally_"):
            _log_tally_observation(request, action_name, params, result)

        return api_response(
            data=result,
            message=f"action '{action_name}' completed",
        )
