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


def test_staff_enter_an_email_in_its_card_and_it_becomes_the_login():
    from apps.communications.models import Email
    c = Contact.objects.create(name_first='Never', name_last='Signedin')   # record-only
    assert _fresh(c).email is None
    rec = Email.objects.create(contact=c, email='never@example.com')
    c = _fresh(c)
    assert c.email_id == rec.id
    assert c.email == 'never@example.com'
    rec.email = 'changed@example.com'
    rec.save()
    assert _fresh(c).email == 'changed@example.com'


def test_a_second_email_does_not_change_the_login():
    from apps.communications.models import Email
    c = _fresh(_contact())
    Email.objects.create(contact=c, email='billing@example.com')
    assert _fresh(c).email == 'susy@example.com'


def test_an_email_another_contact_has_is_refused_naming_that_contact():
    from apps.communications.models import Email
    from apps.core.services.door import Refused
    owner = _contact(email='taken@example.com')
    Email.objects.create(contact=owner, email='shared@example.com')      # not the login
    c = Contact.objects.create(name_first='New', name_last='Person')
    for address in ('Taken@example.com', 'shared@example.com'):
        with pytest.raises(Refused) as refused:
            Email.objects.create(contact=c, email=address)
        assert refused.value.code == 'email_in_use'
        assert refused.value.details['contact_id'] == owner.id


def test_deleting_the_login_email_moves_the_login_to_the_next_one():
    from apps.communications.models import Email
    c = _fresh(_contact())
    second = Email.objects.create(contact=c, email='second@example.com')
    Email.objects.get(pk=c.email_id).delete()
    c = _fresh(c)
    assert c.email_id == second.id
    assert c.email == 'second@example.com'


def test_the_card_save_is_refused_over_http_with_the_owner_id():
    from rest_framework.test import APIClient
    from apps.communications.models import Email
    owner = _contact(email='taken@example.com')
    staff = Contact.objects.create(email='staff@example.com', is_superuser=True, is_staff=True)
    c = Contact.objects.create(name_first='New', name_last='Person')
    rec = Email.objects.create(contact=c, email='new@example.com')
    client = APIClient()
    client.force_authenticate(staff)
    r = client.put(f'/wcapi/email/{rec.id}/', {'email': 'taken@example.com'}, format='json',
                   HTTP_HOST='localhost')
    body = r.json()
    assert r.status_code == 409, body
    assert body['error']['code'] == 'email_in_use'
    assert body['error']['details']['contact_id'] == owner.id


def test_saving_a_communication_record_saves_its_contact():
    c = _fresh(_contact())
    version, modified = c.version, c.dt_modified
    phone = Phone.objects.create(contact=c, number='555-0100')
    c = _fresh(c)
    assert c.version > version and c.dt_modified >= modified
    version = c.version
    phone.number = '555-0199'
    phone.save()
    c = _fresh(c)
    assert c.version == version + 1                    # one save, not a cascade
    assert c.phone == '555-0199'


def test_changing_the_contact_email_through_the_contact_keeps_the_new_address():
    c = _fresh(_contact())
    c.email = 'renamed@example.com'
    c.save()
    c = _fresh(c)
    assert c.email == 'renamed@example.com'
    assert c.primary_communication('email')['email'] == 'renamed@example.com'


def test_no_response_carries_the_password_hash():
    """FAULT 20261017T023030: the contact GET served pbkdf2 hashes to the browser."""
    from rest_framework.test import APIClient
    import secrets
    staff = Contact.objects.create_superuser(email='staff@example.com',
                                             password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    detail = client.get(f'/wcapi/contact/{staff.id}/', HTTP_HOST='localhost').json()['data']
    record = detail.get('record', detail)
    assert 'password' not in record and record.get('last_login', 'missing') != 'missing'
    rows = client.get('/wcapi/contact/?limit=5', HTTP_HOST='localhost').json()['data']['results']
    assert rows and not any('password' in r for r in rows)
    saved = client.put(f'/wcapi/contact/{staff.id}/', {'title': 'Owner'}, format='json',
                       HTTP_HOST='localhost').json()['data']
    assert 'password' not in (saved.get('record') or {})
