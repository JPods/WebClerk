"""An org's name and email are its primary contact's (Bill, 2026-10-31): a de-normalized value
is never edited where it is copied, only on the record it comes from.

The org follows its contact when the contact changes; a typed attention or email on an org
with a primary contact is refused with where to change it; choosing another primary contact
— one of the org's own — takes that contact's values. An org with no contact keeps its own.
"""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact
from apps.orgs.models import OrgBase

pytestmark = pytest.mark.django_db


def _client():
    staff = Contact.objects.create_superuser(email='staff@example.com',
                                             password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    return client


def _customer_with(client, *names):
    """A customer made from the first contact; the others linked to it too."""
    first, *others = [Contact.objects.create(email=f'{n.lower()}@example.com', name_first=n,
                                             name_last='Que') for n in names]
    r = client.post('/wcapi/customer/', {'_from_contact': first.id}, format='json', HTTP_HOST='localhost')
    assert r.status_code in (200, 201), r.json()
    data = r.json()['data']
    org = OrgBase.objects.get(pk=data.get('id') or data['record']['id'])
    for c in others:
        c.customer_id = org.id
        c.save()
    return org, first, others


def _put(client, org, body):
    return client.put(f'/wcapi/customer/{org.id}/', body, format='json', HTTP_HOST='localhost')


def test_the_org_follows_its_contact():
    client = _client()
    org, susy, _ = _customer_with(client, 'Susy')
    susy.name_first = 'Suzanne'
    susy.save()
    org.refresh_from_db()
    assert org.attention == 'Suzanne Que'


def test_a_copied_value_is_refused_with_where_to_change_it():
    client = _client()
    org, susy, _ = _customer_with(client, 'Susy')
    r = _put(client, org, {'attention': 'Somebody Else'})
    assert r.status_code == 400
    body = r.json()
    assert body['error']['code'] == 'copied_value' and f'contact #{susy.id}' in body['message']
    org.refresh_from_db()
    assert org.attention == 'Susy Que'


def test_choosing_another_of_its_contacts_takes_its_values():
    client = _client()
    org, _, [bo] = _customer_with(client, 'Susy', 'Bo')
    r = _put(client, org, {'contact_id': bo.id})
    assert r.status_code == 200, r.json()
    org.refresh_from_db()
    bo.refresh_from_db()
    assert (org.contact_id, org.attention, org.email, org.email_id) == (bo.id, 'Bo Que', bo.email, bo.email_id)


def test_a_contact_not_its_own_is_refused():
    client = _client()
    org, _, _ = _customer_with(client, 'Susy')
    stranger = Contact.objects.create(email='stranger@example.com', name_first='Stranger')
    r = _put(client, org, {'contact_id': stranger.id})
    assert r.status_code == 400 and r.json()['error']['code'] == 'not_this_orgs_contact'


def test_an_org_without_a_contact_keeps_its_own_attention():
    client = _client()
    org = OrgBase.objects.create(org_type='customer', company='zz No Contact Co')
    r = _put(client, org, {'attention': 'Front Desk'})
    assert r.status_code == 200, r.json()
    org.refresh_from_db()
    assert org.attention == 'Front Desk'
