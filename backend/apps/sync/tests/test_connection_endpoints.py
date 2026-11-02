import secrets

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.sync.models.connection import Connection
from tests.utils import wcapi_save, wcapi_get

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(api_client):
    User = get_user_model()
    u = User.objects.create_user(username='syncadmin', email='syncadmin@example.com',
                                 password=secrets.token_urlsafe(16), name_first='Sync',
                                 name_last='Admin', role='admin')
    api_client.force_authenticate(user=u)
    return u


def test_connection_list_via_wcapi(api_client, admin_user):
    """Connections are listed through GET /wcapi/connection/."""
    resp = wcapi_get(api_client, {'model_name': 'connection'})
    assert resp.status_code == 200
    assert resp.json().get('status') == 'success'


def test_connection_create_via_wcapi(api_client, admin_user):
    """A connection is created through wcapi like any record."""
    payload = {'model_name': 'connection', 'name': 'Main ERP', 'type': 'erp', 'config': {'host': 'h'}}
    resp = wcapi_save(api_client, payload, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json().get('status') == 'success'
    assert Connection.objects.filter(name='Main ERP').exists()
