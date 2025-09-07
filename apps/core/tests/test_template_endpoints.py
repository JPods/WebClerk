import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from typing import cast
from apps.core.models import Contact, Template

@pytest.fixture
def api_client(db):
    return APIClient()

@pytest.fixture
def admin_user(db) -> Contact:
    mgr = Contact.objects
    create_user = getattr(mgr, 'create_user', None)
    if callable(create_user):
        u = cast(Contact, create_user(email='admin_templates@example.com', password='pass', name_first='Admin', name_last='User', role='admin', is_staff=True))
    else:
        u = cast(Contact, mgr.create(email='admin_templates@example.com', name_first='Admin', name_last='User', role='admin', is_staff=True))
    u.role = 'admin'; u.is_staff = True; u.save(update_fields=['role','is_staff'])
    return u

@pytest.fixture
def auth_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.mark.django_db
def test_template_crud_and_search(auth_client):
    # create
    list_url = reverse('template-list')
    create_resp = auth_client.post(list_url, {'name':'Welcome Email','purpose':'welcome','model_name':'email'}, format='json')
    assert create_resp.status_code == 201, getattr(create_resp,'data',None)
    rid = create_resp.data['data'].get('id') or create_resp.data['data'].get('record', {}).get('id')  # type: ignore[attr-defined]
    # detail
    detail_url = reverse('template-detail', args=[rid])
    get_resp = auth_client.get(detail_url)
    assert get_resp.status_code == 200
    # patch optimistic
    version = get_resp.data['data'].get('version')  # type: ignore[attr-defined]
    patch_resp = auth_client.patch(detail_url, {'version': version, 'purpose':'welcome_v2'}, format='json')
    assert patch_resp.status_code == 200
    # search
    search_url = reverse('template-search') + '?q=Welcome'
    search_resp = auth_client.get(search_url)
    assert search_resp.status_code == 200
    assert any(r['name']=='Welcome Email' for r in search_resp.data['data']['results'])  # type: ignore[attr-defined]

@pytest.mark.django_db
def test_template_version_conflict(auth_client):
    s = Template.objects.create(name='T', purpose='p')
    detail_url = reverse('template-detail', args=[s.id])
    get_resp = auth_client.get(detail_url)
    version = get_resp.data['data'].get('version')  # type: ignore[attr-defined]
    ok = auth_client.patch(detail_url, {'version': version, 'name':'T2'}, format='json')
    assert ok.status_code == 200
    stale = auth_client.patch(detail_url, {'version': version, 'name':'T3'}, format='json')
    assert stale.status_code == 412
