"""
Cash Flow Forecast Engine
===========================

Combines operational data from WC3 transactions with budget entries
(Budget) to project cash inflows and outflows.

Formula:
    Cash Inflow  = proposals × probability
                 + orders × (delivery timing + terms payment delay)

    Cash Outflow = purchase orders × (delivery + our payment delay)
                 + budget entries (Budget per account per period)

Budget entries:
    Users build complexity in their spreadsheets. When they hand it to us,
    it's a simple debit/credit with a GL account and a period.

    Connection/Bundle handles the import with full audit trail.
    Budget stores the live data. Past periods lock via dt_journaled.

    Alice compares budget vs actual (GlJournal) per account per period.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.apps import apps as dj_apps
from django.db.models import Sum


def _get_term_days(transaction) -> int:
    """Get payment delay in days from transaction's terms FK."""
    try:
        if transaction.terms_fk_id:
            Term = dj_apps.get_model('accounts', 'Term')
            term = Term.objects.filter(pk=transaction.terms_fk_id).values('days_due').first()
            if term and term['days_due']:
                return int(term['days_due'])
    except Exception:
        pass
    return 30  # default net 30


def _epoch_ms(d: date) -> int:
    """Convert date to UTC epoch milliseconds."""
    from datetime import datetime, timezone
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _get_budget_for_range(start_ms: int, end_ms: int) -> dict[str, dict]:
    """Query Budget records whose period overlaps the given date range.

    Uses dt_period_start/dt_period_end for range overlap — works for any
    period granularity (weekly, monthly, quarterly).

    Returns {period: {account: {debit, credit, net, description}, ...}, ...}
    """
    Budget = dj_apps.get_model('accounts', 'Budget')

    # Overlap: entry.start < range.end AND entry.end > range.start
    entries = Budget.objects.filter(
        dt_period_start__lt=end_ms,
        dt_period_end__gt=start_ms,
        is_active=True,
        is_deleted=False,
    ).values('period', 'account', 'debit', 'credit', 'description')

    result: dict[str, dict] = {}
    for e in entries:
        period = e['period']
        if period not in result:
            result[period] = {}
        dr = Decimal(str(e['debit'] or 0))
        cr = Decimal(str(e['credit'] or 0))
        result[period][e['account']] = {
            'debit': float(dr),
            'credit': float(cr),
            'net': float(dr - cr),
            'description': e['description'] or '',
        }

    return result


def _budget_period_totals(period_accounts: dict) -> dict:
    """Sum a period's budget entries into debit/credit/net totals."""
    total_dr = Decimal('0')
    total_cr = Decimal('0')
    for acct_data in period_accounts.values():
        total_dr += Decimal(str(acct_data['debit']))
        total_cr += Decimal(str(acct_data['credit']))
    return {
        'debit': float(total_dr),
        'credit': float(total_cr),
        'net': float(total_dr - total_cr),
        'account_count': len(period_accounts),
    }


