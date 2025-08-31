from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.docs.models.document import Document
import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(api_client):
    User = get_user_model()
    u = User.objects.create_user(username='tester', email='tester@example.com', password='pw12345', name_first='Test', name_last='User')
    api_client.force_authenticate(user=u)
    return u


def test_document_search_basic(api_client, user):
    d1 = Document.objects.create(name='System Architecture', body='This document describes the overall system architecture and components.')
    d2 = Document.objects.create(name='Release Plan', body='Plan for Q1 release including milestones and deliverables.')
    d1.rebuild_search_vector()
    d2.rebuild_search_vector()

    url = reverse('document-search')
    resp = api_client.get(url, {'q': 'architecture'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['count'] == 1
    assert data['results'][0]['name'] == 'System Architecture'


def test_document_list_create(api_client, user):
    url = reverse('document-list')
    resp = api_client.post(url, {'name':'Spec Alpha','body':'Alpha spec body'}, format='json')
    assert resp.status_code in (200,201)
    list_resp = api_client.get(url)
    assert list_resp.status_code == 200
    payload = list_resp.json()
    if isinstance(payload, dict) and 'results' in payload:
        results = payload['results']
    else:
        results = payload
    assert any(r.get('name') == 'Spec Alpha' for r in results)


def test_document_search_highlight_and_filters(api_client, user):
    # create docs with varying status and security level
    d1 = Document.objects.create(name='Alpha Guide', body='Architecture patterns and system overview', status='published', security_level=1)
    d2 = Document.objects.create(name='Beta Plan', body='Plan covers architecture roadmaps', status='draft', security_level=2)
    d3 = Document.objects.create(name='Gamma Notes', body='Miscellaneous text', status='published', security_level=1)
    for d in (d1,d2,d3):
        d.rebuild_search_vector()

    search_url = reverse('document-search')
    resp = api_client.get(search_url, {'q': 'architecture', 'status': 'published', 'level': 1})
    assert resp.status_code == 200
    payload = resp.json()
    # Only d1 should match architecture AND published AND level 1
    assert payload['count'] == 1
    first = payload['results'][0]
    assert first['name'] == 'Alpha Guide'
    assert '<mark>' in first['highlight_snippet']
    # ordering test: list endpoint ordering by name asc
    list_url = reverse('document-list')
    list_resp = api_client.get(list_url + '?ordering=name')
    assert list_resp.status_code == 200
    list_payload = list_resp.json()['results'] if isinstance(list_resp.json(), dict) and 'results' in list_resp.json() else list_resp.json()
    names = [r['name'] for r in list_payload]
    assert names == sorted(names)
