"""Reading orgs through wcapi: each kind of org is its own model key (customer, vendor, ...).
'orgbase' is the table underneath, not a model the API serves — asking for it is refused, not
answered with an empty page."""
import secrets

import pytest
from django.test import Client
from apps.orgs.models import OrgBase, OrgType
from django.contrib.auth import get_user_model
from tests.utils import assert_envelope, wcapi_get
User = get_user_model()


def _admin(email):
    password = secrets.token_urlsafe(16)
    User.objects.create_user(email=email, password=password, name_first='Org', name_last='User',
                             username='', role='admin')
    c = Client()
    assert c.login(email=email, password=password)
    return c


def _companies(c, model):
    resp = wcapi_get(c, {'model_name': model})
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status='success')
    return {r['company'] for r in data['results']}


@pytest.mark.django_db
def test_wcapi_query_orgs_basic():
    OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Acme Customer', status='active')
    OrgBase.objects.create(org_type=OrgType.VENDOR, company='Vendor LLC', status='active')
    c = _admin('wcorg@example.com')

    assert 'Acme Customer' in _companies(c, 'customer')
    assert 'Vendor LLC' in _companies(c, 'vendor')

    refused = wcapi_get(c, {'model_name': 'orgbase'})
    assert refused.status_code == 400
    assert refused.json()['error']['code'] == 'unknown_model'


@pytest.mark.django_db
def test_wcapi_query_customers_proxy_filters():
    OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Cust One', status='active')
    OrgBase.objects.create(org_type=OrgType.VENDOR, company='Vend Two', status='active')
    c = _admin('wcorg2@example.com')

    names = _companies(c, 'customer')
    assert 'Cust One' in names and 'Vend Two' not in names
