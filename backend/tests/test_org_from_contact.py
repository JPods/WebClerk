"""A customer (or vendor, …) made from a contact whose search found nothing (Bill, 2026-10-16).

`POST /wcapi/customer/ {"_from_contact": id, "_company": typed}` saves the org populated:
the company is what staff typed, else the contact's attention (an individual); the org
points at the contact's own email/phone/address records and takes the contact as primary;
the contact is linked to the org. Duplicates are the users' to clean up.
"""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.communications.models import Address, Phone
from apps.core.models import Contact
from apps.orgs.models import OrgBase

pytestmark = pytest.mark.django_db


def _staff_client():
    staff = Contact.objects.create_superuser(email='staff@example.com',
                                             password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    return client


def _susy():
    c = Contact.objects.create(email='susy@example.com', name_first='Susy', name_last='Que')
    Phone.objects.create(contact=c, number='9185551212')
    Address.objects.create(contact=c, address1='3941 60th PL', city='Tulsa', state='OK', zip='74135')
    return Contact.objects.get(pk=c.pk)


def _new(client, model, body):
    r = client.post(f'/wcapi/{model}/', body, format='json', HTTP_HOST='localhost')
    assert r.status_code in (200, 201), r.json()
    data = r.json()['data']
    return OrgBase.objects.get(pk=data.get('id') or data['record']['id'])


def _served(client, model, org):
    data = client.get(f'/wcapi/{model}/{org.id}/', HTTP_HOST='localhost').json()['data']
    return data.get('record') or data


def test_an_individual_customer_from_a_contact():
    client, susy = _staff_client(), _susy()
    org = _new(client, 'customer', {'_from_contact': susy.id})
    assert org.company == 'Susy Que' and org.attention == 'Susy Que'
    assert org.contact_id == susy.id and org.email == 'susy@example.com'
    assert (org.email_id, org.phone_id, org.address_id) == (susy.email_id, susy.phone_id, susy.address_id)
    assert not (org.config or {}).get('is_new')              # populated, not for the sweep
    susy = Contact.objects.get(pk=susy.pk)
    assert susy.customer_id == org.id
    org.refresh_from_db()
    assert [c['id'] for c in _served(client, 'customer', org)['refs']['links']['contact']] \
        == [susy.id]                                                        # CONTACTS panel
    assert org.display_name == 'Susy Que' and org.address_full.startswith('3941 60th PL')


def test_what_staff_typed_is_the_company():
    client, susy = _staff_client(), _susy()
    org = _new(client, 'vendor', {'_from_contact': susy.id, '_company': 'Que Supply'})
    assert org.company == 'Que Supply' and org.attention == 'Susy Que'
    assert Contact.objects.get(pk=susy.pk).vendor_id == org.id


def test_a_contact_the_actor_cannot_see_is_refused():
    client = _staff_client()
    r = client.post('/wcapi/customer/', {'_from_contact': 99999999}, format='json',
                    HTTP_HOST='localhost')
    assert r.status_code == 404 and r.json()['error']['code'] == 'from_contact_not_found'


def test_a_reference_saves_back_in_the_shape_it_was_served():
    """The contact page holds a picked customer as {id, ida, name}, as the GET serves it,
    so the field shows locked; the save links it by its id (Bill, 2026-10-17)."""
    client, susy = _staff_client(), _susy()
    org = _new(client, 'customer', {'_company': 'Que Supply'})
    picked = {'id': org.id, 'ida': org.ida, 'name': org.company}
    r = client.put(f'/wcapi/contact/{susy.id}/', {'customer': picked}, format='json',
                   HTTP_HOST='localhost')
    assert r.status_code == 200, r.json()
    assert Contact.objects.get(pk=susy.pk).customer_id == org.id
    served = client.get(f'/wcapi/contact/{susy.id}/', HTTP_HOST='localhost').json()['data']
    assert (served.get('record') or served)['customer']['id'] == org.id


def test_an_orgs_contacts_are_served_from_the_contacts_links_not_a_stored_copy():
    """Que Supply listed no contacts: a later save wiped the stored copy while Suzy's
    customer_id still pointed at it. The FK is the one source (Bill, 2026-10-17)."""
    client, susy = _staff_client(), _susy()
    org = _new(client, 'customer', {'_company': 'Que Supply'})
    Contact.objects.filter(pk=susy.pk).update(customer_id=org.id)
    OrgBase.objects.filter(pk=org.pk).update(refs={'links': {'contact': [{'id': 10 ** 9}]}})
    assert [c['id'] for c in _served(client, 'customer', org)['refs']['links']['contact']] == [susy.id]


def test_the_contacts_panel_links_by_editing_the_contact():
    """The CONTACTS panel's add and remove write the contact's own customer field."""
    client, susy = _staff_client(), _susy()
    org = _new(client, 'customer', {'_company': 'Que Supply'})
    put = lambda value: client.put(f'/wcapi/contact/{susy.id}/', {'customer': value},
                                   format='json', HTTP_HOST='localhost')
    assert put(org.id).status_code == 200
    assert [c['id'] for c in _served(client, 'customer', org)['refs']['links']['contact']] == [susy.id]
    assert put({'mode': 'delete'}).status_code == 200            # the door's clear
    assert _served(client, 'customer', org)['refs']['links']['contact'] == []
