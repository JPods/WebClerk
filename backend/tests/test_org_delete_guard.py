"""A customer or vendor with business still open cannot be deleted (Bill, 2026-10-25):
unapplied payments, uncollected invoices and open orders; purchases, receipts and payments
on the vendor side. Users clean these up first."""
from __future__ import annotations

import pytest
from django.utils.crypto import get_random_string

from apps.core.services.delete import delete_record
from apps.core.services.door import Actor, Refused
from apps.orgs.models import Customer, Vendor
from apps.transactions.models import Cash, Invoice, Order, OrderLine, Purchase, PurchaseLine


@pytest.fixture
def actor(django_user_model):
    return Actor(user=django_user_model.objects.create_superuser(
        email='guard@example.com', password=get_random_string(20), name_first='G', name_last='U'))


def _refusal(actor, model_key, org):
    with pytest.raises(Refused) as caught:
        delete_record(actor, model_key, org.pk)
    assert caught.value.code == 'delete_refused'
    return caught.value.message


@pytest.mark.django_db
def test_a_customer_with_an_open_order_is_refused_and_told_what_to_clean_up(actor):
    c = Customer.objects.create(company='Open Orders Co')
    o = Order.objects.create(customer=c)
    OrderLine.objects.create(order=o, quantity={'active': 3, 'remaining': 3})
    message = _refusal(actor, 'customer', c)
    assert '1 open orders' in message and (o.ida or f'#{o.pk}') in message
    assert Customer.objects.filter(pk=c.pk).exists()


@pytest.mark.django_db
def test_a_cancelled_or_filled_order_does_not_hold_the_customer(actor):
    c = Customer.objects.create(company='Closed Co')
    cancelled = Order.objects.create(customer=c, status='cancelled')
    OrderLine.objects.create(order=cancelled, quantity={'active': 3, 'remaining': 3})
    filled = Order.objects.create(customer=c)
    OrderLine.objects.create(order=filled, quantity={'active': 3, 'remaining': 0})
    Order.objects.filter(pk__in=[cancelled.pk, filled.pk]).delete()   # documents go first
    assert delete_record(actor, 'customer', c.pk).deleted


@pytest.mark.django_db
def test_an_uncollected_invoice_holds_the_customer(actor):
    c = Customer.objects.create(company='Owes Co')
    Invoice.objects.create(customer=c, totals={'total': 50, 'balance': 50})
    assert 'uncollected invoices' in _refusal(actor, 'customer', c)


@pytest.mark.django_db
def test_an_unapplied_payment_holds_the_customer(actor):
    c = Customer.objects.create(company='Paid Ahead Co')
    Cash.objects.create(customer=c, amount=25, available=25)
    assert 'unapplied customer payments' in _refusal(actor, 'customer', c)


@pytest.mark.django_db
def test_a_vendor_with_an_open_purchase_or_unapplied_payment_is_refused(actor):
    v = Vendor.objects.create(company='Supplier Co')
    p = Purchase.objects.create(vendor=v)
    PurchaseLine.objects.create(purchase=p, quantity={'active': 5, 'remaining': 5})
    Cash.objects.create(vendor=v, amount=-40, available=-40)
    message = _refusal(actor, 'vendor', v)
    assert 'open purchases' in message and 'unapplied vendor payments' in message


@pytest.mark.django_db
def test_a_queryset_delete_is_stopped_too(actor):
    c = Customer.objects.create(company='Bulk Co')
    Cash.objects.create(customer=c, amount=10, available=10)
    with pytest.raises(ValueError):
        Customer.objects.filter(pk=c.pk).delete()


@pytest.mark.django_db
def test_an_org_with_nothing_open_deletes(actor):
    c = Customer.objects.create(company='Clean Co')
    assert delete_record(actor, 'customer', c.pk).deleted

