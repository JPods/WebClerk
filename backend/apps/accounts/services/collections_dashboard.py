"""Collections dashboard data service.

Provides summary data for the collections dashboard widgets:
- Top past-due customers
- Days Sales Outstanding (DSO)
- Cash received this week
- Collection action counts
- Broken promises (overdue collection actions)

And per-customer health data:
- Aging breakdown
- Credit utilization
- Payment velocity and trend
- Health score (green / yellow / red)
"""
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from django.apps import apps as dj_apps
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_collections_dashboard() -> Dict[str, Any]:
    """Return all collections dashboard data in one call."""
    return {
        'top_past_due': _get_top_past_due(),
        'dso_current': _get_dso_current(),
        'cash_this_week': _get_cash_this_week(),
        'collection_actions': _get_collection_actions(),
        'promises_broken': _get_promises_broken(),
        'dt_generated': int(timezone.now().timestamp() * 1000),
    }


def get_customer_health(customer_id: int) -> Dict[str, Any]:
    """Return health data for a single customer."""
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')

    try:
        customer = OrgBase.objects.get(pk=customer_id)
    except OrgBase.DoesNotExist:
        return {'error': f'Customer {customer_id} not found'}

    aging = _extract_aging(customer)
    balance_due = aging['balance_due']
    credit = customer.financial.get('credit', {}) if isinstance(customer.financial, dict) else {}
    credit_limit = Decimal(str(credit.get('limit', 0) or 0))
    available_credit = float(credit_limit - Decimal(str(balance_due)))

    velocity_data = _get_payment_velocity(customer_id)
    last_payment = _get_last_payment(customer_id)
    open_invoices = _get_open_invoices(customer_id)

    # Health score
    health_score = _calculate_health_score(aging, velocity_data['payment_velocity'])

    return {
        'aging': aging,
        'credit_limit': float(credit_limit),
        'available_credit': available_credit,
        'payment_velocity': velocity_data['payment_velocity'],
        'velocity_trend': velocity_data['velocity_trend'],
        'last_payment': last_payment,
        'open_invoices': open_invoices,
        'health_score': health_score,
        'dt_generated': int(timezone.now().timestamp() * 1000),
    }


# ── Private helpers ──────────────────────────────────────────────────


def _get_top_past_due() -> list:
    """Top 10 customers by total past-due amount."""
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    Payment = dj_apps.get_model('transactions', 'Payment')

    customers = OrgBase.objects.filter(
        org_type='customer', is_active=True, is_deleted=False,
    )

    past_due_list = []
    for cust in customers:
        financial = getattr(cust, 'financial', None)
        if not isinstance(financial, dict):
            continue
        cust_fin = financial.get('customer', {})
        aging = cust_fin.get('aging', {})
        if not aging:
            continue

        p1 = Decimal(str(aging.get('period_1', 0) or 0))
        p2 = Decimal(str(aging.get('period_2', 0) or 0))
        p3 = Decimal(str(aging.get('period_3', 0) or 0))
        past_due_total = p1 + p2 + p3

        if past_due_total <= 0:
            continue

        # Days oldest — estimate from aging buckets
        if p3 > 0:
            days_oldest = 90
        elif p2 > 0:
            days_oldest = 60
        elif p1 > 0:
            days_oldest = 30
        else:
            days_oldest = 0

        # Last payment for this customer
        last_pmt = (
            Payment.objects.filter(
                customer_id=cust.pk, type='received',
                is_deleted=False, is_active=True,
            )
            .order_by('-dt_payment')
            .values('dt_payment', 'amount')
            .first()
        )

        past_due_list.append({
            'company': cust.display_name,
            'ida': cust.ida,
            'balance_due': float(past_due_total),
            'days_oldest': days_oldest,
            'last_payment_date': (
                last_pmt['dt_payment'].isoformat() if last_pmt and last_pmt['dt_payment'] else None
            ),
            'last_payment_amount': float(last_pmt['amount']) if last_pmt else None,
        })

    # Sort by balance_due descending, return top 10
    past_due_list.sort(key=lambda x: x['balance_due'], reverse=True)
    return past_due_list[:10]


