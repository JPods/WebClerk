"""Customer summary metrics for dashboard cards.

Graph notes:
  - Customer acquisition over time (line — new customers per month)
  - Status distribution (pie — active, prospect, inactive)
  - Revenue concentration (top 10 customers as % of total — Pareto bar)
  - Customer lifetime value distribution (histogram)
"""
from apps.orgs.models import Customer


def get_customer_summary(params: dict = None) -> dict:
    total = Customer.objects.count()
    active = Customer.objects.filter(status='active').count()
    prospect = Customer.objects.filter(status='prospect').count()
    inactive = total - active - prospect

    return {
        "metrics": [
            {"label": "Count", "value": f"{total:,}"},
            {"label": "Active", "value": f"{active:,}"},
            {"label": "Prospect", "value": f"{prospect:,}"},
            {"label": "Inactive", "value": f"{inactive:,}"},
        ],
    }
