import pytest
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin_user(client):
    from django.contrib.auth import get_user_model
    U = get_user_model()
    u = U.objects.create_superuser(username='admin', email='a@example.com', password='pw')
    client.force_authenticate(user=u)
    return u


def test_readme_sync_requires_admin(client):
    url = reverse('readme-sync')
    resp = client.get(url)
    assert resp.status_code in (401, 403)


def test_readme_sync_dry_run_ok(client, admin_user):
    url = reverse('readme-sync')
    resp = client.get(url, {'dry_run': '1', 'include_output': '1'})
    assert resp.status_code == 200, resp.content
    payload = resp.json().get('data', resp.json())
    assert payload.get('ok') is True
    assert 'stats' in payload