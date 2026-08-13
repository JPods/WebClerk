"""
Sales Pipeline Service — Connect actions to future outcomes.

Funnel: Actions → Proposals → Orders → Revenue (Invoices)

Each stage counts records and dollar values. Actions carry a
predicted_impact score (1-5, user's gut feel). The pipeline
compares predicted impact against actual outcomes to calibrate
judgment over time.
"""
from __future__ import annotations

import time
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.db.models import Sum, Count, Q, Avg


def _now_ms():
    return int(time.time() * 1000)


def _period_filter(year: int = None, month: int = None) -> dict:
    """Build dt_created filter for a year/month period."""
    if not year or not month:
        return {}
    import calendar
    from datetime import date
    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year + 1, 1, 1)
    else:
        period_end = date(year, month + 1, 1)
    start_ms = int(calendar.timegm(period_start.timetuple()) * 1000)
    end_ms = int(calendar.timegm(period_end.timetuple()) * 1000)
    return {'dt_created__gte': start_ms, 'dt_created__lt': end_ms}


def get_sales_pipeline(
    year: int = None,
    month: int = None,
    months: int = 1,
    customer_id: int = None,
) -> Dict[str, Any]:
    """Return the full sales funnel with conversion rates and impact analysis.

    Args:
        year/month: period filter (optional — default is all time)
        months: span in months (default 1)
        customer_id: filter to a single customer

    Returns:
        {stages: [...], conversions: [...], impact_analysis: {...},
         by_action_type: [...], by_rep: [...], summary: {...}}
    """
    Action = dj_apps.get_model('core', 'Action')
    Proposal = dj_apps.get_model('transactions', 'Proposal')
    Order = dj_apps.get_model('transactions', 'Order')
    Invoice = dj_apps.get_model('transactions', 'Invoice')

    # Build period filters
    pf = {}
    if year and month:
        import calendar
        from datetime import date
        period_start = date(year, month, 1)
        end_month = month + months - 1
        end_year = year
        while end_month > 12:
            end_month -= 12
            end_year += 1
        period_end = (
            date(end_year, end_month + 1, 1) if end_month < 12
            else date(end_year + 1, 1, 1)
        )
        start_ms = int(calendar.timegm(period_start.timetuple()) * 1000)
        end_ms = int(calendar.timegm(period_end.timetuple()) * 1000)
        pf = {'dt_created__gte': start_ms, 'dt_created__lt': end_ms}

    # Customer filter
    cf = {'customer_id': customer_id} if customer_id else {}
    # Actions use contact_id, not customer_id
    acf = {'contact_id': customer_id} if customer_id else {}

    # ---- Stage 1: Actions (selling actions) ----
    action_qs = Action.objects.filter(
        is_active=True, is_deleted=False,
        **pf, **acf,
    ).exclude(action_type='')

    action_count = action_qs.count()
    action_by_type = list(
        action_qs.values('action_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    # Impact is a JSONField — aggregate in Python, not ORM
    action_by_impact = _count_by_impact(action_qs)

    # ---- Stage 2: Proposals ----
    proposal_qs = Proposal.objects.filter(
        is_active=True, is_deleted=False,
        **pf, **cf,
    )
    proposal_count = proposal_qs.count()
    proposal_value = float(
        proposal_qs.aggregate(s=Sum('total'))['s'] or 0
    )

    # ---- Stage 3: Orders (from proposals) ----
    order_qs = Order.objects.filter(
        is_active=True, is_deleted=False,
        **pf, **cf,
    )
    order_count = order_qs.count()
    order_value = float(
        order_qs.aggregate(s=Sum('total'))['s'] or 0
    )

    # Orders that came from proposals
    orders_from_proposals = order_qs.filter(
        parent_model='proposal',
    ).exclude(parent_id__isnull=True).exclude(parent_id=0)
    converted_count = orders_from_proposals.count()
    converted_value = float(
        orders_from_proposals.aggregate(s=Sum('total'))['s'] or 0
    )

    # ---- Stage 4: Revenue (invoiced) ----
    invoice_qs = Invoice.objects.filter(
        is_active=True, is_deleted=False,
        **pf, **cf,
    )
    invoice_count = invoice_qs.count()
    invoice_value = float(
        invoice_qs.aggregate(s=Sum('total'))['s'] or 0
    )

    # Invoices from orders
    invoices_from_orders = invoice_qs.filter(
        parent_model='order',
    ).exclude(parent_id__isnull=True).exclude(parent_id=0)
    invoiced_from_orders_count = invoices_from_orders.count()
    invoiced_from_orders_value = float(
        invoices_from_orders.aggregate(s=Sum('total'))['s'] or 0
    )

    # ---- Conversion rates ----
    def _rate(num, denom):
        return round(num / denom * 100, 1) if denom > 0 else 0

    conversions = [
        {
            'from': 'actions', 'to': 'proposals',
            'from_count': action_count, 'to_count': proposal_count,
            'rate': _rate(proposal_count, action_count),
        },
        {
            'from': 'proposals', 'to': 'orders',
            'from_count': proposal_count, 'to_count': converted_count,
            'rate': _rate(converted_count, proposal_count),
            'value_converted': converted_value,
        },
        {
            'from': 'orders', 'to': 'invoices',
            'from_count': order_count, 'to_count': invoiced_from_orders_count,
            'rate': _rate(invoiced_from_orders_count, order_count),
            'value_invoiced': invoiced_from_orders_value,
        },
    ]

    # ---- Impact analysis: predicted vs actual ----
    # For actions with predicted_impact, trace forward to see if they
    # led to proposals/orders within a reasonable time window
    impact_analysis = _analyze_impact(action_qs, Proposal, Order, pf, cf)

    # ---- By rep (contact_id on actions) ----
    by_rep = list(
        action_qs.exclude(contact_id=0)
        .values('contact_id')
        .annotate(action_count=Count('id'))
        .order_by('-action_count')[:20]
    )

    # ---- Stages for the funnel visual ----
    stages = [
        {
            'name': 'Actions',
            'count': action_count,
            'value': None,
            'color': '#6366f1',  # indigo
        },
        {
            'name': 'Proposals',
            'count': proposal_count,
            'value': proposal_value,
            'color': '#8b5cf6',  # violet
        },
        {
            'name': 'Orders',
            'count': order_count,
            'value': order_value,
            'color': '#3b82f6',  # blue
        },
        {
            'name': 'Revenue',
            'count': invoice_count,
            'value': invoice_value,
            'color': '#10b981',  # emerald
        },
    ]

    return {
        'stages': stages,
        'conversions': conversions,
        'impact_analysis': impact_analysis,
        'by_action_type': action_by_type,
        'by_impact_level': action_by_impact,
        'by_rep': by_rep,
        'summary': {
            'action_count': action_count,
            'proposal_count': proposal_count,
            'order_count': order_count,
            'invoice_count': invoice_count,
            'proposal_value': proposal_value,
            'order_value': order_value,
            'invoice_value': invoice_value,
            'conversion_actions_to_orders': _rate(order_count, action_count),
            'conversion_proposals_to_orders': _rate(converted_count, proposal_count),
            'conversion_orders_to_revenue': _rate(invoiced_from_orders_count, order_count),
        },
        'period': f'{year}-{month:02d}' if year and month else 'all',
        'dt_generated': _now_ms(),
    }


def _get_impact_predicted(action) -> int:
    """Extract impact.predicted from an action's JSON field. Returns 0 if missing."""
    impact = getattr(action, 'impact', None)
    if isinstance(impact, dict):
        return int(impact.get('predicted', 0) or 0)
    return 0


def _count_by_impact(action_qs) -> list:
    """Count actions by impact.predicted level. JSON field — must aggregate in Python."""
    counts = defaultdict(int)
    for action in action_qs.exclude(impact={}).exclude(impact__isnull=True):
        level = _get_impact_predicted(action)
        if level > 0:
            counts[level] += 1
    return [{'predicted': k, 'count': v} for k, v in sorted(counts.items())]


def _analyze_impact(action_qs, Proposal, Order, pf, cf):
    """Compare predicted impact against actual outcomes — retrospection, not precision.

    Groups actions by impact.predicted level and checks how many of their
    associated customers produced proposals/orders. The gap between predicted
    and actual is the learning signal.
    """
    contacts_by_level = defaultdict(set)
    counts_by_level = defaultdict(int)
    # Track actions that have both predicted and actual for calibration
    calibration_gaps = []

    for action in action_qs.exclude(contact_id=0).exclude(impact={}).exclude(impact__isnull=True):
        impact = action.impact if isinstance(action.impact, dict) else {}
        predicted = int(impact.get('predicted', 0) or 0)
        actual = int(impact.get('actual', 0) or 0)
        if predicted == 0:
            continue
        contacts_by_level[predicted].add(action.contact_id)
        counts_by_level[predicted] += 1
        if actual > 0:
            calibration_gaps.append({
                'predicted': predicted,
                'actual': actual,
                'gap': predicted - actual,
                'action_id': action.pk,
            })

    results = []
    for level in sorted(contacts_by_level.keys()):
        contact_ids = contacts_by_level[level]
        proposal_customers = set(
            Proposal.objects.filter(
                customer_id__in=contact_ids,
                is_active=True, is_deleted=False,
                **pf,
            ).values_list('customer_id', flat=True).distinct()
        )
        order_customers = set(
            Order.objects.filter(
                customer_id__in=contact_ids,
                is_active=True, is_deleted=False,
                **pf,
            ).values_list('customer_id', flat=True).distinct()
        )

        total_contacts = len(contact_ids)
        results.append({
            'predicted_level': level,
            'action_count': counts_by_level[level],
            'unique_contacts': total_contacts,
            'contacts_with_proposals': len(proposal_customers),
            'contacts_with_orders': len(order_customers),
            'proposal_rate': round(
                len(proposal_customers) / total_contacts * 100, 1
            ) if total_contacts > 0 else 0,
            'order_rate': round(
                len(order_customers) / total_contacts * 100, 1
            ) if total_contacts > 0 else 0,
        })

    # Calibration summary — how good are the predictions?
    avg_gap = 0
    if calibration_gaps:
        avg_gap = round(sum(g['gap'] for g in calibration_gaps) / len(calibration_gaps), 2)

    return {
        'by_level': results,
        'calibration': {
            'actions_with_both': len(calibration_gaps),
            'avg_gap': avg_gap,  # positive = over-optimistic, negative = under-estimating
            'note': (
                'Gap = predicted - actual. Positive means over-optimistic. '
                'Negative means under-estimating. Zero means perfect calibration. '
                'The numbers are waffly — the retrospection is where the value is.'
            ),
        },
    }
