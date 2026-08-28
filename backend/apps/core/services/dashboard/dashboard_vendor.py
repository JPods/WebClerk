"""Vendor summary metrics for dashboard cards.

Graph notes:
  - Open PO value by vendor (horizontal bar — who are we waiting on)
  - Vendor on-time delivery rate (bar — trailing 90 days)
  - Purchase volume trend (line — monthly spend by top 5 vendors)
"""
from django.db.models import Sum, Q
from apps.orgs.models import Vendor
from apps.transactions.models import Purchase


def get_vendor_summary(params: dict = None) -> dict:
    total = Vendor.objects.count()
    active = Vendor.objects.filter(status='active').count()

    # Open purchase orders
    from common.json_lookups import totals_total
    open_pos = Purchase.objects.filter(is_active=True).annotate(
        _total=totals_total(),
    ).aggregate(
        count=Sum('id', default=0),
        total=Sum('_total', default=0),
    )
    po_count = Purchase.objects.filter(is_active=True).count()
    po_total = open_pos.get('total') or 0

    return {
        "metrics": [
            {"label": "Count", "value": f"{total:,}"},
            {"label": "Active", "value": f"{active:,}"},
            {"label": "Open POs", "value": f"{po_count:,}"},
            {"label": "PO Value", "value": f"${po_total:,.2f}"},
        ],
    }
