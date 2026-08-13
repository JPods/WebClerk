"""
Cash Conversion Cycle Service
==============================

Measures how long money takes to flow through each stage of the revenue cycle.
Powers Tab 2 of the Accounting dashboard.

Four stages:
  1. Order → Invoice   : fulfillment lag  (order.dt_created → invoice.dt_created)
  2. Invoice → Payment : collection lag   (invoice.dt_created → payment.dt_created)
  3. Payment → GL      : posting lag      (payment.dt_created → GlJournal.dt_created)
  4. GL → Period Close : reconciliation   (period reconciled flag from journalize.py)

All dt_created values are epoch milliseconds (BigIntegerField).
"""
from __future__ import annotations

import calendar
import statistics
import time
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db.models import Avg, Count, F, Q, Sum


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MS_PER_DAY = 86_400_000          # milliseconds in one calendar day
STALL_THRESHOLD_DAYS = 30        # records older than this trigger an alert


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_ms() -> int:
    return int(time.time() * 1000)


def _ms_to_days(ms: int) -> float:
    """Convert milliseconds to fractional days."""
    return ms / MS_PER_DAY


def _period_ms(year: Optional[int], month: Optional[int]):
    """Return (start_ms, end_ms) for the given year/month, or (None, None)."""
    if not year or not month:
        return None, None
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return (
        int(calendar.timegm(start.timetuple()) * 1000),
        int(calendar.timegm(end.timetuple()) * 1000),
    )


def _stage_dict(
    name: str,
    label: str,
    avg_days: Optional[float],
    median_days: Optional[float],
    count_in_stage: int,
    count_completed: int,
    value_stalled: float,
    count_stalled_30: int,
    stalled_ids: List[int],
) -> Dict[str, Any]:
    return {
        'name': name,
        'label': label,
        'avg_days': round(avg_days, 2) if avg_days is not None else None,
        'median_days': round(median_days, 2) if median_days is not None else None,
        'count_in_stage': count_in_stage,
        'count_completed': count_completed,
        'value_stalled': round(value_stalled, 2),
        'count_stalled_30': count_stalled_30,
        'stalled_ids': stalled_ids[:50],          # cap list for UI safety
    }


# ---------------------------------------------------------------------------
# Stage 1: Order → Invoice (fulfillment lag)
# ---------------------------------------------------------------------------

def _stage_order_to_invoice(start_ms, end_ms) -> Dict[str, Any]:
    """Orders that have been fulfilled (have a child Invoice) vs. still open."""
    Order = dj_apps.get_model('transactions', 'Order')
    Invoice = dj_apps.get_model('transactions', 'Invoice')

    now_ms = _now_ms()

    # Period filter applies to order creation time
    order_qs = Order.objects.filter(is_active=True, is_deleted=False)
    if start_ms and end_ms:
        order_qs = order_qs.filter(dt_created__gte=start_ms, dt_created__lt=end_ms)

    # Invoices whose parent_model='order' — link to the originating order
    inv_qs = Invoice.objects.filter(
        parent_model='order',
        is_active=True,
        is_deleted=False,
    )
    if start_ms and end_ms:
        inv_qs = inv_qs.filter(dt_created__gte=start_ms, dt_created__lt=end_ms)

    # Build map: order_id → invoice.dt_created
    fulfilled_map: Dict[int, int] = {}
    for inv in inv_qs.values('parent_id', 'dt_created'):
        pid = inv['parent_id']
        if pid and pid not in fulfilled_map:
            fulfilled_map[pid] = inv['dt_created']

    # Walk orders; compute lag for fulfilled, flag stalled for open
    lag_days: List[float] = []
    stalled_ids: List[int] = []
    stalled_30_ids: List[int] = []
    value_stalled = Decimal('0')
    count_completed = 0

    for order in order_qs.values('id', 'dt_created', 'total', 'status'):
        oid = order['id']
        o_created = order['dt_created'] or 0
        if oid in fulfilled_map:
            lag = fulfilled_map[oid] - o_created
            if lag >= 0:
                lag_days.append(_ms_to_days(lag))
            count_completed += 1
        else:
            # Still in fulfillment — open orders only (not cancelled)
            status = (order['status'] or '').lower()
            if status not in ('canceled', 'complete'):
                stalled_ids.append(oid)
                age_ms = now_ms - o_created
                if age_ms > STALL_THRESHOLD_DAYS * MS_PER_DAY:
                    stalled_30_ids.append(oid)
                total = Decimal(str(order['total'] or 0))
                value_stalled += total

    avg_d = statistics.mean(lag_days) if lag_days else None
    med_d = statistics.median(lag_days) if lag_days else None

    return _stage_dict(
        name='order_to_invoice',
        label='Order → Invoice (Fulfillment Lag)',
        avg_days=avg_d,
        median_days=med_d,
        count_in_stage=len(stalled_ids),
        count_completed=count_completed,
        value_stalled=float(value_stalled),
        count_stalled_30=len(stalled_30_ids),
        stalled_ids=stalled_ids,
    )


