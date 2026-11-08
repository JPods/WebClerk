"""Two org ↔ contact rulings (Bill, 2026-11-08): "Creating a company is good but it should transfer
the source_name from the contact if one is assigned. On saving the Customer, the Company name in
the contact should update to the Customer saved value."

1. An org given a contact — at birth (_from_contact) or by a later contact_id — takes the contact's
   source_name when its own is blank; a source_name in the same payload wins (the blanks-only rule
   defaults follow). Every org, since source_name is on OrgBase.
2. A save that changes an org's company renames the contacts whose primary affiliation is that org
   (customer > vendor > manufacturer > rep, the order Contact.save uses) and its primary contact,
   versioned as an edit; a contact another person holds is left for them and named in the messages;
   a save that does not change the name writes no contact.
"""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact
from apps.core.services import edit_hold
from apps.orgs.models import OrgBase

pytestmark = pytest.mark.django_db


def _client(email='staff@example.com'):
    staff = Contact.objects.create_superuser(email=email, password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    return client, staff


def _contact(name, **fields):
    return Contact.objects.create(email=f'{name.lower()}@example.com', name_first=name,
                                  name_last='Que', **fields)


def _post(client, model, body):
    r = client.post(f'/wcapi/{model}/', body, format='json', HTTP_HOST='localhost')
    assert r.status_code in (200, 201), r.json()
    data = r.json()['data']
    return OrgBase.objects.get(pk=data.get('id') or data['record']['id'])


def _put(client, model, org, body):
    r = client.put(f'/wcapi/{model}/{org.id}/', body, format='json', HTTP_HOST='localhost')
    assert r.status_code == 200, r.json()
    return r.json()


def _customer_with(client, first, *others, **org_fields):
    org = _post(client, 'customer', {'_from_contact': first.id})
    for c in others:
        c.customer_id = org.id
        c.save()
    if org_fields:
        OrgBase.objects.filter(pk=org.pk).update(**org_fields)
        org.refresh_from_db()
    return org


# ── 1. source_name from the contact ──────────────────────────────────────────────────────────

def test_an_org_born_from_a_contact_takes_its_source_name():
    client, _ = _client()
    susy = _contact('Susy', source_name='referral')
    org = _post(client, 'vendor', {'_from_contact': susy.id, '_company': 'Que Supply'})
    assert org.source_name == 'referral'


def test_a_source_name_in_the_payload_wins():
    client, _ = _client()
    susy, tom = _contact('Susy', source_name='referral'), _contact('Tom', source_name='trade_show')
    org = _customer_with(client, susy, tom)
    OrgBase.objects.filter(pk=org.pk).update(source_name='')
    _put(client, 'customer', org, {'contact_id': tom.id, 'source_name': 'website'})
    org.refresh_from_db()
    assert org.contact_id == tom.id and org.source_name == 'website'


def test_an_org_with_a_source_name_keeps_it_when_given_a_contact():
    client, _ = _client()
    susy, tom = _contact('Susy', source_name='referral'), _contact('Tom', source_name='trade_show')
    org = _customer_with(client, susy, tom)
    assert org.source_name == 'referral'                    # born with Susy's
    _put(client, 'customer', org, {'contact_id': tom.id})
    org.refresh_from_db()
    assert org.contact_id == tom.id and org.source_name == 'referral'


def test_a_later_contact_fills_a_blank_source_name():
    client, _ = _client()
    susy, tom = _contact('Susy'), _contact('Tom', source_name='trade_show')
    org = _customer_with(client, susy, tom)
    assert org.source_name == ''                            # Susy had none
    _put(client, 'customer', org, {'contact_id': tom.id})
    org.refresh_from_db()
    assert org.source_name == 'trade_show'


# ── 2. renaming the org renames its contacts ─────────────────────────────────────────────────

def test_a_rename_updates_the_contacts_whose_primary_affiliation_is_the_org():
    client, _ = _client()
    susy, tom = _contact('Susy'), _contact('Tom')
    org = _customer_with(client, susy, tom)
    other = _customer_with(client, _contact('Ann'))
    elsewhere = _contact('Eve', customer_id=other.id)
    before = {c.pk: (c.version, c.dt_modified) for c in Contact.objects.filter(pk__in=[susy.pk, tom.pk, elsewhere.pk])}
    body = _put(client, 'customer', org, {'company': 'Que Industries'})
    susy.refresh_from_db(); tom.refresh_from_db(); elsewhere.refresh_from_db()
    assert susy.company == tom.company == 'Que Industries'
    assert elsewhere.company == other.company
    for c in (susy, tom):
        assert c.version == before[c.pk][0] + 1 and c.dt_modified > before[c.pk][1]
    assert (elsewhere.version, elsewhere.dt_modified) == before[elsewhere.pk]
    assert any('2 contacts renamed to Que Industries' in str(m) for m in _messages(body)), body


def test_a_contact_that_belongs_first_to_a_customer_keeps_that_name_when_its_vendor_is_renamed():
    client, _ = _client()
    customer = _customer_with(client, _contact('Ann'))
    vendor = _post(client, 'vendor', {'_company': 'Que Supply'})
    both = _contact('Eve', customer_id=customer.id, vendor_id=vendor.id)
    assert both.company == customer.company                 # Contact.save: customer first
    _put(client, 'vendor', vendor, {'company': 'Que Supply Ltd'})
    both.refresh_from_db()
    assert both.company == customer.company


def test_a_save_that_does_not_change_the_name_writes_no_contact():
    client, _ = _client()
    susy, tom = _contact('Susy'), _contact('Tom')
    org = _customer_with(client, susy, tom)
    before = {c.pk: (c.version, c.dt_modified) for c in Contact.objects.filter(pk__in=[susy.pk, tom.pk])}
    _put(client, 'customer', org, {'source_name': 'website'})
    assert {c.pk: (c.version, c.dt_modified) for c in Contact.objects.filter(pk__in=[susy.pk, tom.pk])} == before


def test_a_contact_another_person_holds_is_left_for_them_and_named():
    client, _ = _client()
    _other_client, other = _client('other@example.com')
    susy, tom = _contact('Susy'), _contact('Tom')
    org = _customer_with(client, susy, tom)

    class _Actor:
        user = other
        user_id = other.pk
    edit_hold.take(_Actor(), 'contact', tom.pk)
    body = _put(client, 'customer', org, {'company': 'Que Industries'})
    susy.refresh_from_db(); tom.refresh_from_db()
    assert susy.company == 'Que Industries' and tom.company != 'Que Industries'
    assert any(f'contact #{tom.pk} is being edited by' in str(m) for m in _messages(body)), body


def _messages(body):
    return body.get('messages') or (body.get('data') or {}).get('messages') or []
