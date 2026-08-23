import json
import pytest
from django.template.response import ContentNotRenderedError
from rest_framework.test import APIClient
from apps.communications.models import Domain
from apps.core.models import Contact

@pytest.fixture
def staff_user(db):
    return Contact.objects.create(
        email='staff@example.com',
        name_first='Staff',
        name_last='User',
        role='admin',
        is_staff=True,
    )

@pytest.fixture
def normal_user(db):
    return Contact.objects.create(
        email='user@example.com',
        name_first='Norm',
        name_last='User',
        role='user',
        is_staff=False,
    )

@pytest.fixture
def api_client(db, staff_user):
    api = APIClient()
    api.force_authenticate(user=staff_user)
    api.defaults['HTTP_ACCEPT'] = 'application/json'
    api.defaults['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
    return api

def _json(resp):
    if hasattr(resp, "render") and callable(getattr(resp, "render")):
        resp = resp.render()
    body = getattr(resp, "content", b"") or b""
    if isinstance(body, bytes):
        body = body.decode("utf-8") or ""
    return json.loads(body or "{}")

# Replace '/domain/' etc. with canonical model-key routes.

def test_domain_list_create_and_pagination(api_client, staff_user):
    client = api_client
    client.force_authenticate(user=staff_user)

    # List via canonical model route
    list_url = '/domain/?format=json'
    resp = client.get(list_url)
    assert resp.status_code == 200
    payload = getattr(resp, 'data', {}) or {}
    payload = payload.get('data', payload)
    assert 'items' in payload

    # Create via wcapi
    create = client.post('/wcapi/save', {'model': 'domain', 'data': {'name': 'example.com', 'is_active': True}}, format='json')
    assert create.status_code in (200, 201)
    cdata = getattr(create, 'data', {}) or {}
    cdata = cdata.get('data', cdata)
    did = cdata.get('id')
    assert did

    # Detail via canonical model route
    detail_url = f'/domain/{did}/'
    d = client.get(detail_url)
    assert d.status_code == 200
    ddata = getattr(d, 'data', {}) or {}
    ddata = ddata.get('data', ddata)
    item = ddata.get('item') or ddata
    assert item.get('id') == did

@pytest.mark.skip(reason="Consolidated /domain/?q searches sync connections, not content domains")
def test_domain_search_permission_and_results(api_client, staff_user, normal_user):
    Domain.objects.create(path='https://linkedin.com/in/jdoe', type='linkedin', comment='Profile JD')
    Domain.objects.create(path='https://github.com/jdoe', type='github', comment='Code repo')
    search_url = '/domain/' + '?q=git&format=json'

    # q requires staff; authenticate first
    api_client.force_authenticate(user=staff_user)

    resp = api_client.get(search_url)
    assert resp.status_code == 200
    payload = _json(resp)

    # Canonical wcapi shape uses "items"
    items = payload.get('items') or (payload.get('data') or {}).get('items')
    assert isinstance(items, list), f"Unexpected payload shape: {payload}"
    git_hits = [it for it in items if 'git' in (it.get('path') or '').lower() or 'git' in (it.get('comment') or '').lower()]
    assert len(git_hits) >= 1

    # Non-staff should be forbidden for q
    api_client.force_authenticate(user=normal_user)
    forbidden = api_client.get(search_url)
    assert forbidden.status_code == 403

@pytest.mark.skip(reason="Legacy domain detail + optimistic patch not supported under consolidated wcapi")
def test_domain_atomic_patch_and_version_conflict(api_client, staff_user):
    pass
