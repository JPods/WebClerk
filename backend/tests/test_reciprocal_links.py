"""Two-sided links (Bill, 2026-10-31: "any and all models can be related to each other via
.refs.links"). A record listing another in refs.links.<model>[] is listed back in that record's
refs.links.<this model>[]. The save door writes both sides; deleting either side removes it
from the other. What is not a list of records under refs.links is left as it is.
"""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Action, Contact
from apps.orgs.models import OrgBase

pytestmark = pytest.mark.django_db


def _client():
    staff = Contact.objects.create_superuser(email='staff@example.com',
                                             password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    return client


def _ids(obj, key):
    obj.refresh_from_db()
    return sorted(int(r['id']) for r in ((obj.refs or {}).get('links') or {}).get(key) or [])


def _put(client, model, pk, body):
    r = client.put(f'/wcapi/{model}/{pk}/', body, format='json', HTTP_HOST='localhost')
    assert r.status_code == 200, r.json()


def test_a_record_listing_an_action_is_listed_back():
    client = _client()
    org = OrgBase.objects.create(org_type='customer', company='zz Links Co')
    call, visit = Action.objects.create(action={'en': 'zz call'}), Action.objects.create(action={'en': 'zz visit'})

    _put(client, 'customer', org.id, {'refs.links.action': [{'id': call.id}, {'id': visit.id}]})
    assert _ids(call, 'customer') == [org.id] and _ids(visit, 'customer') == [org.id]

    _put(client, 'customer', org.id, {'refs.links.action': [{'id': visit.id}]})
    assert _ids(call, 'customer') == [] and _ids(visit, 'customer') == [org.id]


def test_an_action_naming_records_is_listed_by_them():
    client = _client()
    org = OrgBase.objects.create(org_type='customer', company='zz Links Co')
    who = Contact.objects.create(email='zz-who@example.com', name_first='Who')
    call = Action.objects.create(action={'en': 'zz call'})
    version = OrgBase.objects.get(pk=org.pk).version

    _put(client, 'action', call.id, {'refs.links.customer': [{'id': org.id}], 'refs.links.contact': [{'id': who.id}]})
    assert _ids(org, 'action') == [call.id] and _ids(who, 'action') == [call.id]
    assert org.version > version                  # a form holding the old list reloads first


def test_deleting_an_action_takes_it_off_its_records():
    client = _client()
    org = OrgBase.objects.create(org_type='customer', company='zz Links Co')
    call = Action.objects.create(action={'en': 'zz call'})
    _put(client, 'customer', org.id, {'refs.links.action': [{'id': call.id}]})

    r = client.delete(f'/wcapi/action/{call.id}/', HTTP_HOST='localhost')
    assert r.status_code in (200, 204), r.content
    assert _ids(org, 'action') == []


def test_documents_are_two_sided_too():
    from apps.docs.models import Document
    client = _client()
    org = OrgBase.objects.create(org_type='customer', company='zz Links Co')
    doc = Document.objects.create(name='zz-links.txt', path={'key': 'uploads/zz-links.txt'})

    _put(client, 'customer', org.id, {'refs.links.document': [{'id': doc.id}]})
    assert _ids(doc, 'customer') == [org.id]


def test_any_two_models_are_linked_both_ways():
    client = _client()
    vendor = OrgBase.objects.create(org_type='vendor', company='zz Supplier')
    buyer = Contact.objects.create(email='zz-buyer@example.com', name_first='Buyer')
    _put(client, 'contact', buyer.id, {'refs.links.vendor': [{'id': vendor.id}]})
    assert _ids(vendor, 'contact') == [buyer.id]


def test_a_record_linked_to_another_of_its_kind_is_linked_back():
    client = _client()
    ann = Contact.objects.create(email='zz-ann@example.com', name_first='Ann')
    bob = Contact.objects.create(email='zz-bob@example.com', name_first='Bob')
    _put(client, 'contact', ann.id, {'refs.links.contact': [{'id': bob.id}]})
    assert _ids(bob, 'contact') == [ann.id] and _ids(ann, 'contact') == [bob.id]


def test_what_is_not_a_list_of_records_is_left_alone():
    client = _client()
    org = OrgBase.objects.create(org_type='customer', company='zz Links Co')
    call = Action.objects.create(action={'en': 'zz call'},
                                 refs={'links': {'customer': {'ida': 'snapshot'}, 'children': [{'id': 9}]}})
    _put(client, 'action', call.id, {'refs.links.customer': {'ida': 'snapshot', 'name': 'x'}})
    org.refresh_from_db()
    assert _ids(org, 'action') == []
