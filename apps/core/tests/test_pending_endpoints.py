import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.core.models import Pending, Contact
from typing import cast

@pytest.fixture
def api_client(db):
    return APIClient()
@pytest.fixture
def user(db) -> Contact:
    mgr = Contact.objects
    create_user = getattr(mgr, 'create_user', None)
    if callable(create_user):
        u = cast(Contact, create_user(email='user@example.com', password='pass', name_first='U', name_last='Ser', role='admin', is_staff=True))
    else:
        u = cast(Contact, mgr.create(email='user@example.com', name_first='U', name_last='Ser', role='admin', is_staff=True))
    u.role = 'admin'
    u.is_staff = True
    u.save(update_fields=['role','is_staff'])
    return u
    return u

@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

@pytest.mark.django_db
def test_pending_list_create_and_pagination(auth_client):
    # create few records
    for i in range(3):
        Pending.objects.create(model_name='domain', record_id=str(i))
    url = reverse('pending-list')
    resp = auth_client.get(url)
    assert resp.status_code == 200
    payload = resp.data
    assert 'data' in payload and 'results' in payload['data']
    assert payload['data']['count'] >= 3

@pytest.mark.django_db
def test_pending_detail_and_optimistic_patch(auth_client):
    p = Pending.objects.create(model_name='domain', record_id='42')
    detail_url = reverse('pending-detail', args=[p.id])
    # fetch
    resp = auth_client.get(detail_url)
    assert resp.status_code == 200
    version = resp.data['data']['version']
    # optimistic patch metadata.flags.processed_pending
    patch_body = {
        'version': version,
        'ops': [
            {'op':'set','field':'metadata','path':['flags','processed_pending'],'value':True}
        ]
    }
    patch_resp = auth_client.patch(detail_url, patch_body, format='json')
    assert patch_resp.status_code == 200
    assert patch_resp.data['data']['version'] == version + 1
    # conflict test
    conflict_resp = auth_client.patch(detail_url, patch_body, format='json')
    assert conflict_resp.status_code == 412

@pytest.mark.django_db
def test_pending_search(auth_client):
    Pending.objects.create(model_name='alpha', record_id='1')
    Pending.objects.create(model_name='beta', record_id='2')
    url = reverse('pending-search') + '?q=alp'
    resp = auth_client.get(url)
    assert resp.status_code == 200
    assert any(r.get('model_name')=='alpha' for r in resp.data['data']['results'])
