import pytest
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
    u = User.objects.create_user(username='syncstaff', email='syncstaff@example.com', password='pw12345', name_first='Sync', name_last='Staff', role='staff', is_staff=True)
    api_client.force_authenticate(user=u)
    return u

@pytest.fixture
def normal_user(api_client):
    User = get_user_model()
    u = User.objects.create_user(username='syncuser', email='syncuser@example.com', password='pw12345', name_first='Sync', name_last='User', role='user')
    return u


def test_connection_list_via_wcapi(api_client, staff_user):
    """Test that connections can be listed via /wcapi/get/."""
    api_client.defaults['HTTP_ACCEPT'] = 'application/json'
    api_client.defaults['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    resp = api_client.get('/wcapi/get/', {'model_name': 'connection'})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get('status') == 'success'


def test_connection_create_via_wcapi(api_client, staff_user):
    """Test that connections can be created via /wcapi/save/."""
    api_client.defaults['HTTP_ACCEPT'] = 'application/json'
    api_client.defaults['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    payload = {
        'model_name': 'connection',
        'data': {'name': 'Main ERP', 'type': 'erp', 'config': {'host': 'h'}}
    }
    resp = api_client.post('/wcapi/save/', payload, format='json')
    assert resp.status_code in (200, 201)
    body = resp.json()
    assert body.get('status') == 'success'


@pytest.mark.skip(reason="POST /domain/ disabled under consolidated wcapi; use /wcapi/save/ instead")
def test_connection_atomic_patch(api_client, staff_user):
    list_url = '/domain/'
    r = api_client.post(list_url, {'name': 'PatchTarget', 'type': 'erp', 'config': {}}, format='json')
    cid = r.json()['data']['id']
    detail = '/domain/'
    g = api_client.get(detail)
    version = g.json()['data']['version']
    p1 = api_client.patch(detail, {'version': version, 'set': {'metadata.flags.schema_rev': 2}}, format='json')
    assert p1.status_code == 200
    new_version = p1.json()['data']['version']
    # stale conflict
    conflict = api_client.patch(detail, {'version': version, 'set': {'metadata.flags.schema_rev': 3}}, format='json')
    assert conflict.status_code == 412
    p2 = api_client.patch(detail, {'version': new_version, 'append': {'comments.notes': {'text':'sync note'}}}, format='json')
    assert p2.status_code == 200
