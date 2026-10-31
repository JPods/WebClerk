"""A dt_ field holds UTC epoch milliseconds (Bill: dates are stored UTC; a date typed in a form
is 23:59 local, which only the browser knows). A date string was coerced to its first digits:
'2026-12-06' stored 2026 — January 1970 — with a 200. It is refused, saying what to send."""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Action, Contact

pytestmark = pytest.mark.django_db


def _client():
    su = Contact.objects.create_superuser(email='dt@example.com', password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(su)
    return client


def test_a_date_string_is_refused_not_stored_as_1970():
    client, action = _client(), Action.objects.create(action={'en': 'zz'})
    r = client.put(f'/wcapi/action/{action.id}/', {'dt_deadline': '2026-12-06'}, format='json', HTTP_HOST='localhost')
    assert r.status_code == 400 and 'epoch milliseconds' in str(r.json()['error']['details'])
    action.refresh_from_db()
    assert action.dt_deadline in (None, 0)


def test_epoch_milliseconds_are_stored():
    client, action = _client(), Action.objects.create(action={'en': 'zz'})
    ms = 1796515199999                           # 2026-12-06 23:59:59.999 in some local zone
    r = client.put(f'/wcapi/action/{action.id}/', {'dt_deadline': ms}, format='json', HTTP_HOST='localhost')
    assert r.status_code == 200, r.json()
    action.refresh_from_db()
    assert action.dt_deadline == ms


def test_a_timestamp_naming_its_zone_is_converted():
    client, action = _client(), Action.objects.create(action={'en': 'zz'})
    r = client.put(f'/wcapi/action/{action.id}/', {'dt_deadline': '2026-09-24T12:00:00Z'}, format='json', HTTP_HOST='localhost')
    assert r.status_code == 200, r.json()
    action.refresh_from_db()
    assert action.dt_deadline == 1790251200000