def cash_flow_forecast(
    months_ahead: int = 6,
    as_of_date: Optional[date] = None,
) -> dict:
    """Project cash inflows and outflows for the next N months.

    Returns:
        {
            'as_of_date': '2026-09-11',
            'months': [
                {
                    'period': '2026-10',
                    'inflows': {
                        'pipeline': 45000.00,
                        'committed': 82000.00,
                        'total': 127000.00,
                    },
                    'outflows': {
                        'purchases': 35000.00,
                        'budget': {
                            'debit': 32000.00,
                            'credit': 0.00,
                            'net': 32000.00,
                            'account_count': 8,
                        },
                        'total': 67000.00,
                    },
                    'budget_detail': {
                        '6100-SALARY': {'debit': 12500, 'credit': 0, 'net': 12500, 'description': 'Salaried staff'},
                        ...
                    },
                    'net': 60000.00,
                },
            ],
            'summary': {...},
        }
    """
    Proposal = dj_apps.get_model('transactions', 'Proposal')
    Order = dj_apps.get_model('transactions', 'Order')
    Purchase = dj_apps.get_model('transactions', 'Purchase')

    if as_of_date is None:
        as_of_date = date.today()

    # Build list of future periods (month boundaries for the forecast grid)
    import calendar
    future_periods = []
    for i in range(months_ahead):
        y = as_of_date.year + (as_of_date.month + i) // 12
        m = (as_of_date.month + i) % 12 + 1
        last_day = calendar.monthrange(y, m)[1]
        future_periods.append({
            'label': f"{y}-{m:02d}",
            'start': date(y, m, 1),
            'end': date(y, m, last_day),
        })

    # ── Load budget entries for the full forecast range at once ──
    range_start_ms = _epoch_ms(future_periods[0]['start'])
    range_end_ms = _epoch_ms(future_periods[-1]['end']) + 86400000  # inclusive
    budget_by_period = _get_budget_for_range(range_start_ms, range_end_ms)

    # ── Pipeline inflow: proposals × probability ──
    pipeline_proposals = Proposal.objects.filter(
        status__in=['planned', 'signoff_request', 'released', 'in_progress'],
        probability__gt=0,
    ).values('id', 'probability', 'totals', 'terms_fk_id')

    pipeline_by_month: dict[str, Decimal] = {}
    for prop in pipeline_proposals:
        total = Decimal(str((prop['totals'] or {}).get('total', 0)))
        prob = Decimal(str(prop['probability'] or 0))
        weighted = total * prob
        term_days = 30
        expected_date = as_of_date + timedelta(days=term_days)
        period = f"{expected_date.year}-{expected_date.month:02d}"
        pipeline_by_month[period] = pipeline_by_month.get(period, Decimal('0')) + weighted

    # ── Committed inflow: orders expected to collect ──
    open_orders = Order.objects.filter(
        status__in=['planned', 'released', 'in_progress'],
    ).select_related('terms_fk')

    committed_by_month: dict[str, Decimal] = {}
    for order in open_orders:
        total = Decimal(str((order.totals or {}).get('balance', 0) or (order.totals or {}).get('total', 0)))
        if total <= 0:
            continue
        term_days = _get_term_days(order)
        expected_date = as_of_date + timedelta(days=term_days)
        period = f"{expected_date.year}-{expected_date.month:02d}"
        committed_by_month[period] = committed_by_month.get(period, Decimal('0')) + total

    # ── Purchase outflow: POs expected to pay ──
    open_purchases = Purchase.objects.filter(
        status__in=['planned', 'released', 'in_progress'],
    ).select_related('terms_fk')

    purchases_by_month: dict[str, Decimal] = {}
    for po in open_purchases:
        total = Decimal(str((po.totals or {}).get('balance', 0) or (po.totals or {}).get('total', 0)))
        if total <= 0:
            continue
        term_days = _get_term_days(po)
        expected_date = as_of_date + timedelta(days=term_days)
        period = f"{expected_date.year}-{expected_date.month:02d}"
        purchases_by_month[period] = purchases_by_month.get(period, Decimal('0')) + total

    # ── Build month-by-month forecast ──
    months = []
    total_inflow = Decimal('0')
    total_outflow = Decimal('0')

    for fp in future_periods:
        period = fp['label']
        pipeline = pipeline_by_month.get(period, Decimal('0'))
        committed = committed_by_month.get(period, Decimal('0'))
        purchases = purchases_by_month.get(period, Decimal('0'))

        period_budget = budget_by_period.get(period, {})
        budget_totals = _budget_period_totals(period_budget)
        budget_net = Decimal(str(budget_totals['net']))

        inflow_total = pipeline + committed
        outflow_total = purchases + budget_net

        total_inflow += inflow_total
        total_outflow += outflow_total

        months.append({
            'period': period,
            'inflows': {
                'pipeline': float(pipeline),
                'committed': float(committed),
                'total': float(inflow_total),
            },
            'outflows': {
                'purchases': float(purchases),
                'budget': budget_totals,
                'total': float(outflow_total),
            },
            'budget_detail': period_budget,
            'net': float(inflow_total - outflow_total),
        })

    return {
        'as_of_date': as_of_date.isoformat(),
        'months_ahead': months_ahead,
        'months': months,
        'summary': {
            'total_inflow': float(total_inflow),
            'total_outflow': float(total_outflow),
            'net': float(total_inflow - total_outflow),
        },
    }


