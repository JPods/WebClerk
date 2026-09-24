"""Customer, rep and vendor ids on line records (Bill, 2026-09-23).

"If we did users could more easily search and report on customers by item and item by
customer. It is relatively cheap to add them." Values, not foreign keys ("Yes, not FK").
Stamped from the header on every line save — never entered — and cascaded when the header
changes. A line's rep is the rep who made the sale: a customer's later rep change does not
rewrite a document.
"""
import pytest

from apps.orgs.models import OrgBase
from apps.transactions.models import (Invoice, InvoiceLine, Order, OrderLine, Purchase,
                                      PurchaseLine, Quote, QuoteLine)

pytestmark = pytest.mark.django_db

LINE = dict(status='OPEN', item={"id_num": 1}, quantity={"active": 1}, price={"amount": 1})


def _orgs():
    rep = OrgBase.objects.create(company='Rep Co', org_type='rep')
    acme = OrgBase.objects.create(company='Acme', org_type='customer', rep_id=rep.pk)
    globex = OrgBase.objects.create(company='Globex', org_type='customer')
    vendor = OrgBase.objects.create(company='Parts Inc', org_type='vendor')
    return rep, acme, globex, vendor


def disagreements() -> list:
    """Every line whose party ids differ from its header's — the guard."""
    bad = []
    for Header, Line, fk, fields in ((Quote, QuoteLine, 'quote', ('customer_id', 'rep_id')),
                                     (Order, OrderLine, 'order', ('customer_id', 'rep_id')),
                                     (Invoice, InvoiceLine, 'invoice', ('customer_id', 'rep_id')),
                                     (Purchase, PurchaseLine, 'purchase', ('vendor_id',))):
        for line in Line.objects.select_related(fk):
            header = getattr(line, fk)
            for field in fields:
                if getattr(line, field) != getattr(header, field):
                    bad.append((Line.__name__, line.pk, field))
    return bad


@pytest.mark.parametrize('Header, Line, fk', [(Quote, QuoteLine, 'quote'),
                                              (Order, OrderLine, 'order'),
                                              (Invoice, InvoiceLine, 'invoice')])
def test_a_sell_line_carries_its_headers_customer_and_rep(Header, Line, fk):
    rep, acme, _globex, _vendor = _orgs()
    header = Header.objects.create(customer_id=acme.pk, rep_id=rep.pk)
    line = Line.objects.create(**{fk: header}, **LINE)
    assert (line.customer_id, line.rep_id) == (acme.pk, rep.pk)


def test_a_value_sent_for_the_line_is_replaced_by_the_headers():
    rep, acme, globex, _vendor = _orgs()
    order = Order.objects.create(customer_id=acme.pk, rep_id=rep.pk)
    line = OrderLine(order=order, customer_id=globex.pk, rep_id=999, **LINE)
    line.save()
    line.refresh_from_db()
    assert (line.customer_id, line.rep_id) == (acme.pk, rep.pk)


def test_a_header_change_cascades_to_its_lines():
    rep, acme, globex, _vendor = _orgs()
    order = Order.objects.create(customer_id=acme.pk, rep_id=rep.pk)
    lines = [OrderLine.objects.create(order=order, **LINE) for _ in range(3)]
    order.customer_id = globex.pk
    order.save()
    assert set(OrderLine.objects.filter(pk__in=[l.pk for l in lines])
               .values_list('customer_id', flat=True)) == {globex.pk}
    assert disagreements() == []


def test_a_purchase_line_carries_its_vendor():
    _rep, _acme, _globex, vendor = _orgs()
    purchase = Purchase.objects.create(vendor_id=vendor.pk)
    line = PurchaseLine.objects.create(purchase=purchase, status='OPEN', item={"id_num": 1},
                                       quantity={"active": 1})
    assert line.vendor_id == vendor.pk


def test_a_customers_new_rep_does_not_rewrite_a_sale():
    """The line's rep is the seller's, kept with the sale."""
    rep, acme, _globex, _vendor = _orgs()
    invoice = Invoice.objects.create(customer_id=acme.pk, rep_id=rep.pk)
    line = InvoiceLine.objects.create(invoice=invoice, **LINE)
    new_rep = OrgBase.objects.create(company='New Rep', org_type='rep')
    acme.rep_id = new_rep.pk
    acme.save()
    line.refresh_from_db()
    assert line.rep_id == rep.pk


def test_customers_by_item_is_one_query():
    rep, acme, globex, _vendor = _orgs()
    for customer in (acme, globex):
        quote = Quote.objects.create(customer_id=customer.pk, rep_id=rep.pk)
        QuoteLine.objects.create(quote=quote, **LINE)
    assert set(QuoteLine.objects.filter(item__id_num=1)
               .values_list('customer_id', flat=True)) == {acme.pk, globex.pk}
