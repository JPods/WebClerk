import pytest
from apps.transactions.models import Order, OrderLine

@pytest.mark.django_db
def test_order_update_sell_cost_totals():
    so = Order.objects.create()
    OrderLine.objects.create(
        parent=so,
        price={"extended": 120.0, "discount_amount": 5.0, "unit": 120.0, "precision": 2},
        cost={"extended": 80.0, "tax": 0.0, "shipping": 5.0, "handling": 0.0, "freight": 0.0, "commissions": 0.0, "precision": 2},
    )
    OrderLine.objects.create(
        parent=so,
        price={"extended": 30.0, "discount_amount": 0.0, "unit": 30.0, "precision": 2},
        cost={"extended": 20.0, "tax": 0.0, "shipping": 0.0, "handling": 0.0, "freight": 0.0, "commissions": 0.0, "precision": 2},
    )

    computed = so.update_sell_cost_totals(persist=False)

    assert computed["sell"]["line_sum_goods"] == 150.0
    assert computed["sell"]["discount"] == 5.0
    assert computed["sell"]["total"] == 150.0

    assert computed["cost"]["line_sum_goods"] == 100.0
    assert computed["cost"]["line_sum_shipping"] == 5.0
    assert computed["cost"]["total"] == 105.0

    assert computed["totals"]["total"] == 150.0
    assert computed["totals"]["cost"] == 105.0
    assert round(computed["totals"]["margin"], 2) == 45.0