def budget_vs_actual(
    period: str,
    dt_start: Optional[int] = None,
    dt_end: Optional[int] = None,
    division: str = '',
) -> dict:
    """Compare budget (Budget) vs actual (GlJournal) for a period.

    This is Alice's retrospection signal — where did the forecast miss?

    Args:
        period: Period label to match (e.g., '2026-10', '2026-W41')
        dt_start: Optional epoch ms override — if provided, actuals are queried
                  by dt_journaled range instead of batch_id prefix. Useful for
                  non-monthly periods (weekly, quarterly).
        dt_end: Optional epoch ms end of range.
        division: Optional division filter.
    """
    Budget = dj_apps.get_model('accounts', 'Budget')
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    # Budget entries for this period
    budget_qs = Budget.objects.filter(
        period=period, is_active=True, is_deleted=False,
    )
    budget_entries = budget_qs.values('account', 'debit', 'credit', 'description')

    budget_map: dict[str, dict] = {}
    for e in budget_entries:
        budget_map[e['account']] = {
            'debit': Decimal(str(e['debit'] or 0)),
            'credit': Decimal(str(e['credit'] or 0)),
            'description': e['description'] or '',
        }

    # If no explicit range, try to get it from the Budget records
    if dt_start is None or dt_end is None:
        range_row = budget_qs.values('dt_period_start', 'dt_period_end').first()
        if range_row:
            dt_start = dt_start or range_row['dt_period_start']
            dt_end = dt_end or range_row['dt_period_end']

    # Actual GL entries — use epoch range if available, else batch_id prefix
    if dt_start and dt_end:
        gl_q = GlJournal.objects.filter(
            dt_journaled__gte=dt_start,
            dt_journaled__lte=dt_end,
        )
    else:
        gl_q = GlJournal.objects.filter(
            batch_id__startswith=period,
            dt_journaled__gt=0,
        )

    if division:
        gl_q = gl_q.filter(division=division)

    actual_rows = gl_q.values('account').annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
    )

    actual_map: dict[str, dict] = {}
    for row in actual_rows:
        actual_map[row['account'] or ''] = {
            'debit': Decimal(str(row['total_debit'] or 0)),
            'credit': Decimal(str(row['total_credit'] or 0)),
        }

    # Merge — all accounts that appear in either budget or actual
    all_accounts = sorted(set(budget_map.keys()) | set(actual_map.keys()))

    accounts = []
    totals = {
        'budget_debit': Decimal('0'), 'budget_credit': Decimal('0'),
        'actual_debit': Decimal('0'), 'actual_credit': Decimal('0'),
        'variance_debit': Decimal('0'), 'variance_credit': Decimal('0'),
    }

    for acct in all_accounts:
        b = budget_map.get(acct, {'debit': Decimal('0'), 'credit': Decimal('0'), 'description': ''})
        a = actual_map.get(acct, {'debit': Decimal('0'), 'credit': Decimal('0')})

        var_dr = a['debit'] - b['debit']
        var_cr = a['credit'] - b['credit']

        accounts.append({
            'account': acct,
            'budget_debit': float(b['debit']),
            'budget_credit': float(b['credit']),
            'actual_debit': float(a['debit']),
            'actual_credit': float(a['credit']),
            'variance_debit': float(var_dr),
            'variance_credit': float(var_cr),
            'description': b['description'],
        })

        totals['budget_debit'] += b['debit']
        totals['budget_credit'] += b['credit']
        totals['actual_debit'] += a['debit']
        totals['actual_credit'] += a['credit']
        totals['variance_debit'] += var_dr
        totals['variance_credit'] += var_cr

    return {
        'period': period,
        'dt_start': dt_start,
        'dt_end': dt_end,
        'division': division or None,
        'accounts': accounts,
        'totals': {k: float(v) for k, v in totals.items()},
    }
