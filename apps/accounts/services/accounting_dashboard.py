"""Accounting dashboard data service.

Provides summary data for the admin accounting dashboard:
- Last journalized records by type
- Pending journal count (staged but not posted)
- GL imbalances (debits != credits)
- Orphan counts
- Aging summary
- Transaction volume by type
- Locked record counts
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List

from django.apps import apps as dj_apps
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_accounting_dashboard() -> Dict[str, Any]:
    """Return all accounting dashboard data in one call."""
    return {
        'journal_status': _get_journal_status(),
        'gl_balance': _get_gl_balance(),
        'transaction_volume': _get_transaction_volume(),
        'locked_records': _get_locked_records(),
        'aging_summary': _get_aging_summary(),
        'pending_inventory': _get_pending_inventory(),
        'dt_generated': int(timezone.now().timestamp() * 1000),
    }


def _get_journal_status() -> Dict[str, Any]:
    """Last journalized records and pending journal count by type."""
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Payment = dj_apps.get_model('transactions', 'Payment')

    # Last journalized by type
    last_invoice_gl = (
        GlJournal.objects.filter(source_model='invoice')
        .order_by('-dt_created').values('source_id', 'dt_created').first()
    )
    last_payment_gl = (
        GlJournal.objects.filter(source_model='payment')
        .order_by('-dt_created').values('source_id', 'dt_created').first()
    )

    # Count invoices with staged GL but not posted (metadata has gl_accounts but no GlJournal records)
    # Approximation: invoices not locked that have totals > 0
    pending_invoices = Invoice.objects.filter(
        is_locked=False, is_deleted=False, is_active=True,
    ).exclude(
        totals={},
    ).count()

    pending_payments = Payment.objects.filter(
        is_locked=False, is_deleted=False, is_active=True,
    ).exclude(
        amount=0,
    ).count()

    # Total journalized
    total_journal_entries = GlJournal.objects.count()

    return {
        'last_invoice_journalized': last_invoice_gl,
        'last_payment_journalized': last_payment_gl,
        'pending_invoices': pending_invoices,
        'pending_payments': pending_payments,
        'total_journal_entries': total_journal_entries,
    }


def _get_gl_balance() -> Dict[str, Any]:
    """Check GL balance — total debits should equal total credits."""
    GlJournal = dj_apps.get_model('accounts', 'GlJournal')

    totals = GlJournal.objects.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
    )
    total_debit = Decimal(str(totals['total_debit'] or 0))
    total_credit = Decimal(str(totals['total_credit'] or 0))
    imbalance = total_debit - total_credit

    # Per-source imbalances
    source_imbalances = []
    sources = GlJournal.objects.values('source_model').annotate(
        debits=Sum('debit'), credits=Sum('credit'),
    )
    for s in sources:
        d = Decimal(str(s['debits'] or 0))
        c = Decimal(str(s['credits'] or 0))
        if d != c:
            source_imbalances.append({
                'source_model': s['source_model'],
                'debits': float(d),
                'credits': float(c),
                'imbalance': float(d - c),
            })

    return {
        'total_debit': float(total_debit),
        'total_credit': float(total_credit),
        'imbalance': float(imbalance),
        'balanced': abs(imbalance) < Decimal('0.01'),
        'source_imbalances': source_imbalances,
    }


def _get_transaction_volume() -> Dict[str, Any]:
    """Transaction counts by type and status."""
    result = {}
    for model_name in ['Order', 'Invoice', 'Proposal', 'Purchase', 'WorkOrder']:
        try:
            Model = dj_apps.get_model('transactions', model_name)
            total = Model.objects.filter(is_deleted=False).count()
            by_status = dict(
                Model.objects.filter(is_deleted=False)
                .values_list('status')
                .annotate(count=Count('id'))
            )
            result[model_name.lower()] = {
                'total': total,
                'by_status': by_status,
            }
        except Exception:
            pass
    return result


def _get_locked_records() -> Dict[str, Any]:
    """Count of locked (journalized) records by type."""
    result = {}
    for model_name in ['Invoice', 'Payment']:
        try:
            Model = dj_apps.get_model('transactions', model_name)
            locked = Model.objects.filter(is_locked=True, is_deleted=False).count()
            unlocked = Model.objects.filter(is_locked=False, is_deleted=False).count()
            result[model_name.lower()] = {
                'locked': locked,
                'unlocked': unlocked,
            }
        except Exception:
            pass
    return result


def _get_aging_summary() -> Dict[str, Any]:
    """Aggregate aging across all customer orgs."""
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')

    customers = OrgBase.objects.filter(
        org_type='customer', is_active=True, is_deleted=False,
    )

    total_current = Decimal('0')
    total_30 = Decimal('0')
    total_60 = Decimal('0')
    total_90 = Decimal('0')
    customers_with_balance = 0

    for cust in customers:
        financial = getattr(cust, 'financial', None)
        if not isinstance(financial, dict):
            continue
        cust_fin = financial.get('customer', {})
        aging = cust_fin.get('aging', {})
        if not aging:
            continue

        current = Decimal(str(aging.get('current', 0) or 0))
        p1 = Decimal(str(aging.get('period_1', 0) or 0))
        p2 = Decimal(str(aging.get('period_2', 0) or 0))
        p3 = Decimal(str(aging.get('period_3', 0) or 0))

        if current + p1 + p2 + p3 > 0:
            customers_with_balance += 1
            total_current += current
            total_30 += p1
            total_60 += p2
            total_90 += p3

    return {
        'current': float(total_current),
        'period_1_30': float(total_30),
        'period_2_60': float(total_60),
        'period_3_90_plus': float(total_90),
        'total_ar': float(total_current + total_30 + total_60 + total_90),
        'customers_with_balance': customers_with_balance,
    }


def _get_pending_inventory() -> Dict[str, Any]:
    """Unprocessed inventory pending records."""
    Pending = dj_apps.get_model('core', 'Pending')

    unprocessed = Pending.objects.filter(
        model_name='item',
        purpose__startswith='inventory',
        dt_processed=0,
    )

    count = unprocessed.count()

    # Age of oldest unprocessed
    oldest = unprocessed.order_by('dt_created').values('dt_created').first()
    oldest_age_ms = 0
    if oldest and oldest['dt_created']:
        now_ms = int(timezone.now().timestamp() * 1000)
        oldest_age_ms = now_ms - oldest['dt_created']

    return {
        'unprocessed_count': count,
        'oldest_age_ms': oldest_age_ms,
        'oldest_age_minutes': round(oldest_age_ms / 60000, 1) if oldest_age_ms else 0,
    }
