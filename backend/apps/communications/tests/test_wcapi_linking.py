import pytest
from rest_framework.test import APIClient


@pytest.fixture
def staff_user(db):
    from apps.core.models import Contact
    return Contact.objects.create(
        email='staff2@example.com',
        name_first='Staff',
        name_last='Two',
        role='admin',
        is_staff=True,
    )

@pytest.fixture
def api_client(db, staff_user):
    api = APIClient()
    api.force_authenticate(user=staff_user)
    api.defaults['HTTP_ACCEPT'] = 'application/json'
    api.defaults['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
    return api


def _json(resp):
    # Helper to decode response data
    try:
        return getattr(resp, 'data', {}) or {}
    except Exception:
        return {}


def test_wcapi_save_email_creates_record(api_client, staff_user):
    """Test that /wcapi/save/ can create an email record."""
    client = api_client
    payload = {'model_name': 'email', 'data': {'email': 'auto@link.test', 'name': 'work'}}
    resp = client.post('/wcapi/save/', payload, format='json')
    assert resp.status_code in (200, 201), f"Unexpected status {resp.status_code}: {resp.content}"
    data = _json(resp)
    # Response is an envelope: {status, code, message, data}
    inner = data.get('data', data)
    created_id = inner.get('id')
    assert created_id, f"Expected id in response data: {data}"


def test_wcapi_save_email_with_contact_id(api_client, db):
    """Test that /wcapi/save/ can create an email record with explicit contact_id."""
    from apps.core.models import Contact
    contact = Contact.objects.create(email='other@example.com', name_first='Other', name_last='Person')
    api = APIClient()
    staff = Contact.objects.create(email='staff3@example.com', name_first='Staff', name_last='Three', role='admin', is_staff=True)
    api.force_authenticate(user=staff)
    api.defaults['HTTP_ACCEPT'] = 'application/json'
    api.defaults['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    payload = {'model_name': 'email', 'data': {'email': 'explicit@link.test', 'name': 'home', 'contact_id': contact.id}}
    resp = api.post('/wcapi/save/', payload, format='json')
    assert resp.status_code in (200, 201), f"Unexpected status {resp.status_code}: {resp.content}"
    data = _json(resp)
    inner = data.get('data', data)
    created_id = inner.get('id')
    assert created_id, f"Expected id in response data: {data}"
