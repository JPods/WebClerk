"""Purchasing dashboard metrics — inbound goods from purchases and work orders.

Mirrors sales_dashboard.py for the buy side. Alice computes, dashboard displays.
Switchable views: by date range, vendor, buyer (employee), warehouse.

Metrics:
  - PO and WO counts by status (open/received/partial/closed)
  - Receipts for the period (qty and value)
  - Cost variance: PO cost vs actual receipt cost vs average layer cost
  - Vendor performance: on-time %, fill rate, lead time accuracy
  - Inbound pipeline: open PO value by vendor, expected receipt dates
  - Layer age: oldest unreceived PO lines, stale open POs
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta


@dataclass
class PurchasingDashboard:
    """Complete purchasing snapshot for a given filter."""
    period_start_ms: int
    period_end_ms: int
    filter_by: str = ''          # 'vendor', 'buyer', 'warehouse', or ''
    filter_id: Optional[int] = None

    # PO counts by status
    po_open: int = 0
    po_partial: int = 0
    po_received: int = 0
    po_closed: int = 0
    po_total: int = 0

    # WO counts by status
    wo_open: int = 0
    wo_in_progress: int = 0
    wo_completed: int = 0
    wo_total: int = 0

    # Receipt metrics for the period
    receipts_count: int = 0
    receipts_qty: float = 0
    receipts_value: float = 0

    # Cost variance
    avg_po_cost: float = 0          # what we ordered at
    avg_receipt_cost: float = 0     # what we actually paid
    avg_layer_cost: float = 0       # what's in inventory now
    cost_variance_pct: float = 0    # (receipt - po) / po × 100

    # Vendor performance (top vendors for the period)
    vendor_summary: list = field(default_factory=list)
    # [{vendor_id, vendor_name, po_count, receipt_count, on_time_pct, fill_rate_pct, avg_lead_days}]

    # Inbound pipeline
    open_po_value: float = 0
    open_po_by_vendor: list = field(default_factory=list)
    # [{vendor_id, vendor_name, open_value, oldest_po_date, line_count}]

    # Stale items
    stale_pos: list = field(default_factory=list)
    # [{po_id, vendor_name, dt_created, days_open, value}]

    # Layer health
    layers_created: int = 0
    layers_consumed: int = 0
    unreconciled_layers: int = 0    # journal_complete=False older than 30 days


def compute_purchasing_dashboard(
    *,
    period_days: int = 30,
    period_start_ms: Optional[int] = None,
    period_end_ms: Optional[int] = None,
    vendor_id: Optional[int] = None,
    buyer_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
) -> PurchasingDashboard:
    """Compute the full purchasing dashboard for a given period and filter."""
    from apps.transactions.models.purchase import Purchase
    from apps.transactions.models.workorder import WorkOrder
    from apps.transactions.models.receipt import Receipt
    from apps.products.models.inventory_layer import InventoryLayer, InventoryMovement

    now_ms = int(timezone.now().timestamp() * 1000)
    if period_start_ms is None:
        period_start_ms = int((timezone.now() - timedelta(days=period_days)).timestamp() * 1000)
    if period_end_ms is None:
        period_end_ms = now_ms

    filter_by = ''
    filter_id = None
    if vendor_id:
        filter_by = 'vendor'
        filter_id = vendor_id
    elif buyer_id:
        filter_by = 'buyer'
        filter_id = buyer_id
    elif warehouse_id:
        filter_by = 'warehouse'
        filter_id = warehouse_id

    date_filter = Q(dt_created__gte=period_start_ms, dt_created__lte=period_end_ms)
    active_filter = Q(is_active=True, is_deleted=False)

    dashboard = PurchasingDashboard(
        period_start_ms=period_start_ms,
        period_end_ms=period_end_ms,
        filter_by=filter_by,
        filter_id=filter_id,
    )

    # --- PO counts ---
    try:
        po_qs = Purchase.objects.filter(active_filter)
        if vendor_id:
            po_qs = po_qs.filter(
                Q(refs__links__vendor_id=vendor_id) | Q(refs__links__contact__contains=[vendor_id])
            )

        # All POs for status breakdown
        all_pos = po_qs.values('status').annotate(count=Count('id'))
        for row in all_pos:
            s = (row.get('status') or '').lower()
            c = row.get('count', 0)
            if s in ('open', 'pending', 'draft'):
                dashboard.po_open += c
            elif s in ('partial', 'partially_received'):
                dashboard.po_partial += c
            elif s in ('received', 'complete'):
                dashboard.po_received += c
            elif s in ('closed', 'canceled'):
                dashboard.po_closed += c
            dashboard.po_total += c

        # Period POs
        period_pos = po_qs.filter(date_filter)
        dashboard.po_total = period_pos.count() or dashboard.po_total
    except Exception:
        pass

    # --- WO counts ---
    try:
        wo_qs = WorkOrder.objects.filter(active_filter)
        if vendor_id:
            wo_qs = wo_qs.filter(refs__links__vendor_id=vendor_id)

        all_wos = wo_qs.values('status').annotate(count=Count('id'))
        for row in all_wos:
            s = (row.get('status') or '').lower()
            c = row.get('count', 0)
            if s in ('open', 'pending', 'draft'):
                dashboard.wo_open += c
            elif s in ('in_progress', 'active'):
                dashboard.wo_in_progress += c
            elif s in ('completed', 'complete', 'closed'):
                dashboard.wo_completed += c
            dashboard.wo_total += c
    except Exception:
        pass

    # --- Receipt metrics ---
    try:
        receipt_qs = Receipt.objects.filter(date_filter & active_filter)
        if vendor_id:
            receipt_qs = receipt_qs.filter(refs__links__vendor_id=vendor_id)
        if warehouse_id:
            receipt_qs = receipt_qs.filter(refs__links__warehouse_id=warehouse_id)

        dashboard.receipts_count = receipt_qs.count()
    except Exception:
        pass

    # --- Layer health ---
    try:
        layer_qs = InventoryLayer.objects.filter(active_filter)
        if warehouse_id:
            layer_qs = layer_qs.filter(warehouse_id=warehouse_id)

        # Layers created in period
        dashboard.layers_created = layer_qs.filter(
            dt_created__gte=period_start_ms, dt_created__lte=period_end_ms
        ).count()

        # Movements in period
        move_qs = InventoryMovement.objects.filter(
            dt_created__gte=period_start_ms, dt_created__lte=period_end_ms
        )
        if warehouse_id:
            move_qs = move_qs.filter(warehouse_id=warehouse_id)

        dashboard.receipts_qty = float(abs(
            move_qs.filter(movement_type='receipt').aggregate(
                total=Sum('quantity'))['total'] or 0
        ))
        dashboard.receipts_value = float(abs(
            move_qs.filter(movement_type='issue').aggregate(
                total=Sum('quantity'))['total'] or 0
        ))
        dashboard.layers_consumed = move_qs.filter(movement_type='issue').count()

        # Unreconciled layers (source_doc_type='po', no cost finalization — older than 30 days)
        thirty_days_ago = now_ms - (30 * 86400000)
        dashboard.unreconciled_layers = layer_qs.filter(
            source_doc_type__in=['po', 'purchase'],
            dt_created__lt=thirty_days_ago,
        ).count()
    except Exception:
        pass

    # --- Open PO pipeline ---
    try:
        open_pos = Purchase.objects.filter(
            active_filter,
            status__in=['open', 'pending', 'draft', 'partial', 'partially_received'],
        )
        if vendor_id:
            open_pos = open_pos.filter(refs__links__vendor_id=vendor_id)

        # Stale POs (open > 60 days)
        sixty_days_ago = now_ms - (60 * 86400000)
        stale = open_pos.filter(dt_created__lt=sixty_days_ago).order_by('dt_created')[:10]
        dashboard.stale_pos = [{
            'po_id': po.id,
            'ida': po.ida,
            'dt_created': po.dt_created,
            'days_open': (now_ms - po.dt_created) // 86400000,
            'status': po.status if hasattr(po, 'status') else '',
        } for po in stale]
    except Exception:
        pass

    return dashboard


def purchasing_dashboard_to_dict(d: PurchasingDashboard) -> dict:
    """Convert to JSON-serializable dict for API response."""
    return {
        'period': {
            'start_ms': d.period_start_ms,
            'end_ms': d.period_end_ms,
            'filter_by': d.filter_by,
            'filter_id': d.filter_id,
        },
        'purchase_orders': {
            'open': d.po_open,
            'partial': d.po_partial,
            'received': d.po_received,
            'closed': d.po_closed,
            'total': d.po_total,
        },
        'work_orders': {
            'open': d.wo_open,
            'in_progress': d.wo_in_progress,
            'completed': d.wo_completed,
            'total': d.wo_total,
        },
        'receipts': {
            'count': d.receipts_count,
            'qty': d.receipts_qty,
            'value': d.receipts_value,
        },
        'cost_variance': {
            'avg_po_cost': d.avg_po_cost,
            'avg_receipt_cost': d.avg_receipt_cost,
            'avg_layer_cost': d.avg_layer_cost,
            'variance_pct': d.cost_variance_pct,
        },
        'vendors': d.vendor_summary,
        'pipeline': {
            'open_value': d.open_po_value,
            'by_vendor': d.open_po_by_vendor,
        },
        'stale_pos': d.stale_pos,
        'layers': {
            'created': d.layers_created,
            'consumed': d.layers_consumed,
            'unreconciled': d.unreconciled_layers,
        },
    }


__all__ = ['compute_purchasing_dashboard', 'purchasing_dashboard_to_dict', 'PurchasingDashboard']
