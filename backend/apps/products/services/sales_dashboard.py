"""Sales dashboard metrics — Alice computes, dashboard displays.

Switchable views: by date range, salesperson, rep, customer.
No approval gates — flag and ship, review here.

Metrics:
  - Transaction counts by type (order/invoice/proposal)
  - Margin velocity for the period
  - Order and invoice counts with below/above margin identification
  - Margin velocity by item
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from django.db.models import Count, Sum, Q, F, Avg
from django.utils import timezone
from datetime import timedelta


@dataclass
class SalesDashboard:
    """Complete dashboard snapshot for a given filter."""
    period_start_ms: int
    period_end_ms: int
    filter_by: str = ''          # 'salesperson', 'rep', 'customer', or ''
    filter_id: Optional[int] = None

    # Transaction counts
    order_count: int = 0
    invoice_count: int = 0
    proposal_count: int = 0

    # Revenue
    order_total: float = 0
    invoice_total: float = 0
    proposal_total: float = 0

    # Margin
    avg_margin_pct: float = 0
    above_margin_count: int = 0
    below_margin_count: int = 0
    margin_floor: float = 20.0   # default floor for flagging

    # Margin velocity
    avg_margin_velocity: float = 0
    top_velocity_items: list = field(default_factory=list)
    dead_capital_items: list = field(default_factory=list)
    volume_driver_items: list = field(default_factory=list)
    star_items: list = field(default_factory=list)

    # Below/above margin transactions
    below_margin_orders: list = field(default_factory=list)
    below_margin_invoices: list = field(default_factory=list)


def compute_dashboard(
    *,
    period_days: int = 30,
    period_start_ms: Optional[int] = None,
    period_end_ms: Optional[int] = None,
    salesperson_id: Optional[int] = None,
    rep_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    margin_floor: float = 20.0,
) -> SalesDashboard:
    """Compute the full sales dashboard for a given period and filter."""
    from apps.transactions.models.order import Order
    from apps.transactions.models.invoice import Invoice
    from apps.transactions.models.proposal import Proposal
    from apps.products.models.item import Item

    now_ms = int(timezone.now().timestamp() * 1000)
    if period_start_ms is None:
        period_start_ms = int((timezone.now() - timedelta(days=period_days)).timestamp() * 1000)
    if period_end_ms is None:
        period_end_ms = now_ms

    # Determine filter
    filter_by = ''
    filter_id = None
    contact_filter = Q()
    if salesperson_id:
        filter_by = 'salesperson'
        filter_id = salesperson_id
        contact_filter = Q(refs__links__salesperson_id=salesperson_id)
    elif rep_id:
        filter_by = 'rep'
        filter_id = rep_id
        contact_filter = Q(refs__links__rep_id=rep_id)
    elif customer_id:
        filter_by = 'customer'
        filter_id = customer_id
        contact_filter = Q(refs__links__customer_id=customer_id) | Q(refs__links__contact__contains=[customer_id])

    date_filter = Q(dt_created__gte=period_start_ms, dt_created__lte=period_end_ms)

    dashboard = SalesDashboard(
        period_start_ms=period_start_ms,
        period_end_ms=period_end_ms,
        filter_by=filter_by,
        filter_id=filter_id,
        margin_floor=margin_floor,
    )

    # --- Transaction counts ---
    try:
        orders = Order.objects.filter(date_filter & contact_filter & Q(is_active=True, is_deleted=False))
        dashboard.order_count = orders.count()
        dashboard.order_total = float(orders.aggregate(
            total=Sum('cost__total'))['total'] or 0) if hasattr(Order, 'cost') else 0
    except Exception:
        pass

    try:
        invoices = Invoice.objects.filter(date_filter & contact_filter & Q(is_active=True, is_deleted=False))
        dashboard.invoice_count = invoices.count()
        dashboard.invoice_total = float(invoices.aggregate(
            total=Sum('cost__total'))['total'] or 0) if hasattr(Invoice, 'cost') else 0
    except Exception:
        pass

    try:
        proposals = Proposal.objects.filter(date_filter & contact_filter & Q(is_active=True, is_deleted=False))
        dashboard.proposal_count = proposals.count()
    except Exception:
        pass

    # --- Margin velocity by item ---
    try:
        items_qs = Item.objects.filter(is_active=True, is_deleted=False, margin_velocity__gt=0)
        if items_qs.exists():
            dashboard.avg_margin_velocity = float(
                items_qs.aggregate(avg=Avg('margin_velocity'))['avg'] or 0
            )
            dashboard.avg_margin_pct = float(
                items_qs.aggregate(avg=Avg('margin_pct'))['avg'] or 0
            )

            # Categorized items
            dashboard.star_items = list(
                items_qs.filter(velocity_category='star')
                .values('id', 'ida', 'name', 'margin_velocity', 'margin_pct', 'annual_turns')
                .order_by('-margin_velocity')[:10]
            )
            dashboard.dead_capital_items = list(
                items_qs.filter(velocity_category='dead_capital')
                .values('id', 'ida', 'name', 'margin_velocity', 'margin_pct', 'annual_turns')
                .order_by('annual_turns')[:10]
            )
            dashboard.volume_driver_items = list(
                items_qs.filter(velocity_category='volume_driver')
                .values('id', 'ida', 'name', 'margin_velocity', 'margin_pct', 'annual_turns')
                .order_by('-annual_turns')[:10]
            )
            dashboard.top_velocity_items = list(
                items_qs.values('id', 'ida', 'name', 'margin_velocity', 'margin_pct', 'annual_turns')
                .order_by('-margin_velocity')[:10]
            )

            # Above/below margin counts
            dashboard.above_margin_count = items_qs.filter(margin_pct__gte=margin_floor).count()
            dashboard.below_margin_count = items_qs.filter(margin_pct__lt=margin_floor).count()
    except Exception:
        pass

    return dashboard


def dashboard_to_dict(d: SalesDashboard) -> dict:
    """Convert dashboard to JSON-serializable dict for API response."""
    return {
        'period': {
            'start_ms': d.period_start_ms,
            'end_ms': d.period_end_ms,
            'filter_by': d.filter_by,
            'filter_id': d.filter_id,
        },
        'transactions': {
            'orders': {'count': d.order_count, 'total': d.order_total},
            'invoices': {'count': d.invoice_count, 'total': d.invoice_total},
            'proposals': {'count': d.proposal_count, 'total': d.proposal_total},
        },
        'margin': {
            'avg_pct': d.avg_margin_pct,
            'floor': d.margin_floor,
            'above_count': d.above_margin_count,
            'below_count': d.below_margin_count,
        },
        'velocity': {
            'avg': d.avg_margin_velocity,
            'stars': d.star_items,
            'dead_capital': d.dead_capital_items,
            'volume_drivers': d.volume_driver_items,
            'top_items': d.top_velocity_items,
        },
    }


__all__ = ['compute_dashboard', 'dashboard_to_dict', 'SalesDashboard']
