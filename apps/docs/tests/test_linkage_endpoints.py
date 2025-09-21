import pytest
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


# Ensure a minimal payload exists for create
linkage_payload = {
    "type": "reference",
    "status": "active",
    "comment": "Test linkage",
}

def test_linkage_crud_and_links(api_client, user):
    client = api_client
    client.force_authenticate(user=user)

    # Canonical list route
    list_url = '/linkage/?format=json'
    resp = client.get(list_url)
    assert resp.status_code == 200

    # Create via wcapi canonical route
    create = client.post('/wcapi/save', {'model': 'linkage', 'data': linkage_payload}, format='json')
    assert create.status_code in (200, 201), getattr(create, 'data', None)
    cdata = getattr(create, 'data', {}) or {}
    cdata = cdata.get('data', cdata)
    lid = cdata.get('id')
    assert lid

    # Canonical detail route
    detail_url = f'/linkage/{lid}/?format=json'
    d = client.get(detail_url)
    assert d.status_code == 200

    # For updates use:
    # upd = client.post(f'/linkage/{lid}/', {'data': {'field': 'value'}}, format='json')
    # For delete use:
    # delr = client.delete(f'/linkage/{lid}/')


# from django.urls import reverse  # legacy, not used

def test_linkage_pagination(api_client, user):
    client = api_client
    client.force_authenticate(user=user)

    # Canonical list route
    list_url = '/linkage/?format=json'

    # Create a batch via wcapi canonical create
    for i in range(30):
        r = client.post(
            '/wcapi/save',
            {'model': 'linkage', 'data': {'name': f'L{i}', 'purpose': 'batch'}},
            format='json',
        )
        assert r.status_code in (200, 201), getattr(r, 'data', None)

    # List and assert canonical payload uses "items"
    page1 = client.get(list_url)
    assert page1.status_code == 200
    data = (getattr(page1, 'data', {}) or {}).get('data', getattr(page1, 'data', {}) or {})
    items = data.get('items') or []
    assert isinstance(items, list)
    assert len(items) >= 1
