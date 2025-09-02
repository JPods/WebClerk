import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.communications.models import Domain

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def staff_user(api_client):
    User = get_user_model()
    u = User.objects.create_user(username='staff', email='staff@example.com', password='pw12345', name_first='Staff', name_last='User', role='staff')
    api_client.force_authenticate(user=u)
    return u

@pytest.fixture
def normal_user(api_client):
    User = get_user_model()
    u = User.objects.create_user(username='user', email='user@example.com', password='pw12345', name_first='Norm', name_last='User', role='user')
    return u


def test_domain_list_create_and_pagination(api_client, staff_user):
    list_url = reverse('communications:domain-list')
    # create one
    r = api_client.post(list_url, {'path': 'https://example.com', 'type': 'website', 'comment': 'Main site'}, format='json')
    assert r.status_code in (200, 201)
    for i in range(30):
        api_client.post(list_url, {'path': f'https://ex{i}.com', 'type': 'website'}, format='json')
    page1 = api_client.get(list_url)
    assert page1.status_code == 200
    data = page1.json()
    if isinstance(data, dict) and 'results' in data:
        assert len(data['results']) <= 25
        page2 = api_client.get(list_url + '?page=2')
        assert page2.status_code == 200


def test_domain_search_permission_and_results(api_client, staff_user, normal_user):
    # create sample domains
    Domain.objects.create(path='https://linkedin.com/in/jdoe', type='linkedin', comment='Profile JD')
    Domain.objects.create(path='https://github.com/jdoe', type='github', comment='Code repo')
    search_url = reverse('communications:domain-search') + '?q=git'
    resp = api_client.get(search_url)
    assert resp.status_code == 200
    payload = resp.json()
    # Support new envelope (status/data) or legacy raw (?raw=1)
    results_block = payload.get('results') if 'results' in payload else payload.get('data', {}).get('results') if isinstance(payload.get('data'), dict) else None
    if results_block is None:
        raise AssertionError(f"Unexpected payload shape: {payload}")
    names = [d['path'] for d in results_block]
    assert any('github' in p for p in names)
    # Now auth as normal user (no staff/admin role)
    api_client.force_authenticate(user=normal_user)
    forbidden = api_client.get(search_url)
    assert forbidden.status_code == 403


def test_domain_atomic_patch_and_version_conflict(api_client, staff_user):
    # Create domain
    list_url = reverse('communications:domain-list')
    r = api_client.post(list_url, {'path': 'https://atomic.com', 'type': 'website'}, format='json')
    assert r.status_code in (200,201)
    body = r.json()
    domain_id = body.get('id') or (body.get('data') or {}).get('id')
    assert domain_id, f"Could not extract id from payload {body}"
    detail_url = reverse('communications:domain-detail', args=[domain_id])
    # Fetch to get version
    g = api_client.get(detail_url)
    assert g.status_code == 200
    g_body = g.json()
    version = g_body.get('version') or (g_body.get('data') or {}).get('version')
    # Atomic set
    p1 = api_client.patch(detail_url, {'version': version, 'set': {'metadata.flags.schema_rev': 5}}, format='json')
    assert p1.status_code == 200, p1.json()
    p1_body = p1.json(); new_version = p1_body.get('version') or (p1_body.get('data') or {}).get('version')
    assert new_version == version + 1
    # Use stale version for conflict
    conflict = api_client.patch(detail_url, {'version': version, 'set': {'metadata.flags.schema_rev': 6}}, format='json')
    assert conflict.status_code == 412
    # Append note with current version
    p2 = api_client.patch(detail_url, {'version': new_version, 'append': {'comments.notes': {'text':'hello','type':'info'}}}, format='json')
    assert p2.status_code == 200
    # append should bump version by 1 relative to new_version
    p2_body = p2.json(); v2 = p2_body.get('version') or (p2_body.get('data') or {}).get('version')
    assert v2 == new_version + 1
