import pytest
from apps.transactions.models import Order, OrderLine

@pytest.mark.django_db
def test_order_update_sell_cost_totals():
    so = Order.objects.create()
    OrderLine.objects.create(
        order=so,
        price={"extended": 120.0, "discount_amount": 5.0, "unit": 120.0, "precision": 2},
        cost={"extended": 80.0, "tax": 0.0, "shipping": 5.0, "handling": 0.0, "freight": 0.0, "commissions": 0.0, "precision": 2},
    )
    OrderLine.objects.create(
        order=so,
        price={"extended": 30.0, "discount_amount": 0.0, "unit": 30.0, "precision": 2},
        cost={"extended": 20.0, "tax": 0.0, "shipping": 0.0, "handling": 0.0, "freight": 0.0, "commissions": 0.0, "precision": 2},
    )

    so.update_sell_cost_totals(persist=True)
    so.refresh_from_db()
    totals = so.totals

    # Subtotal = sum of line price.extended minus discounts = (120-5) + 30 = 145
    assert totals["subtotal"] == 145.0
    assert totals["total"] == 145.0 + totals["tax"] + totals["shipping"]
    assert totals["cost"] == 100.0  # 80 + 20
    assert round(totals["margin"], 2) == round(totals["total"] - 100.0, 2)
