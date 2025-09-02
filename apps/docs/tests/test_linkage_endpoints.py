import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.docs.models.linkage import Linkage

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(api_client):
    User = get_user_model()
    u = User.objects.create_user(email='linktester@example.com', password='pw12345', name_first='Link', name_last='Tester', username='')
    api_client.force_authenticate(user=u)
    return u


def test_linkage_crud_and_links(api_client, user):
    list_url = reverse('linkage-list')
    resp = api_client.post(list_url, {'name': 'L1', 'purpose': 'generic'}, format='json')
    assert resp.status_code in (200,201)
    link_id = resp.json()['data']['id']
    detail_url = reverse('linkage-detail', args=[link_id])
    get_resp = api_client.get(detail_url)
    assert get_resp.status_code == 200
    links_url = reverse('linkage-links', args=[link_id])
    add_resp = api_client.post(links_url, {'table': 'proposal_lines', 'record_id': 123}, format='json')
    assert add_resp.status_code == 200
    assert add_resp.json()['data']['added'] is True
    # duplicate add should be False
    add_resp2 = api_client.post(links_url, {'table': 'proposal_lines', 'record_id': 123}, format='json')
    assert add_resp2.json()['data']['added'] is False
    # remove
    del_resp = api_client.delete(links_url, {'table': 'proposal_lines', 'record_id': 123}, format='json')
    assert del_resp.status_code == 200
    assert del_resp.json()['data']['removed'] is True


def test_linkage_pagination(api_client, user):
    list_url = reverse('linkage-list')
    for i in range(30):
        api_client.post(list_url, {'name': f'L{i}', 'purpose': 'batch'}, format='json')
    page1 = api_client.get(list_url)
    assert page1.status_code == 200
    # Expect paginated style (results key) or list fallback
    data = page1.json()['data']
    assert len(data['results']) <= 25
    page2 = api_client.get(list_url + '?page=2')
    assert page2.status_code == 200
