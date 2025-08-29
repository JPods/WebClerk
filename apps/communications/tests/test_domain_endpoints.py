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
    u = User.objects.create_user(email='staff@example.com', password='pw12345', name_first='Staff', name_last='User', role='staff', username='staff')
    api_client.force_authenticate(user=u)
    return u

@pytest.fixture
def normal_user(api_client):
    User = get_user_model()
    u = User.objects.create_user(email='user@example.com', password='pw12345', name_first='Norm', name_last='User', role='user', username='norm')
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
    names = [d['path'] for d in payload['results']]
    assert any('github' in p for p in names)
    # Now auth as normal user (no staff/admin role)
    api_client.force_authenticate(user=normal_user)
    forbidden = api_client.get(search_url)
    assert forbidden.status_code == 403
