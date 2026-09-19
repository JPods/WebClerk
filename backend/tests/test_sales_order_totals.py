import pytest
from apps.transactions.models import Order, OrderLine

@pytest.mark.django_db
def test_order_update_sell_cost_totals():
    so = Order.objects.create()
    OrderLine.objects.create(
        order=so,
        quantity={"staged": 1, "active": 1},
        price={"amount": 120.0, "discount_amount": 5.0, "unit": 120.0, "precision": 2},
        cost={"unit": 80.0, "extended": 80.0, "tax": 0.0, "shipping": 5.0, "handling": 0.0, "freight": 0.0, "commissions": 0.0, "precision": 2},
    )
    OrderLine.objects.create(
        order=so,
        quantity={"staged": 1, "active": 1},
        price={"amount": 30.0, "discount_amount": 0.0, "unit": 30.0, "precision": 2},
        cost={"unit": 20.0, "extended": 20.0, "tax": 0.0, "shipping": 0.0, "handling": 0.0, "freight": 0.0, "commissions": 0.0, "precision": 2},
    )

    so.update_sell_cost_totals(persist=True)
    so.refresh_from_db()
    totals = so.totals

    # Subtotal = sum of line price.amount minus discounts = (120-5) + 30 = 145
    assert totals["amount"] == 145.0
    assert totals["total"] == 145.0 + totals["tax"] + totals["shipping"]
    assert totals["cost"] == 100.0  # 80 + 20
    # Margin is on goods (subtotal), not tax or shipping pass-through
    assert round(totals["margin"], 2) == round(totals["amount"] - 100.0, 2)
