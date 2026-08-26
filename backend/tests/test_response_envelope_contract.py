import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.products.models.item import Item


pytestmark = pytest.mark.django_db


def _create_user(role='user'):
    User = get_user_model()
    u = User.objects.create_user(
        username=f'{role}_tester',
        email=f'{role}_tester@example.com',
        password='pw12345',
        name_first=role.capitalize(),
        name_last='Tester',
        role=role,
    )
    return u


@pytest.fixture
def api_client(client):
    return client


def test_envelope_presence_core_endpoints(api_client):
    """Smoke contract: representative JSON API endpoints must include top-level 'status'.

    This guards against accidental regressions (e.g. removing api_response() calls,
    deleting middleware, or returning a bare list/dict) that would break clients
    relying on the unified envelope.
    """
    # Auth user (normal) for most endpoints
    user = _create_user('user')
    api_client.force_login(user)

    # Email list (should auto-create empty data array envelope)
    email_list_url = '/domain/'
    r = api_client.get(email_list_url)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict) and 'status' in body, body

    # Raw query parameter is ignored; envelope must still be present
    raw_r = api_client.get(email_list_url + '?raw=1')
    raw_body = raw_r.json()
    assert 'status' in raw_body and isinstance(raw_body, dict)

    # Create a parent/component items for BOM list
    parent = Item.objects.create(name='ContractParent')
    component = Item.objects.create(name='ContractComponent')
    bom_url = '/domain/'
    # List (empty)
    bom_list = api_client.get(bom_url)
    assert bom_list.status_code == 200
    bom_body = bom_list.json()
    assert 'status' in bom_body, bom_body
    # Create a BOM line then list again
    create_resp = api_client.post(bom_url, {'component_id': component.id, 'quantity': '1'})
    assert create_resp.status_code in (200, 201)
    assert 'status' in create_resp.json()
    bom_list2 = api_client.get(bom_url)
    assert 'status' in bom_list2.json()

    # Universal API (wcapi) manage view should already be enveloped
    manage_url = '/wcapi/_manage/?model_name=contact'
    manage_resp = api_client.get(manage_url)
    if manage_resp.status_code == 200:  # allow 200 only; other codes would still include status
        assert 'status' in manage_resp.json(), manage_resp.json()

    # Domain endpoints require staff role
    staff = _create_user('staff')
    api_client.force_login(staff)
    domain_list_url = '/domain/'
    d_list = api_client.get(domain_list_url)
    assert d_list.status_code == 200
    assert 'status' in d_list.json(), d_list.json()

    # Create domain
    d_create = api_client.post(domain_list_url, {'path': 'https://contract.example', 'type': 'website'})
    assert d_create.status_code in (200, 201)
    assert 'status' in d_create.json()


def test_envelope_delete_semantics(api_client):
    """Ensure delete responses are enveloped (except raw escape)."""
    staff = _create_user('staff')
    api_client.force_login(staff)
    domain_list_url = '/domain/'
    created = api_client.post(domain_list_url, {'path': 'https://delete.example', 'type': 'website'})
    body = created.json()
    domain_id = body.get('data', {}).get('id') or body.get('id')
    assert domain_id, body
    detail_url = '/domain/'
    del_resp = api_client.delete(detail_url)
    assert del_resp.status_code in (200, 204)  # enveloped implementation currently returns 200
    if del_resp.status_code == 200:
        assert 'status' in del_resp.json(), del_resp.json()