# ---------------------------------------------------------------------------
# Stage 2: Invoice → Payment (collection lag)
# ---------------------------------------------------------------------------

def _stage_invoice_to_payment(start_ms, end_ms) -> Dict[str, Any]:
    """Invoices that have a payment vs. still outstanding."""
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Payment = dj_apps.get_model('transactions', 'Payment')

    now_ms = _now_ms()

    inv_qs = Invoice.objects.filter(is_active=True, is_deleted=False)
    if start_ms and end_ms:
        inv_qs = inv_qs.filter(dt_created__gte=start_ms, dt_created__lt=end_ms)

    # Build map: invoice_id → earliest payment.dt_created
    pay_map: Dict[int, int] = {}
    pay_qs = Payment.objects.filter(
        is_active=True,
        is_deleted=False,
        invoice_id__isnull=False,
        type='received',
    ).values('invoice_id', 'dt_created').order_by('invoice_id', 'dt_created')

    for pay in pay_qs:
        iid = pay['invoice_id']
        if iid not in pay_map:
            pay_map[iid] = pay['dt_created']

    lag_days: List[float] = []
    stalled_ids: List[int] = []
    stalled_30_ids: List[int] = []
    value_stalled = Decimal('0')
    count_completed = 0

    for inv in inv_qs.values('id', 'dt_created', 'total', 'balance', 'status'):
        iid = inv['id']
        i_created = inv['dt_created'] or 0
        balance = Decimal(str(inv['balance'] or 0))
        total = Decimal(str(inv['total'] or 0))

        if iid in pay_map:
            lag = pay_map[iid] - i_created
            if lag >= 0:
                lag_days.append(_ms_to_days(lag))
            count_completed += 1
        else:
            # No payment yet — if balance > 0, it's stalled
            status = (inv['status'] or '').lower()
            if status not in ('canceled',) and balance > 0:
                stalled_ids.append(iid)
                age_ms = now_ms - i_created
                if age_ms > STALL_THRESHOLD_DAYS * MS_PER_DAY:
                    stalled_30_ids.append(iid)
                value_stalled += balance

    avg_d = statistics.mean(lag_days) if lag_days else None
    med_d = statistics.median(lag_days) if lag_days else None

    return _stage_dict(
        name='invoice_to_payment',
        label='Invoice → Payment (Collection Lag)',
        avg_days=avg_d,
        median_days=med_d,
        count_in_stage=len(stalled_ids),
        count_completed=count_completed,
        value_stalled=float(value_stalled),
        count_stalled_30=len(stalled_30_ids),
        stalled_ids=stalled_ids,
    )


# ---------------------------------------------------------------------------
# Stage 3: Payment → GL (posting lag)
# ---------------------------------------------------------------------------

def _stage_payment_to_gl(start_ms, end_ms) -> Dict[str, Any]:
    """Payments that have a GL journal entry vs. awaiting posting."""
    Payment = dj_apps.get_model('transactions', 'Payment')
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    now_ms = _now_ms()

    pay_qs = Payment.objects.filter(
        is_active=True,
        is_deleted=False,
        type='received',
    ).exclude(amount=0)
    if start_ms and end_ms:
        pay_qs = pay_qs.filter(dt_created__gte=start_ms, dt_created__lt=end_ms)

    # Build map: payment_id → earliest GlJournal.dt_created for that payment
    gl_map: Dict[int, int] = {}
    gl_qs = (
        GlJournal.objects
        .filter(source_model='payment')
        .values('source_id', 'dt_created')
        .order_by('source_id', 'dt_created')
    )
    for gl in gl_qs:
        sid = gl['source_id']
        if sid not in gl_map:
            gl_map[sid] = gl['dt_created']

    lag_days: List[float] = []
    stalled_ids: List[int] = []
    stalled_30_ids: List[int] = []
    value_stalled = Decimal('0')
    count_completed = 0

    for pay in pay_qs.values('id', 'dt_created', 'amount', 'status'):
        pid = pay['id']
        p_created = pay['dt_created'] or 0
        amount = Decimal(str(pay['amount'] or 0))
        status = (pay['status'] or '').lower()

        if pid in gl_map:
            lag = gl_map[pid] - p_created
            if lag >= 0:
                lag_days.append(_ms_to_days(lag))
            count_completed += 1
        else:
            # No GL entry yet — skip holds (they are intentionally deferred)
            if not status.startswith('hold'):
                stalled_ids.append(pid)
                age_ms = now_ms - p_created
                if age_ms > STALL_THRESHOLD_DAYS * MS_PER_DAY:
                    stalled_30_ids.append(pid)
                value_stalled += abs(amount)

    avg_d = statistics.mean(lag_days) if lag_days else None
    med_d = statistics.median(lag_days) if lag_days else None

    return _stage_dict(
        name='payment_to_gl',
        label='Payment → GL (Posting Lag)',
        avg_days=avg_d,
        median_days=med_d,
        count_in_stage=len(stalled_ids),
        count_completed=count_completed,
        value_stalled=float(value_stalled),
        count_stalled_30=len(stalled_30_ids),
        stalled_ids=stalled_ids,
    )


