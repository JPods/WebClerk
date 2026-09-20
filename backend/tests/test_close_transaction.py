"""close_transaction — the one door a commitment leaves through (Bill, 2026-09-19)."""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db


def _order_with_a_commitment(qty=5, remaining=None):
    from apps.orgs.models import Customer
    from apps.products.models import Item
    from apps.transactions.models import Order, OrderLine
    customer = Customer.objects.create(company='C')
    # on_so starts empty: creating the line is what commits it, the same way a user's
    # line entry does. Seeding it too would double the commitment.
    item = Item.objects.create(name='Widget', quantity={'on_hand': 100, 'on_so': 0, 'allocated': 0})
    order = Order.objects.create(customer_id=customer.pk)
    line = OrderLine.objects.create(
        order=order, item={'item_id': item.pk, 'description': 'Widget'},
        quantity={'active': qty}, price={'unit': 10.00, 'precision': 2},
    )
    item.refresh_from_db()
    return order, line, item


def test_closing_releases_what_the_document_still_commits():
    from apps.transactions.services.close_transaction import close_transaction
    order, line, item = _order_with_a_commitment(qty=5)

    assert float((item.quantity or {}).get('on_so')) == float(5)   # the line committed it

    out = close_transaction('order', order.pk, reason='abandoned', acted_by='tester')

    item.refresh_from_db()
    order.refresh_from_db()
    line.refresh_from_db()
    assert out['released'] == {'on_so': -5.0}
    assert float((item.quantity or {}).get('on_so')) == 0.0      # the commitment came back
    assert order.status == 'complete'
    assert order.metadata['closed']['by'] == 'tester'
    assert order.metadata['closed']['reason'] == 'abandoned'
    # is_complete makes remaining 0, so the line can never release twice
    assert float((line.quantity or {}).get('remaining')) == 0.0


def test_closing_twice_releases_once():
    from apps.transactions.services.close_transaction import close_transaction
    order, _line, item = _order_with_a_commitment(qty=4)

    close_transaction('order', order.pk, reason='first', acted_by='tester')
    again = close_transaction('order', order.pk, reason='second', acted_by='tester')

    item.refresh_from_db()
    assert again['already_closed'] is True
    assert again['lines'] == 0
    assert float((item.quantity or {}).get('on_so')) == 0.0      # not -4


def test_a_close_records_who_and_why():
    from apps.transactions.services.close_transaction import close_transaction
    order, _line, _item = _order_with_a_commitment()
    with pytest.raises(ValidationError):
        close_transaction('order', order.pk, reason='', acted_by='tester')
    with pytest.raises(ValidationError):
        close_transaction('order', order.pk, reason='why', acted_by='')


def test_an_invoice_holds_no_commitment_to_release():
    from apps.orgs.models import Customer
    from apps.transactions.models import Invoice, InvoiceLine
    from apps.transactions.services.close_transaction import close_transaction
    customer = Customer.objects.create(company='C')
    invoice = Invoice.objects.create(customer_id=customer.pk)
    InvoiceLine.objects.create(invoice=invoice, item={'item_id': 1}, quantity={'active': 3},
                               price={'unit': 5.00, 'precision': 2})

    out = close_transaction('invoice', invoice.pk, reason='done', acted_by='tester')

    assert out['released'] == {}          # an invoice records a movement that happened
    assert out['status'] == 'complete'


def test_stale_commitments_lists_what_is_still_held():
    from apps.transactions.services.close_transaction import stale_commitments
    order, _line, _item = _order_with_a_commitment(qty=7)

    rows = [r for r in stale_commitments(days=0) if r['id'] == order.pk and r['model'] == 'order']

    assert rows and rows[0]['holding'] == 7.0
    assert rows[0]['bucket'] == 'on_so'
