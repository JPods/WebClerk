import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.sync.models.connection import Connection

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def staff_user(api_client):
    User = get_user_model()
    u = User.objects.create_user(email='syncstaff@example.com', password='pw12345', name_first='Sync', name_last='Staff', role='staff', username='syncstaff')
    api_client.force_authenticate(user=u)
    return u

@pytest.fixture
def normal_user(api_client):
    User = get_user_model()
    u = User.objects.create_user(email='syncuser@example.com', password='pw12345', name_first='Sync', name_last='User', role='user', username='syncuser')
    return u


def test_connection_list_create_and_pagination(api_client, staff_user):
    list_url = reverse('sync:connection-list')
    r = api_client.post(list_url, {'name': 'Main ERP', 'type': 'erp', 'config': {'host':'h'}}, format='json')
    assert r.status_code in (200,201)
    for i in range(30):
        api_client.post(list_url, {'name': f'C{i}', 'type': 'erp', 'config': {'i': i}}, format='json')
    page1 = api_client.get(list_url)
    assert page1.status_code == 200
    data = page1.json()
    assert 'results' in data and len(data['results']) <= 25


def test_connection_search_permission_and_results(api_client, staff_user, normal_user):
    Connection.objects.create(name='HubSpot', type='crm', config={})
    Connection.objects.create(name='Netsuite', type='erp', config={})
    search_url = reverse('sync:connection-search') + '?q=hub'
    resp = api_client.get(search_url)
    assert resp.status_code == 200
    paths = [c['name'] for c in resp.json()['results']]
    assert any('HubSpot' in p for p in paths)
    api_client.force_authenticate(user=normal_user)
    forbidden = api_client.get(search_url)
    assert forbidden.status_code == 403


def test_connection_atomic_patch(api_client, staff_user):
    list_url = reverse('sync:connection-list')
    r = api_client.post(list_url, {'name': 'PatchTarget', 'type': 'erp', 'config': {}}, format='json')
    cid = r.json()['id']
    detail = reverse('sync:connection-detail', args=[cid])
    g = api_client.get(detail)
    version = g.json()['version']
    p1 = api_client.patch(detail, {'version': version, 'set': {'metadata.flags.schema_rev': 2}}, format='json')
    assert p1.status_code == 200
    new_version = p1.json()['version']
    # stale conflict
    conflict = api_client.patch(detail, {'version': version, 'set': {'metadata.flags.schema_rev': 3}}, format='json')
    assert conflict.status_code == 412
    p2 = api_client.patch(detail, {'version': new_version, 'append': {'comments.notes': {'text':'sync note'}}}, format='json')
    assert p2.status_code == 200
