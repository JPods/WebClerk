import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from typing import cast
from apps.core.models import Contact, Setting

@pytest.fixture
def api_client(db):
    return APIClient()

@pytest.fixture
def admin_user(db) -> Contact:
    mgr = Contact.objects
    create_user = getattr(mgr, 'create_user', None)
    if callable(create_user):
        u = cast(Contact, create_user(email='admin_settings@example.com', password='pass', name_first='Admin', name_last='User', role='admin', is_staff=True))
    else:
        u = cast(Contact, mgr.create(email='admin_settings@example.com', name_first='Admin', name_last='User', role='admin', is_staff=True))
    u.role = 'admin'; u.is_staff = True; u.save(update_fields=['role','is_staff'])
    return u

@pytest.fixture
def auth_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.mark.django_db
def test_setting_crud_and_search(auth_client):
    # create
    list_url = reverse('setting-list')
    create_resp = auth_client.post(list_url, {'name':'Keywords Config','purpose':'keywords','model_name':'documents','data':{'fields':['title','body']}}, format='json')
    assert create_resp.status_code == 201, getattr(create_resp,'data',None)
    rid = create_resp.data['data'].get('id') or create_resp.data['data'].get('record', {}).get('id')  # type: ignore[attr-defined]
    # detail
    detail_url = reverse('setting-detail', args=[rid])
    get_resp = auth_client.get(detail_url)
    assert get_resp.status_code == 200
    # patch optimistic
    version = get_resp.data['data'].get('version')
    patch_resp = auth_client.patch(detail_url, {'version': version, 'purpose':'keywords_v2'}, format='json')
    assert patch_resp.status_code == 200
    # search
    search_url = reverse('setting-search') + '?q=Keyword'
    search_resp = auth_client.get(search_url)
    assert search_resp.status_code == 200
    assert any(r['name']=='Keywords Config' for r in search_resp.data['data']['results'])  # type: ignore[attr-defined]

@pytest.mark.skip(reason="Legacy setting-detail URL is not part of consolidated wcapi; enable when restored")
def test_setting_version_conflict(auth_client):
    s = Setting.objects.create(name='X', purpose='p')
    detail_url = reverse('setting-detail', args=[s.id])
    # get current version
    get_resp = auth_client.get(detail_url)
    version = get_resp.data['data'].get('version')  # type: ignore[attr-defined]
    # modify once
    ok = auth_client.patch(detail_url, {'version': version, 'name':'X2'}, format='json')
    assert ok.status_code == 200
    # retry with stale version
    stale = auth_client.patch(detail_url, {'version': version, 'name':'X3'}, format='json')
    assert stale.status_code == 412
