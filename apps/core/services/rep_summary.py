"""Rep summary metrics for dashboard cards.

Graph notes:
  - Sales by rep (bar — trailing 30/90/365 days)
  - Margin by rep (bar — avg margin % per rep)
  - Order count by rep (bar — volume ranking)
  - Commission earned vs paid (stacked bar per rep)
"""
from apps.orgs.models import Rep


def get_rep_summary(params: dict = None) -> dict:
    total = Rep.objects.count()
    active = Rep.objects.filter(status='active').count()

    # Rep sales/margins require order->rep linkage.
    # Currently no rep FK on orders — metrics come from rep.financial JSON.
    # Iterate active reps and sum their financial data.
    total_sales = 0
    total_orders = 0
    for rep in Rep.objects.filter(status='active').only('financial'):
        fin = rep.get_flat_financial() if hasattr(rep, 'get_flat_financial') else {}
        total_sales += float(fin.get('ytd_sales', 0) or 0)
        total_orders += int(fin.get('ytd_orders', 0) or 0)

    return {
        "metrics": [
            {"label": "Count", "value": f"{total:,}"},
            {"label": "Active", "value": f"{active:,}"},
            {"label": "YTD Sales", "value": f"${total_sales:,.2f}"},
            {"label": "YTD Orders", "value": f"{total_orders:,}"},
        ],
    }
