"""Item summary metrics for dashboard cards.

Graph notes:
  - Inventory value by warehouse (stacked bar)
  - Price distribution histogram (how many items at each price tier)
  - Items with zero price or zero quantity (pie — healthy vs needs attention)
  - Inventory turns: qty sold / avg on hand over trailing 90 days (bar by category)
"""
import logging
from django.db.models import Count, Avg
from apps.products.models import Item

logger = logging.getLogger(__name__)


def get_item_summary(params: dict = None) -> dict:
    total = Item.objects.count()
    active = Item.objects.filter(is_active=True).count()

    # Average price from JSON field — need to iterate since price is JSON
    prices = []
    costs = []
    zero_price = 0
    for row in Item.objects.values_list('price', 'cost').iterator():
        p = row[0]
        c = row[1]
        if isinstance(p, dict):
            base = p.get('base')
            if base is not None:
                try:
                    val = float(base)
                    prices.append(val)
                    if val == 0:
                        zero_price += 1
                except (ValueError, TypeError):
                    pass
        if isinstance(c, dict):
            std = c.get('standard')
            if std is not None:
                try:
                    costs.append(float(std))
                except (ValueError, TypeError):
                    pass

    avg_price = sum(prices) / len(prices) if prices else 0
    avg_cost = sum(costs) / len(costs) if costs else 0

    return {
        "metrics": [
            {"label": "Count", "value": f"{total:,}"},
            {"label": "Active", "value": f"{active:,}"},
            {"label": "Avg Price", "value": f"${avg_price:,.2f}"},
            {"label": "Avg Cost", "value": f"${avg_cost:,.2f}"},
            {"label": "Zero Price", "value": f"{zero_price:,}"},
        ],
    }
