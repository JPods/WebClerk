"""Alice's weekly housekeeping — she raises these and asks (Bill, 2026-09-19)."""
import time

import pytest

pytestmark = pytest.mark.django_db

DAY = 86_400_000


def _customer():
    from apps.orgs.models import Customer
    return Customer.objects.create(company='C')


def test_a_document_with_no_lines_is_a_draft_to_finish():
    from apps.transactions.models import Order
    from apps.transactions.services.housekeeping import line_less_documents
    now = int(time.time() * 1000)
    order = Order.objects.create(customer_id=_customer().pk)
    Order.objects.filter(pk=order.pk).update(dt_created=now - 10 * DAY)   # older than draft_days

    out = line_less_documents(now_ms=now)

    rows = [r for r in out['complete'] if r['id'] == order.pk]
    assert rows and rows[0]['model'] == 'order'
    assert rows[0]['age_days'] == 10
    assert not any(r['id'] == order.pk for r in out['delete'])


def test_an_old_line_less_document_is_offered_for_deletion():
    from apps.transactions.models import Receipt
    from apps.transactions.services.housekeeping import line_less_documents
    now = int(time.time() * 1000)
    receipt = Receipt.objects.create()
    Receipt.objects.filter(pk=receipt.pk).update(dt_created=now - 120 * DAY)

    out = line_less_documents(now_ms=now)

    assert any(r['id'] == receipt.pk and r['model'] == 'receipt' for r in out['delete'])


def test_a_document_with_lines_is_not_on_the_list():
    from apps.transactions.models import Order, OrderLine
    from apps.transactions.services.housekeeping import line_less_documents
    now = int(time.time() * 1000)
    order = Order.objects.create(customer_id=_customer().pk)
    OrderLine.objects.create(order=order, item={'item_id': 1}, quantity={'active': 1},
                             price={'unit': 1.00, 'precision': 2})
    Order.objects.filter(pk=order.pk).update(dt_created=now - 30 * DAY)

    out = line_less_documents(now_ms=now)

    assert not any(r['id'] == order.pk for r in out['complete'] + out['delete'])


def test_a_credit_balance_is_proposed_as_unapplied_cash_not_posted():
    from apps.transactions.models import Invoice
    from apps.transactions.services.housekeeping import negative_invoices_to_convert
    now = int(time.time() * 1000)
    invoice = Invoice.objects.create(customer_id=_customer().pk)
    Invoice.objects.filter(pk=invoice.pk).update(
        dt_created=now - 5 * DAY, totals={'total': -40.0, 'balance': -40.0})

    rows = negative_invoices_to_convert(now_ms=now)

    row = next(r for r in rows if r['invoice_id'] == invoice.pk)
    assert row['credit'] == 40.0
    assert row['proposal']['create'] == 'cash'        # proposed
    invoice.refresh_from_db()
    assert invoice.totals['balance'] == -40.0         # and nothing was posted
