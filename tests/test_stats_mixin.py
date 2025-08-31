import math
from django.utils import timezone

from apps.products.models import Item
from apps.orgs.models import OrgBase, OrgType


def test_stats_transaction_and_margin(db):
    item = Item.objects.create(name="Widget A")
    # First sale with 30% margin (0.30)
    item.record_transaction("sale", value=100.0, margin_value=0.30)
    item.save()
    stats = item.stats
    assert stats["counts"]["tx_sale_count"] == 1
    assert stats["counts"]["tx_total"] == 1
    assert stats["values"]["tx_sale_total_value"] == 100.0
    assert math.isclose(stats["values"]["avg_margin_pct"], 0.30, rel_tol=1e-6)
    assert math.isclose(stats["values"]["last_margin_pct"], 0.30, rel_tol=1e-6)
    assert stats["last"].get("dt_last_sale")

    # Second sale with 50% margin -> average should update to (0.30 + 0.50)/2 = 0.40
    item.record_transaction("sale", value=50.0, margin_value=0.50)
    item.save()
    stats = item.stats
    assert stats["counts"]["tx_sale_count"] == 2
    assert stats["values"]["tx_sale_total_value"] == 150.0
    assert math.isclose(stats["values"]["avg_margin_pct"], 0.40, rel_tol=1e-6)
    assert math.isclose(stats["values"]["last_margin_pct"], 0.50, rel_tol=1e-6)

    # Record a return without margin update
    item.record_transaction("return", value= -20.0)
    item.save()
    stats = item.stats
    assert stats["counts"]["tx_return_count"] == 1
    assert stats["counts"]["tx_total"] == 3
    assert stats["values"]["tx_return_total_value"] == -20.0
    assert "dt_last_return" in stats["last"]


def test_stats_service_call_and_series(db):
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name="Acme Corp")
    # Record service calls
    org.record_service_call()
    org.record_service_call()
    org.save()
    stats = org.stats
    assert stats["counts"]["service_calls"] == 2
    assert "dt_last_service_call" in stats["last"]

    # Series push & capping
    for i in range(60):
        org.push_series("weekly_sales", i, max_len=50)
    org.save()
    stats = org.stats
    assert len(stats["series"]["weekly_sales"]) == 50  # capped
    # ensure newest value present
    assert stats["series"]["weekly_sales"][-1]["v"] == 59


def test_stats_basic_counters_and_values(db):
    item = Item.objects.create(name="Widget B")
    item.inc_stat("page_views")
    item.inc_stat("page_views", 4)
    item.set_value("rating", 4.7)
    item.save()
    stats = item.stats
    assert stats["counts"]["page_views"] == 5
    assert stats["values"]["rating"] == 4.7