def _get_dso_current() -> Dict[str, Any]:
    """Current DSO = (total AR / total credit sales last 90 days) * 90."""
    OrgBase = dj_apps.get_model('orgs', 'OrgBase')
    Invoice = dj_apps.get_model('transactions', 'Invoice')

    # Total AR from aging summary
    customers = OrgBase.objects.filter(
        org_type='customer', is_active=True, is_deleted=False,
    )
    total_ar = Decimal('0')
    for cust in customers:
        financial = getattr(cust, 'financial', None)
        if not isinstance(financial, dict):
            continue
        cust_fin = financial.get('customer', {})
        aging = cust_fin.get('aging', {})
        if not aging:
            continue
        total_ar += Decimal(str(aging.get('current', 0) or 0))
        total_ar += Decimal(str(aging.get('period_1', 0) or 0))
        total_ar += Decimal(str(aging.get('period_2', 0) or 0))
        total_ar += Decimal(str(aging.get('period_3', 0) or 0))

    # Credit sales last 90 days — invoices with status released or complete
    ninety_days_ago = timezone.now() - timedelta(days=90)
    ninety_days_ago_ms = int(ninety_days_ago.timestamp() * 1000)

    credit_sales = Invoice.objects.filter(
        invoice_type='invoice',
        is_deleted=False, is_active=True,
        status__in=['released', 'complete'],
        dt_created__gte=ninety_days_ago_ms,
    ).aggregate(total=Sum('total'))

    total_sales = Decimal(str(credit_sales['total'] or 0))

    if total_sales > 0:
        dso = float((total_ar / total_sales) * 90)
    else:
        dso = 0.0

    return {
        'dso': round(dso, 1),
        'total_ar': float(total_ar),
        'credit_sales_90d': float(total_sales),
    }


def _get_cash_this_week() -> Dict[str, Any]:
    """Total payments received in last 7 days with daily breakdown."""
    Payment = dj_apps.get_model('transactions', 'Payment')

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    received = Payment.objects.filter(
        type='received',
        is_deleted=False, is_active=True,
        dt_payment__gte=week_ago,
    )

    totals = received.aggregate(
        total=Sum('amount'),
        count=Count('id'),
    )

    # Daily breakdown
    daily = []
    for day_offset in range(7):
        day_start = (now - timedelta(days=6 - day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        day_end = day_start + timedelta(days=1)
        day_data = received.filter(
            dt_payment__gte=day_start, dt_payment__lt=day_end,
        ).aggregate(total=Sum('amount'), count=Count('id'))

        daily.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'total': float(day_data['total'] or 0),
            'count': day_data['count'],
        })

    return {
        'total': float(totals['total'] or 0),
        'count': totals['count'],
        'daily': daily,
    }


def _get_collection_actions() -> Dict[str, Any]:
    """Count of open collection actions and how many are overdue."""
    Action = dj_apps.get_model('core', 'Action')

    now_ms = int(timezone.now().timestamp() * 1000)

    open_collection = Action.objects.filter(
        project_name='collection',
        is_deleted=False, is_active=True,
    ).exclude(
        kanban_column='Complete',
    )

    total_open = open_collection.count()
    overdue = open_collection.filter(
        dt_deadline__gt=0,
        dt_deadline__lt=now_ms,
    ).count()

    return {
        'open': total_open,
        'overdue': overdue,
    }


def _get_promises_broken() -> int:
    """Count of collection actions still open past their deadline — broken promises."""
    Action = dj_apps.get_model('core', 'Action')

    now_ms = int(timezone.now().timestamp() * 1000)

    return Action.objects.filter(
        project_name='collection',
        is_deleted=False, is_active=True,
        dt_deadline__gt=0,
        dt_deadline__lt=now_ms,
    ).exclude(
        kanban_column='Complete',
    ).count()


