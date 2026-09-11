"""
Financial Statements — Trial Balance, P&L, Balance Sheet
==========================================================

Projections of GL journal data grouped by GlAccount type/category.
These are operational finance reports for business owners — not
regulatory accounting. For compliance, export GL via gl_export.py
to accountants and external programs.

All three reports query GlJournal and group by GlAccount classification.
Period filtering uses dt_journaled (epoch ms) or batch_id (YYYY-MM).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from django.apps import apps as dj_apps
from django.db.models import Sum, Q, F


def _epoch_ms(d: date) -> int:
    """Convert date to UTC epoch milliseconds for dt_journaled comparison."""
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _period_filter(
    period_start: Optional[date],
    period_end: Optional[date],
    posted_only: bool = False,
) -> Q:
    """Build Q filter for GL entries within a date range.

    Args:
        posted_only: If True, only locked/journalized entries (dt_journaled > 0).
                     If False (default), all entries using dt_created for date range.
    """
    if posted_only:
        q = Q(dt_journaled__gt=0)
        if period_start:
            q &= Q(dt_journaled__gte=_epoch_ms(period_start))
        if period_end:
            q &= Q(dt_journaled__lte=_epoch_ms(period_end))
    else:
        q = Q()  # all entries
        if period_start:
            q &= Q(dt_created__gte=_epoch_ms(period_start))
        if period_end:
            q &= Q(dt_created__lte=_epoch_ms(period_end))
    return q


def _build_account_map() -> dict[str, dict]:
    """Build a map of account ida → {type, category, name} from GlAccount."""
    GlAccount = dj_apps.get_model('accounts', 'GlAccount')
    return {
        acct['ida']: {
            'name': acct['name'] or acct['ida'],
            'type': acct['type'] or '',
            'category': acct['category'] or 'other',
        }
        for acct in GlAccount.objects.values('ida', 'name', 'type', 'category')
        if acct['ida']
    }


# ═════════════════════════════════════════════════════════════════════════
# Trial Balance
# ═════════════════════════════════════════════════════════════════════════

def trial_balance(
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    division: str = '',
    posted_only: bool = False,
) -> dict:
    """All GL accounts with period debit/credit totals and running balance.

    Returns:
        {
            'period_start': '2026-01-01',
            'period_end': '2026-09-11',
            'accounts': [
                {
                    'account': '1000-Cash',
                    'name': 'Cash',
                    'type': 'asset',
                    'category': 'cash',
                    'debit': 125000.00,
                    'credit': 98000.00,
                    'balance': 27000.00,
                },
            ],
            'total_debit': ...,
            'total_credit': ...,
            'difference': ...,   # should be 0.00 if balanced
        }
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    account_map = _build_account_map()

    q = _period_filter(period_start, period_end, posted_only=posted_only)
    if division:
        q &= Q(division=division)

    # Aggregate by account
    rows = (
        GlJournal.objects.filter(q)
        .values('account')
        .annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )
        .order_by('account')
    )

    accounts = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for row in rows:
        acct_ida = row['account'] or ''
        dr = Decimal(str(row['total_debit'] or 0))
        cr = Decimal(str(row['total_credit'] or 0))
        info = account_map.get(acct_ida, {'name': acct_ida, 'type': '', 'category': 'other'})

        accounts.append({
            'account': acct_ida,
            'name': info['name'],
            'type': info['type'],
            'category': info['category'],
            'debit': float(dr),
            'credit': float(cr),
            'balance': float(dr - cr),
        })

        total_debit += dr
        total_credit += cr

    return {
        'period_start': period_start.isoformat() if period_start else None,
        'period_end': period_end.isoformat() if period_end else None,
        'division': division or None,
        'accounts': accounts,
        'total_debit': float(total_debit),
        'total_credit': float(total_credit),
        'difference': float(total_debit - total_credit),
    }


