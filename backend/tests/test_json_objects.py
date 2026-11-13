"""A form's json panel lists every JSON object the model has that the viewer may see (Bill,
2026-11-12: "the listing of all objects is a better choice, more flexible, without much sprawl").
GET /wcapi/<model>/fields/ names them; a layout only orders or hides.
"""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact
from apps.core.views.field_rules_view import json_objects_for
from apps.transactions.models import Purchase

pytestmark = pytest.mark.django_db


def test_only_objects_the_viewer_sees_part_of_and_in_the_models_order():
    seen = json_objects_for(Purchase, ['ida', 'totals.total', 'addresses.ship_to.company', 'refs.links'])
    assert seen == [n for n in (f.name for f in Purchase._meta.concrete_fields) if n in ('addresses', 'totals', 'refs')]
    assert 'ida' not in seen and 'emails' not in seen
    assert json_objects_for(Purchase, []) == []


def test_the_endpoint_names_a_purchases_party_objects():
    staff = Contact.objects.create_superuser(email='jsonobjects@example.com', password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    r = client.get('/wcapi/purchase/fields/', HTTP_HOST='localhost')
    assert r.status_code == 200, r.content
    names = r.json()['data']['json_objects']
    assert {'addresses', 'emails', 'phones', 'totals', 'metadata', 'refs', 'prefs', 'config'} <= set(names)
    assert 'ida' not in names and 'lines' not in names
