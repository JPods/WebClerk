import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.core.models import Contact
from apps.core.models.action import Action

@pytest.fixture
def user(db):
    return Contact.objects.create_user(email='actiontester@example.com', password='pass', name_first='A', name_last='Tester', role='admin', is_staff=True)

@pytest.fixture
def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c

@pytest.mark.django_db
def test_action_list_create_and_pagination(auth_client):
    url = reverse('action2-list')
    r = auth_client.post(url, {"action":"Call Customer","status":"open","priority":"high"}, format='json')
    assert r.status_code in (200,201)
    for i in range(3):
        Action.objects.create(action=f"Task {i}")
    resp = auth_client.get(url)
    assert resp.status_code == 200
    assert 'results' in resp.data
    assert resp.data['count'] >= 4

@pytest.mark.django_db
def test_action_detail_atomic_patch(auth_client):
    obj = Action.objects.create(action='Follow Up', status='open')
    detail = reverse('action2-detail', args=[obj.id])
    get_resp = auth_client.get(detail)
    version = get_resp.data['version']
    patch_resp = auth_client.patch(detail, {"version":version, "set":{"metadata.flags.schema_rev":2}}, format='json')
    assert patch_resp.status_code == 200
    assert patch_resp.data['version'] == version + 1
    conflict = auth_client.patch(detail, {"version":version, "set":{"metadata.flags.schema_rev":3}}, format='json')
    assert conflict.status_code == 409

@pytest.mark.django_db
def test_action_search(auth_client):
    Action.objects.create(action='Alpha Task')
    Action.objects.create(action='Beta Task')
    url = reverse('action2-search') + '?q=Al'
    resp = auth_client.get(url)
    assert resp.status_code == 200
    names = [r['action'] for r in resp.data['results']]
    assert any('Alpha' in n for n in names)