# ═════════════════════════════════════════════════════════════════════════
# P&L (Income Statement)
# ═════════════════════════════════════════════════════════════════════════

# Account types that appear on P&L
_PNL_TYPES = ('revenue', 'expense', 'contra')

# Display order for P&L sections
_PNL_SECTION_ORDER = {
    'revenue': 0,
    'cogs': 1,
    'expense': 2,
    'depreciation': 3,
    'payroll': 4,
    'other': 5,
}


def income_statement(
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    division: str = '',
    posted_only: bool = False,
) -> dict:
    """Revenue minus Expenses grouped by GlAccount category for a period.

    Returns:
        {
            'period_start': '2026-01-01',
            'period_end': '2026-09-30',
            'sections': [
                {
                    'type': 'revenue',
                    'label': 'Revenue',
                    'accounts': [...],
                    'subtotal': 250000.00,
                },
                {
                    'type': 'expense',
                    'label': 'Expenses',
                    'accounts': [...],
                    'subtotal': -180000.00,
                },
            ],
            'total_revenue': 250000.00,
            'total_expense': 180000.00,
            'net_income': 70000.00,
        }
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    account_map = _build_account_map()

    q = _period_filter(period_start, period_end, posted_only=posted_only)
    if division:
        q &= Q(division=division)

    rows = (
        GlJournal.objects.filter(q)
        .values('account')
        .annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )
        .order_by('account')
    )

    # Group accounts by category (only P&L types)
    categories: dict[str, list] = {}
    for row in rows:
        acct_ida = row['account'] or ''
        info = account_map.get(acct_ida, {'name': acct_ida, 'type': '', 'category': 'other'})

        if info['type'] not in _PNL_TYPES:
            continue

        dr = Decimal(str(row['total_debit'] or 0))
        cr = Decimal(str(row['total_credit'] or 0))

        # Revenue: natural credit balance (cr - dr)
        # Expense: natural debit balance (dr - cr)
        if info['type'] == 'revenue':
            amount = float(cr - dr)
        else:
            amount = float(dr - cr)

        cat = info['category']
        if cat not in categories:
            categories[cat] = []

        categories[cat].append({
            'account': acct_ida,
            'name': info['name'],
            'type': info['type'],
            'amount': amount,
        })

    # Build sections sorted by display order
    sections = []
    total_revenue = Decimal('0')
    total_expense = Decimal('0')

    for cat in sorted(categories.keys(), key=lambda c: _PNL_SECTION_ORDER.get(c, 99)):
        accts = categories[cat]
        subtotal = sum(a['amount'] for a in accts)
        accts.sort(key=lambda a: a['account'])

        # Classify as revenue or expense for totals
        is_revenue = all(a['type'] == 'revenue' for a in accts)
        if is_revenue:
            total_revenue += Decimal(str(subtotal))
            label = cat.replace('_', ' ').title()
        else:
            total_expense += Decimal(str(subtotal))
            label = cat.replace('_', ' ').title()

        sections.append({
            'category': cat,
            'label': label,
            'is_revenue': is_revenue,
            'accounts': accts,
            'subtotal': float(subtotal),
        })

    net_income = float(total_revenue - total_expense)

    return {
        'period_start': period_start.isoformat() if period_start else None,
        'period_end': period_end.isoformat() if period_end else None,
        'division': division or None,
        'sections': sections,
        'total_revenue': float(total_revenue),
        'total_expense': float(total_expense),
        'net_income': net_income,
    }


# ═════════════════════════════════════════════════════════════════════════
# Balance Sheet
# ═════════════════════════════════════════════════════════════════════════

# Account types that appear on Balance Sheet
_BS_TYPES = ('asset', 'liability', 'equity')

_BS_SECTION_ORDER = {
    'asset': 0,
    'liability': 1,
    'equity': 2,
}

_BS_CATEGORY_ORDER = {
    # Assets
    'cash': 0,
    'receivables': 1,
    'inventory': 2,
    'fixed_assets': 3,
    # Liabilities
    'payables': 10,
    # Equity
    'other': 20,
}


def balance_sheet(
    as_of_date: Optional[date] = None,
    division: str = '',
    posted_only: bool = False,
) -> dict:
    """Assets = Liabilities + Equity at a point in time.

    Includes capital assets from Purchase records with is_capital=True
    and accumulated depreciation from GL.

    Returns:
        {
            'as_of_date': '2026-09-11',
            'assets': {
                'sections': [...],
                'total': 450000.00,
            },
            'liabilities': {
                'sections': [...],
                'total': 280000.00,
            },
            'equity': {
                'sections': [...],
                'total': 170000.00,
                'retained_earnings': 70000.00,
            },
            'balanced': True,
        }
    """
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    account_map = _build_account_map()

    if as_of_date is None:
        as_of_date = date.today()

    # All journalized entries up to as_of_date
    # All entries up to as_of_date
    if posted_only:
        q = Q(dt_journaled__gt=0) & Q(dt_journaled__lte=_epoch_ms(as_of_date))
    else:
        q = Q(dt_created__lte=_epoch_ms(as_of_date))
    if division:
        q &= Q(division=division)

    rows = (
        GlJournal.objects.filter(q)
        .values('account')
        .annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )
        .order_by('account')
    )

    # Separate into BS types and compute retained earnings from P&L accounts
    type_groups: dict[str, dict[str, list]] = {
        'asset': {},
        'liability': {},
        'equity': {},
    }
    retained_earnings = Decimal('0')

    for row in rows:
        acct_ida = row['account'] or ''
        info = account_map.get(acct_ida, {'name': acct_ida, 'type': '', 'category': 'other'})
        dr = Decimal(str(row['total_debit'] or 0))
        cr = Decimal(str(row['total_credit'] or 0))

        acct_type = info['type']

        if acct_type in _BS_TYPES:
            # Assets: natural debit balance (dr - cr)
            # Liabilities/Equity: natural credit balance (cr - dr)
            if acct_type == 'asset':
                balance = float(dr - cr)
            else:
                balance = float(cr - dr)

            cat = info['category']
            if cat not in type_groups[acct_type]:
                type_groups[acct_type][cat] = []

            type_groups[acct_type][cat].append({
                'account': acct_ida,
                'name': info['name'],
                'category': cat,
                'balance': balance,
            })

        elif acct_type == 'revenue':
            retained_earnings += (cr - dr)
        elif acct_type in ('expense', 'contra'):
            retained_earnings -= (dr - cr)

    # Build output sections
    def _build_section(type_key: str) -> dict:
        cats = type_groups[type_key]
        sections = []
        total = Decimal('0')

        for cat in sorted(cats.keys(), key=lambda c: _BS_CATEGORY_ORDER.get(c, 99)):
            accts = cats[cat]
            accts.sort(key=lambda a: a['account'])
            subtotal = sum(a['balance'] for a in accts)
            total += Decimal(str(subtotal))

            sections.append({
                'category': cat,
                'label': cat.replace('_', ' ').title(),
                'accounts': accts,
                'subtotal': float(subtotal),
            })

        return {'sections': sections, 'total': float(total)}

    assets = _build_section('asset')
    liabilities = _build_section('liability')
    equity_section = _build_section('equity')

    # Add retained earnings to equity
    equity_total = Decimal(str(equity_section['total'])) + retained_earnings
    equity_section['retained_earnings'] = float(retained_earnings)
    equity_section['total'] = float(equity_total)

    assets_total = Decimal(str(assets['total']))
    liab_eq_total = Decimal(str(liabilities['total'])) + equity_total

    return {
        'as_of_date': as_of_date.isoformat(),
        'division': division or None,
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity_section,
        'balanced': abs(assets_total - liab_eq_total) < Decimal('0.01'),
    }
