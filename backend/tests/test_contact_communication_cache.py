"""The contact's communication cache follows whichever side changed (Bill, 2026-10-16).

Phone, Address, Domain and Email are edited only in their own records. The contact
keeps pointers (phone_id, …) and a cache in refs.links, rebuilt when the contact saves
and when a communication record saves or is deleted (apps/communications/signals.py).
"""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.communications.models import Address, Phone
from apps.core.models import Contact

pytestmark = pytest.mark.django_db


def _contact(**kw):
    return Contact.objects.create(email=kw.pop('email', 'susy@example.com'),
                                  name_first='Susy', name_last='Que', **kw)


def _fresh(c):
    return Contact.objects.get(pk=c.pk)


def test_editing_a_phone_in_its_card_refreshes_the_contact():
    c = _contact()
    phone = Phone.objects.create(contact=c, number='555-0100')
    c = _fresh(c)
    assert c.phone_id == phone.id                       # first record becomes primary
    assert c.phone == '555-0100'
    phone.number = '555-0199'
    phone.save()
    c = _fresh(c)
    assert [p['number'] for p in c.refs['links']['phone']] == ['555-0199']
    assert c.phone == '555-0199'


def test_deleting_the_primary_moves_the_pointer_or_clears_it():
    c = _contact()
    first = Phone.objects.create(contact=c, number='555-0100')
    second = Phone.objects.create(contact=c, number='555-0200')
    assert _fresh(c).phone_id == first.id
    first.delete()
    c = _fresh(c)
    assert c.phone_id == second.id
    assert c.phone == '555-0200'
    second.delete()
    c = _fresh(c)
    assert c.phone_id is None
    assert c.phone == ''
    assert 'phone' not in c.refs['links']


def test_moving_a_record_refreshes_both_contacts():
    a = _contact(email='a@example.com')
    b = _contact(email='b@example.com')
    addr = Address.objects.create(contact=a, address1='1 Main St', full='1 Main St')
    assert _fresh(a).address_full == '1 Main St'
    addr.contact = b
    addr.save()
    assert _fresh(a).address_full == ''
    assert _fresh(b).address_full == '1 Main St'


def test_the_primary_value_reads_without_a_query():
    c = _contact()
    Phone.objects.create(contact=c, number='555-0100')
    Address.objects.create(contact=c, address1='1 Main St', full='1 Main St')
    c = _fresh(c)
    with CaptureQueriesContext(connection) as ctx:
        assert c.phone == '555-0100'
        assert c.address_full == '1 Main St'
    assert len(ctx.captured_queries) == 0


def test_login_email_flows_one_way_into_its_email_record():
    c = _contact()
    c = _fresh(c)
    assert c.email_id
    assert [e['email'] for e in c.refs['links']['email']] == ['susy@example.com']
