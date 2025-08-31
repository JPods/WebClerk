import json
import pytest
from django.test import Client
from apps.orgs.models import OrgBase, OrgType
from django.contrib.auth import get_user_model
User = get_user_model()

@pytest.mark.django_db
def test_wcapi_query_orgs_basic():
    OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Acme Customer', status='active')
    OrgBase.objects.create(org_type=OrgType.VENDOR, display_name='Vendor LLC', status='active')

    User.objects.create_user(email='wcorg@example.com', password='pw12345', name_first='Org', name_last='User', username='')
    c = Client(); assert c.login(email='wcorg@example.com', password='pw12345')

    resp = c.post('/wcapi/query/', data=json.dumps({'table_name': 'orgs'}), content_type='application/json')
    assert resp.status_code == 200
    data = resp.json(); assert data['status'] == 'success' and data['table_name'] == 'orgs'
    names = {r['display_name'] for r in data['data']}
    assert 'Acme Customer' in names and 'Vendor LLC' in names

@pytest.mark.django_db
def test_wcapi_query_customers_proxy_filters():
    OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Cust One', status='active')
    OrgBase.objects.create(org_type=OrgType.VENDOR, display_name='Vend Two', status='active')

    User.objects.create_user(email='wcorg2@example.com', password='pw12345', name_first='Org', name_last='User', username='')
    c = Client(); assert c.login(email='wcorg2@example.com', password='pw12345')

    resp = c.post('/wcapi/query/', data=json.dumps({'table_name': 'customers'}), content_type='application/json')
    assert resp.status_code == 200
    data = resp.json(); assert data['status'] == 'success'
    names = {r['display_name'] for r in data['data']}
    assert 'Cust One' in names and 'Vend Two' not in names
