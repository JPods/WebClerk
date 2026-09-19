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
    _assert_document_is_sum_of_lines(q)
    assert q.totals["amount"] == pytest.approx(216.13)
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
    # the discount line became allocations on the quote; it carries as a percent, not a line
    assert [l["line_type"] for l in result["lines"]] == ["product"]
    assert order.allocations["discount_percent"] == pytest.approx(10.0)   # $10 of $100


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
    assert first.totals["amount"] + second.totals["amount"] == pytest.approx(45.00)


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
        assert float(t["amount"]) == pytest.approx(90.00)
        assert float(t["tax"]) == pytest.approx(4.50)   # tax on the discounted price
        assert float(t["total"]) == pytest.approx(94.50)


KEYS = ('amount', 'discount', 'taxable', 'tax', 'shipping', 'other', 'finance_charge', 'cost', 'margin', 'total')


def _assert_document_is_sum_of_lines(header):
    """Bill 2026-09-19: every document number is the sum of the same number on its lines."""
    header.refresh_from_db()
    lines = list(header.lines.all())
    for k in KEYS:
        assert header.totals[k] == pytest.approx(sum(l.totals.get(k, 0) for l in lines), abs=0.001), k


@pytest.mark.django_db
def test_tax_is_applied_to_the_discounted_price():
    """A document discount (a discount line) goes into allocations and is spread over the
    lines as a per-unit reduction; each line is taxed on its own discounted amount."""
    q = Quote.objects.create(finance={"sales_tax_rate": 0.05})
    a = _line(q, 15, 10.00)                                              # 150.00
    b = _line(q, 3, 19.99, discount_percent=12.5)                        # 17.49 × 3 = 52.47
    c = _line(q, 2, 7.33, discount_amount=1.00, tax_code='NONTAXABLE')   # 6.83 × 2 = 13.66
    d = _line(q, 1, 10.00, line_type='discount')                         # $10 off the document
    q.refresh_from_db()
    assert q.allocations["discount_amount"] == 10.0
    for l in (a, b, c, d):
        l.refresh_from_db()
    assert d.totals["amount"] == 0 and d.metadata["document_discount"]["applied"] == 10.0
    # shares 6.94 / 2.43 / 0.63 → discounted units 9.54 / 16.68 / 6.52 (rounding difference accepted)
    assert [a.totals["discounted_unit"], b.totals["discounted_unit"], c.totals["discounted_unit"]] == \
        [pytest.approx(9.54), pytest.approx(16.68), pytest.approx(6.52)]
    assert [a.totals["amount"], b.totals["amount"], c.totals["amount"]] == \
        [pytest.approx(143.10), pytest.approx(50.04), pytest.approx(13.04)]
    assert a.totals["tax"] == pytest.approx(7.16) and b.totals["tax"] == pytest.approx(2.50)
    assert c.totals["tax"] == 0 and c.totals["rate_source"] == "item_exempt"
    assert q.totals["amount"] == pytest.approx(206.18)
    assert q.totals["discount"] == pytest.approx(224.63 - 206.18)   # gross 150 + 59.97 + 14.66 − amount
    assert q.totals["tax"] == pytest.approx(9.66)
    assert q.totals["total"] == pytest.approx(215.84)
    _assert_document_is_sum_of_lines(q)


@pytest.mark.django_db
def test_a_document_percent_discount_follows_lines_added_later():
    """Bill: a 10% discount applied later is distributed over the lines in proportion."""
    from apps.transactions.services.pricing.document_discount import apply_document_discount
    q = Quote.objects.create(finance={"sales_tax_rate": 0.10})
    _line(q, 2, 10.00)
    apply_document_discount(q, percent=10)
    q.refresh_from_db()
    assert q.totals["amount"] == pytest.approx(18.00)
    _line(q, 1, 5.00)                                  # added after the discount
    q.refresh_from_db()
    assert q.totals["amount"] == pytest.approx(22.50)  # 18.00 + 4.50
    assert q.totals["tax"] == pytest.approx(2.25)
    _assert_document_is_sum_of_lines(q)


@pytest.mark.django_db
def test_document_shipping_and_other_are_spread_exactly():
    """Total = amount + line taxes + shipping + finance charge + other; each is Σ lines."""
    q = Quote.objects.create(finance={"sales_tax_rate": 0.10},
                             allocations={"shipping": 10.00, "other": 7.00})
    a = _line(q, 1, 10.00)
    b = _line(q, 2, 10.00)
    q.refresh_from_db(); a.refresh_from_db(); b.refresh_from_db()
    assert a.totals["shipping"] + b.totals["shipping"] == pytest.approx(10.00)
    assert a.totals["other"] + b.totals["other"] == pytest.approx(7.00)
    assert q.totals["total"] == pytest.approx(30 + 3 + 10 + 7)
    _assert_document_is_sum_of_lines(q)


@pytest.mark.django_db
def test_a_rate_typed_on_the_line_wins():
    q = Quote.objects.create(finance={"sales_tax_rate": 0.10})
    line = QuoteLine.objects.create(
        quote=q, quantity={"active": 1}, price={"unit": 100.0, "precision": 2},
        cost={"unit": 0}, tax={"sales_rate": 0.02, "rate_source": "line"})
    line.refresh_from_db(); q.refresh_from_db()
    assert line.totals["tax"] == pytest.approx(2.00)
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
    assert inv.totals["amount"] == pytest.approx(18.00)
    assert inv.totals["tax"] == pytest.approx(1.00)            # tax stays on the sale
    assert inv.totals["total"] == pytest.approx(19.00)
    _assert_document_is_sum_of_lines(inv)


@pytest.mark.django_db
def test_with_both_a_percent_and_a_dollar_discount_the_larger_applies():
    """Bill 2026-09-19: if discount_amount or % — use the larger."""
    q = Quote.objects.create()
    a = _line(q, 2, 50.00, discount_percent=10, discount_amount=15.00)   # 10% = 10.00 < 15.00
    b = _line(q, 2, 50.00, discount_percent=20, discount_amount=15.00)   # 20% = 20.00 > 15.00
    a.refresh_from_db(); b.refresh_from_db()
    assert a.totals["amount"] == pytest.approx(85.00)
    assert b.totals["amount"] == pytest.approx(80.00)