def _extract_aging(customer) -> Dict[str, Any]:
    """Extract aging dict from customer's financial JSON."""
    financial = getattr(customer, 'financial', None)
    if not isinstance(financial, dict):
        return {'current': 0, 'past_1_30': 0, 'past_31_60': 0, 'past_61': 0, 'balance_due': 0}

    cust_fin = financial.get('customer', {})
    aging = cust_fin.get('aging', {})

    current = float(Decimal(str(aging.get('current', 0) or 0)))
    p1 = float(Decimal(str(aging.get('period_1', 0) or 0)))
    p2 = float(Decimal(str(aging.get('period_2', 0) or 0)))
    p3 = float(Decimal(str(aging.get('period_3', 0) or 0)))

    return {
        'current': current,
        'past_1_30': p1,
        'past_31_60': p2,
        'past_61': p3,
        'balance_due': current + p1 + p2 + p3,
    }


def _get_payment_velocity(customer_id: int) -> Dict[str, Any]:
    """Average days between invoice date and payment date for last 10 payments.

    Also compares last 5 vs prior 5 for trend.
    """
    Payment = dj_apps.get_model('transactions', 'Payment')

    # Get last 10 received payments that have an invoice
    payments = (
        Payment.objects.filter(
            customer_id=customer_id,
            type='received',
            is_deleted=False, is_active=True,
            invoice__isnull=False,
        )
        .select_related('invoice')
        .order_by('-dt_payment')[:10]
    )

    velocities = []
    for pmt in payments:
        if pmt.dt_payment and pmt.invoice and pmt.invoice.dt_created:
            # invoice.dt_created is epoch ms, dt_payment is DateTimeField
            invoice_dt = timezone.datetime.fromtimestamp(
                pmt.invoice.dt_created / 1000, tz=timezone.utc,
            )
            delta = (pmt.dt_payment - invoice_dt).days
            if delta >= 0:
                velocities.append(delta)

    if not velocities:
        return {'payment_velocity': None, 'velocity_trend': 'unknown'}

    avg_velocity = sum(velocities) / len(velocities)

    # Trend: compare last 5 vs prior 5
    # velocities[0] is most recent
    if len(velocities) >= 6:
        recent_5 = sum(velocities[:5]) / 5
        prior_5 = sum(velocities[5:]) / len(velocities[5:])
        if recent_5 < prior_5 - 3:
            trend = 'improving'
        elif recent_5 > prior_5 + 3:
            trend = 'deteriorating'
        else:
            trend = 'stable'
    else:
        trend = 'insufficient_data'

    return {
        'payment_velocity': round(avg_velocity, 1),
        'velocity_trend': trend,
    }


def _get_last_payment(customer_id: int) -> Optional[Dict[str, Any]]:
    """Most recent payment for a customer."""
    Payment = dj_apps.get_model('transactions', 'Payment')

    pmt = (
        Payment.objects.filter(
            customer_id=customer_id,
            type='received',
            is_deleted=False, is_active=True,
        )
        .order_by('-dt_payment')
        .values('dt_payment', 'amount')
        .first()
    )
    if not pmt:
        return None
    return {
        'date': pmt['dt_payment'].isoformat() if pmt['dt_payment'] else None,
        'amount': float(pmt['amount']),
    }


def _get_open_invoices(customer_id: int) -> Dict[str, Any]:
    """Count and total of invoices with balance > 0 for a customer."""
    Invoice = dj_apps.get_model('transactions', 'Invoice')

    open_inv = Invoice.objects.filter(
        customer_id=customer_id,
        invoice_type='invoice',
        is_deleted=False, is_active=True,
        balance__gt=0,
    ).aggregate(
        count=Count('id'),
        total=Sum('balance'),
    )

    return {
        'count': open_inv['count'],
        'total': float(open_inv['total'] or 0),
    }


def _calculate_health_score(aging: Dict[str, Any], velocity: Optional[float]) -> str:
    """Simple health score: green, yellow, red.

    Red:    past_61 > 0 OR velocity > 45 days
    Yellow: past_1_30 + past_31_60 > 0 OR velocity > 30 days
    Green:  current only, velocity <= 30 days
    """
    if aging['past_61'] > 0:
        return 'red'
    if velocity is not None and velocity > 45:
        return 'red'
    if aging['past_31_60'] > 0:
        return 'yellow'
    if aging['past_1_30'] > 0:
        return 'yellow'
    if velocity is not None and velocity > 30:
        return 'yellow'
    return 'green'
