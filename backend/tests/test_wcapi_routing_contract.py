"""Tests for the canonical wcapi routing contract.

All data operations route through /wcapi/get/, /wcapi/save/, /wcapi/delete/.
There are no /<model>/ URL patterns — those are legacy patterns that no longer exist.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

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

    resp = client.get('/wcapi/get/', {'model_name': 'contact'})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('status') == 'success'
    assert 'data' in data


@pytest.mark.django_db
def test_wcapi_get_with_model_path(admin_user):
    """GET /wcapi/get/<model_name>/ returns a success envelope."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.get('/wcapi/get/contact/')
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('status') == 'success'


@pytest.mark.django_db
def test_wcapi_save_requires_data(admin_user):
    """POST /wcapi/save/ with empty payload returns an error."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.post('/wcapi/save/', {}, format='json')
    # Missing model_name should return an error (400 or 500 depending on how save validates)
    assert resp.status_code in (400, 422, 500)


@pytest.mark.django_db
def test_wcapi_delete_requires_model_and_id(admin_user):
    """POST /wcapi/delete/ without model_name and id returns 400."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.post('/wcapi/delete/', {}, format='json')
    assert resp.status_code == 400
