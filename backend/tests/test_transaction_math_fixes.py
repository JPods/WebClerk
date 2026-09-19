"""Regression tests for the Bite 1 transaction-math findings (assessment 2026-09-19).

readmes/assessments/2026-09-19/bite-1-transaction-math/comparison.md in ~/Allie
lists the findings; each test names the one it covers.
"""
from __future__ import annotations

import pytest

from apps.transactions.models import Order, OrderLine, Quote, QuoteLine
from apps.transactions.services.convert.convert import convert_quote_to_order
from apps.transactions.services.transaction_save import calculate_header_totals


def _line(quote, qty, unit, *, discount_amount=0.0, discount_percent=0, cost=0.0,
          tax_code='', line_type='product'):
    return QuoteLine.objects.create(
        quote=quote,
        line_type=line_type,
        quantity={"active": qty},
        price={"unit": unit, "discount_amount": discount_amount,
               "discount_percent": discount_percent, "precision": 2},
        cost={"unit": cost, "tax_code": tax_code, "precision": 2},
    )


def _order_line_from(order, src, qty):
    """Save a child line the way the review screen does: price copied, refs.source set."""
    return OrderLine.objects.create(
        order=order,
        line_type=src.line_type,
        quantity={"active": qty},
        price=dict(src.price),
        cost=dict(src.cost),
        refs={"source": {"quote_line_id": src.pk}},
    )


@pytest.mark.django_db
def test_taxable_is_the_base_tax_was_computed_on():
    """#4: taxable = net of line discounts, once; non-taxable lines excluded."""
    q = Quote.objects.create(finance={"sales_tax_rate": 0.05})
    _line(q, 15, 10.00)                                  # 150.00
    _line(q, 3, 19.99, discount_percent=12.5)            # 59.97 − 7.50 = 52.47
    _line(q, 2, 7.33, discount_amount=1.00, tax_code='NONTAXABLE')  # 13.66, untaxed
    q.refresh_from_db()
    assert q.totals["subtotal"] == pytest.approx(216.13)
    assert q.totals["taxable"] == pytest.approx(202.47)
    assert q.totals["tax"] == pytest.approx(10.12)       # 7.50 + 2.62


@pytest.mark.django_db
def test_header_rate_change_recomputes_totals():
    """#5: setting the tax rate after the lines exist changes the tax at once."""
    q = Quote.objects.create()
    _line(q, 4, 10.00)
    q.refresh_from_db()
    assert q.totals["tax"] == 0.0
    q.finance = {"sales_tax_rate": 10}                   # percent form is accepted
    q.save()
    q.refresh_from_db()
    assert q.totals["tax"] == pytest.approx(4.00)
    assert q.totals["total"] == pytest.approx(44.00)


@pytest.mark.django_db
def test_conversion_keeps_line_type_and_tax_rate():
    """#1, #3: a discount line stays a discount; the order keeps the quote's tax rate."""
    q = Quote.objects.create(finance={"sales_tax_rate": 0.05, "sales_tax_name": "test"})
    _line(q, 1, 100.00)
    _line(q, 1, 10.00, line_type='discount')
    result = convert_quote_to_order(q.pk)
    order = Order.objects.get(pk=result["order_id"])
    assert order.finance.get("sales_tax_rate") == 0.05
    assert [l["line_type"] for l in result["lines"]] == ["product", "discount"]


@pytest.mark.django_db
def test_flat_discount_is_shared_across_partial_conversions():
    """#2: $5 flat on 2 units, converted 1 + 1, carries 2.50 + 2.50, never 5 + 5."""
    q = Quote.objects.create()
    src = _line(q, 2, 25.00, discount_amount=5.00)
    o1 = Order.objects.create()
    first = _order_line_from(o1, src, 1)
    o2 = Order.objects.create()
    second = _order_line_from(o2, src, 1)
    first.refresh_from_db(); second.refresh_from_db()
    assert first.price["discount_amount"] == pytest.approx(2.50)
    assert second.price["discount_amount"] == pytest.approx(2.50)
    assert first.price["extended"] + second.price["extended"] == pytest.approx(45.00)


@pytest.mark.django_db
def test_flat_discount_last_child_takes_the_remainder():
    """#2: $1 flat on 3 units, converted 1 + 1 + 1 → 0.33 + 0.33 + 0.34 = 1.00."""
    q = Quote.objects.create()
    src = _line(q, 3, 5.00, discount_amount=1.00)
    shares = []
    for _ in range(3):
        child = _order_line_from(Order.objects.create(), src, 1)
        child.refresh_from_db()
        shares.append(child.price["discount_amount"])
    assert shares == [pytest.approx(0.33), pytest.approx(0.33), pytest.approx(0.34)]


@pytest.mark.django_db
def test_verifier_uses_the_same_engine():
    """#9: the pre-save verifier agrees with the engine for 5 and 0.05 alike."""
    lines = [
        {"line_type": "product", "quantity": {"active": 2}, "price": {"unit": 50.0}, "cost": {}},
        {"line_type": "discount", "quantity": {"active": 1}, "price": {"unit": 10.0}, "cost": {}},
    ]
    for rate in (5, 0.05):
        t = calculate_header_totals(lines, {"finance": {"sales_tax_rate": rate}}, "quote")
        assert float(t["subtotal"]) == pytest.approx(90.00)
        assert float(t["tax"]) == pytest.approx(4.50)   # tax on the discounted price
        assert float(t["total"]) == pytest.approx(94.50)


@pytest.mark.django_db
def test_tax_is_applied_to_the_discounted_price():
    """Bill 2026-09-19: a document discount comes off the taxable amount, spread over
    the taxable and non-taxable lines by their nets (calc 06 of Bite 1)."""
    q = Quote.objects.create(finance={"sales_tax_rate": 0.05})
    _line(q, 15, 10.00)                                              # 150.00
    _line(q, 3, 19.99, discount_percent=12.5)                        # 52.47
    _line(q, 2, 7.33, discount_amount=1.00, tax_code='NONTAXABLE')   # 13.66
    _line(q, 1, 10.00, line_type='discount')                         # −10.00
    q.refresh_from_db()
    # factor = 1 − 10 / 216.13; taxable lines 150.00 → 143.06, 52.47 → 50.04
    assert q.totals["subtotal"] == pytest.approx(206.13)
    assert q.totals["taxable"] == pytest.approx(193.10)
    assert q.totals["tax"] == pytest.approx(9.65)                    # 7.15 + 2.50, rounded per line
