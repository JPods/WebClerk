import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.core.models import Contact
from apps.transactions.models import Requisition

pytestmark = pytest.mark.skip(reason="requisition2 viewset/URLs not yet implemented")

@pytest.fixture
def user(db):
    # Use create instead of create_user since Contact manager lacks create_user
    u = Contact.objects.create(email='reqtester@example.com', name_first='R', name_last='Tester', role='admin', is_staff=True)
    # If a hashed password is ever needed (not required for force_authenticate):
    # u.set_password('pass'); u.save()
    return u

@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
def test_requisition_list_create_and_pagination(auth_client):
    url = reverse('requisition2-list')
    # create
    resp = auth_client.post(url, {"name":"Req A","purpose":"ops","status":"draft"}, format='json')
    assert resp.status_code in (200,201)
    # seed more
    for i in range(3):
        Requisition.objects.create(name=f"Req {i}", purpose='ops', status='draft')
    resp = auth_client.get(url)
    assert resp.status_code == 200
    assert 'data' in resp.data and 'results' in resp.data['data']
    assert resp.data['data']['count'] >= 4

@pytest.mark.django_db
def test_requisition_detail_and_atomic_patch(auth_client):
    r = Requisition.objects.create(name='PatchMe', purpose='ops', status='draft')
    detail = reverse('requisition2-detail', args=[r.id])
    get_resp = auth_client.get(detail)
    version = get_resp.data['data']['version']
    # atomic set metadata flag
    patch_resp = auth_client.patch(detail, {"version":version, "set":{"metadata.flags.schema_rev":2}}, format='json')
    assert patch_resp.status_code == 200
    assert patch_resp.data['data']['version'] == version + 1
    # conflict
    conflict = auth_client.patch(detail, {"version":version, "set":{"metadata.flags.schema_rev":3}}, format='json')
    assert conflict.status_code == 412

@pytest.mark.django_db
def test_requisition_search(auth_client):
    Requisition.objects.create(name='Alpha', purpose='ops', status='draft')
    Requisition.objects.create(name='Beta', purpose='ops', status='draft')
    url = reverse('requisition2-search') + '?q=Al'
    resp = auth_client.get(url)
    assert resp.status_code == 200
    names = [r['name'] for r in resp.data['data']['results']]
    assert 'Alpha' in names