# ---------------------------------------------------------------------------
# Stage 4: GL → Period Close (reconciliation)
# ---------------------------------------------------------------------------

def _stage_gl_to_period_close(year: Optional[int], month: Optional[int]) -> Dict[str, Any]:
    """Whether the period has been reconciled via mark_period_reconciled."""
    from apps.accounts.services.journalize import get_reconciliation_status

    if year and month:
        status = get_reconciliation_status(year, month)
        reconciled = status.get('reconciled', False)
        dt_reconciled = status.get('dt_reconciled')
        reconciled_by = status.get('reconciled_by', '')
        period_label = f'{year}-{month:02d}'
    else:
        reconciled = None   # no period filter — cannot assess
        dt_reconciled = None
        reconciled_by = ''
        period_label = 'all'

    return {
        'name': 'gl_to_period_close',
        'label': 'GL → Period Close (Reconciliation)',
        'period': period_label,
        'reconciled': reconciled,
        'dt_reconciled': dt_reconciled,
        'reconciled_by': reconciled_by,
        # Reconciliation is binary — no lag metric, no stall value
        'avg_days': None,
        'median_days': None,
        'count_in_stage': 0 if reconciled else 1,
        'count_completed': 1 if reconciled else 0,
        'value_stalled': 0.0,
        'count_stalled_30': 0,
        'stalled_ids': [],
    }


# ---------------------------------------------------------------------------
# Stalled-records detail list
# ---------------------------------------------------------------------------

def _build_stalled_records(stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten each stage's stalled_ids into a single alert list for the UI.

    Returns records that are stalled > 30 days, enriched with model name and
    count. Full detail (ida, customer, amount) is left to the view layer to
    fetch via wcapi to avoid N+1 here.
    """
    records = []
    for stage in stages:
        if stage['count_stalled_30'] > 0:
            records.append({
                'stage': stage['name'],
                'label': stage['label'],
                'count': stage['count_stalled_30'],
                'ids': stage['stalled_ids'][:20],       # first 20 for the alert list
                'value_stalled': stage['value_stalled'],
            })
    return records


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _build_summary(stages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate across the three timed stages (stage 4 is binary)."""
    timed = [s for s in stages if s['avg_days'] is not None]
    total_avg = sum(s['avg_days'] for s in timed) if timed else None
    total_value_stalled = sum(s['value_stalled'] for s in stages)
    total_stalled_count = sum(s['count_in_stage'] for s in stages)
    total_alert_count = sum(s['count_stalled_30'] for s in stages)

    return {
        'total_cycle_days_avg': round(total_avg, 2) if total_avg is not None else None,
        'total_value_stalled': round(total_value_stalled, 2),
        'total_stalled_count': total_stalled_count,
        'total_alert_count': total_alert_count,
        'stage_count': len(stages),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_cash_conversion(year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
    """Compute the cash conversion cycle metrics.

    Args:
        year:  Filter to this calendar year (optional).
        month: Filter to this calendar month (optional; requires year).

    Returns:
        {
            'stages': [
                {
                    'name': str,
                    'label': str,
                    'avg_days': float | None,
                    'median_days': float | None,
                    'count_in_stage': int,       # records currently stuck here
                    'count_completed': int,
                    'value_stalled': float,      # dollars sitting in this stage
                    'count_stalled_30': int,     # records stalled > 30 days
                    'stalled_ids': [int, ...],   # PKs for drill-down
                },
                ...                              # 4 stages total
            ],
            'stalled_records': [                 # cross-stage alert list
                {'stage': str, 'label': str, 'count': int, 'ids': [...], 'value_stalled': float},
                ...
            ],
            'summary': {
                'total_cycle_days_avg': float | None,
                'total_value_stalled': float,
                'total_stalled_count': int,
                'total_alert_count': int,
                'stage_count': int,
            },
            'period': str,          # 'YYYY-MM' or 'all'
            'dt_generated': int,    # epoch ms
        }
    """
    start_ms, end_ms = _period_ms(year, month)
    period_label = f'{year}-{month:02d}' if year and month else 'all'

    stages = [
        _stage_order_to_invoice(start_ms, end_ms),
        _stage_invoice_to_payment(start_ms, end_ms),
        _stage_payment_to_gl(start_ms, end_ms),
        _stage_gl_to_period_close(year, month),
    ]

    stalled_records = _build_stalled_records(stages)
    summary = _build_summary(stages)

    return {
        'stages': stages,
        'stalled_records': stalled_records,
        'summary': summary,
        'period': period_label,
        'dt_generated': _now_ms(),
    }
