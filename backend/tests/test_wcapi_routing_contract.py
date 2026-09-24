"""Tests for the canonical wcapi routing contract.

All data operations route through the REST channel: /wcapi/<model>/[<id>/].
There are no /<model>/ URL patterns — those are legacy patterns that no longer exist.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tests.utils import wcapi_get

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create(
        email='admin@routing.test',
        name_first='Admin',
        name_last='User',
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
def test_wcapi_get_returns_success_envelope(admin_user):
    """GET /wcapi/get/?model_name=contact returns a success envelope."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = wcapi_get(client, {'model_name': 'contact'})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('status') == 'success'
    assert 'data' in data


@pytest.mark.django_db
def test_wcapi_get_with_model_path(admin_user):
    """GET /wcapi/<model>/ returns a success envelope."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.get('/wcapi/contact/')
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('status') == 'success'


@pytest.mark.django_db
def test_wcapi_save_refuses_a_payload_naming_another_model(admin_user):
    """POST /wcapi/<model>/ — the path names the model; a payload naming another is refused."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.post('/wcapi/contact/', {'model_name': 'item'}, format='json')
    assert resp.status_code == 400
    assert resp.json()['error']['code'] == 'model_mismatch'


@pytest.mark.django_db
def test_wcapi_delete_requires_model_and_id(admin_user):
    """DELETE /wcapi/<model>/ (no id) is not a verb."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.delete('/wcapi/contact/')
    assert resp.status_code == 405
