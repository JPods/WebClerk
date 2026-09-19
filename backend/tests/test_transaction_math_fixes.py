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
        {"line_type": "product", "quantity": {"active": 2},
         "price": {"unit": 50.0, "discount_amount": 10.0}, "cost": {}},
    ]
    for rate in (5, 0.05):
        t = calculate_header_totals(lines, {"finance": {"sales_tax_rate": rate}}, "quote")
        assert float(t["subtotal"]) == pytest.approx(90.00)
        assert float(t["tax"]) == pytest.approx(4.50)   # tax on the discounted price
        assert float(t["total"]) == pytest.approx(94.50)


@pytest.mark.django_db
def test_tax_is_applied_to_the_discounted_price():
    """Bill 2026-09-19: a document discount is spread into the line discounts by line
    amount; each line is taxed on its own discounted amount (calc 06 of Bite 1)."""
    q = Quote.objects.create(finance={"sales_tax_rate": 0.05})
    a = _line(q, 15, 10.00)                                              # 150.00
    b = _line(q, 3, 19.99, discount_percent=12.5)                        # 52.47
    c = _line(q, 2, 7.33, discount_amount=1.00, tax_code='NONTAXABLE')   # 13.66
    d = _line(q, 1, 10.00, line_type='discount')                         # $10 off the document
    for l in (a, b, c, d):
        l.refresh_from_db()
    # shares by amount: 6.94 / 2.43 / 0.63 (the last takes the remainder)
    assert [a.price["discount_amount"], b.price["discount_amount"], c.price["discount_amount"]] == \
        [pytest.approx(6.94), pytest.approx(9.93), pytest.approx(1.63)]
    assert [a.price["extended"], b.price["extended"], c.price["extended"]] == \
        [pytest.approx(143.06), pytest.approx(50.04), pytest.approx(13.03)]
    assert d.price["extended"] == 0 and d.metadata["document_discount"]["applied"] == 10.0
    # the tax is stored on each line
    assert a.tax["sales"] == pytest.approx(7.15) and b.tax["sales"] == pytest.approx(2.50)
    assert c.tax["sales"] == 0 and c.tax["rate_source"] == "item_exempt"
    q.refresh_from_db()
    assert q.totals["subtotal"] == pytest.approx(206.13)
    assert q.totals["taxable"] == pytest.approx(193.10)
    assert q.totals["tax"] == pytest.approx(9.65)
    assert q.totals["total"] == pytest.approx(215.78)


@pytest.mark.django_db
def test_document_total_includes_other_charges():
    """Total = amount + line taxes + shipping + finance charge + other (landed costs)."""
    q = Quote.objects.create(finance={"sales_tax_rate": 0.10}, totals={"other": 7.00})
    _line(q, 2, 10.00)
    q.refresh_from_db()
    assert q.totals["tax"] == pytest.approx(2.00)
    assert q.totals["total"] == pytest.approx(29.00)          # 20 + 2 + 7


@pytest.mark.django_db
def test_a_rate_typed_on_the_line_wins():
    q = Quote.objects.create(finance={"sales_tax_rate": 0.10})
    line = QuoteLine.objects.create(
        quote=q, quantity={"active": 1}, price={"unit": 100.0, "precision": 2},
        cost={"unit": 0}, tax={"sales_rate": 0.02, "rate_source": "line"})
    line.refresh_from_db(); q.refresh_from_db()
    assert line.tax["sales"] == pytest.approx(2.00)
    assert q.totals["tax"] == pytest.approx(2.00)


@pytest.mark.django_db
def test_a_cash_discount_line_reduces_the_invoice_whatever_its_sign():
    """Bite 2 #1: cash_pending stores the discount unit negative; it must still reduce."""
    from apps.transactions.models import Invoice, InvoiceLine
    inv = Invoice.objects.create(finance={"sales_tax_rate": 0.05})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": 20.0, "precision": 2}, cost={"unit": 0})
    InvoiceLine.objects.create(invoice=inv, line_type='discount', purpose='cash_discount',
                               quantity={"active": 1}, price={"unit": -2.0}, cost={})
    inv.refresh_from_db()
    assert inv.totals["subtotal"] == pytest.approx(18.00)
    assert inv.totals["tax"] == pytest.approx(1.00)            # tax stays on the sale
    assert inv.totals["total"] == pytest.approx(19.00)
