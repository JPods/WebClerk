import json
import pytest
from django.test import Client
from apps.orgs.models import OrgBase, OrgType
from django.contrib.auth import get_user_model
from tests.utils import assert_envelope
User = get_user_model()

@pytest.mark.django_db
def test_wcapi_query_orgs_basic():
    OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Acme Customer', status='active')
    OrgBase.objects.create(org_type=OrgType.VENDOR, company='Vendor LLC', status='active')

    User.objects.create_user(email='wcorg@example.com', password='pw12345', name_first='Org', name_last='User', username='')
    c = Client(); assert c.login(email='wcorg@example.com', password='pw12345')

    resp = c.post('/wcapi/query/', data=json.dumps({'model_name': 'org'}), content_type='application/json')  #chaned from t_n
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status='success')
    assert data['model_name'] == 'org'
    names = {r['company'] for r in data['results']}
    assert 'Acme Customer' in names and 'Vendor LLC' in names

@pytest.mark.django_db
def test_wcapi_query_customers_proxy_filters():
    OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Cust One', status='active')
    OrgBase.objects.create(org_type=OrgType.VENDOR, company='Vend Two', status='active')

    User.objects.create_user(email='wcorg2@example.com', password='pw12345', name_first='Org', name_last='User', username='')
    c = Client(); assert c.login(email='wcorg2@example.com', password='pw12345')

    resp = c.post('/wcapi/query/', data=json.dumps({'model_name': 'customer'}), content_type='application/json')  #chaned from t_n
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status='success')
    names = {r['company'] for r in data['results']}
    assert 'Cust One' in names and 'Vend Two' not in names
