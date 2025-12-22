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


def test_wcapi_save_email_auto_links_to_authenticated_contact(api_client, staff_user):
    client = api_client
    payload = {'model_name': 'email', 'data': {'email': 'auto@link.test', 'name': 'work'}}
    resp = client.post('/wcapi/save', payload, format='json')
    assert resp.status_code in (200, 201)
    data = _json(resp)
    created_id = data.get('id') or (data.get('data') or {}).get('id')
    assert created_id
    # The API should also indicate whether the created object was linked to the contact
    assert data.get('linked') is True

    # Refresh contact and verify denormalized object exists under refs.links.email
    staff_user.refresh_from_db()
    links = (staff_user.refs or {}).get('links') or {}
    emails = links.get('email') or []
    assert any(isinstance(e, dict) and e.get('id') == created_id and e.get('email') == 'auto@link.test' for e in emails)


def test_wcapi_save_email_links_to_explicit_contact_id(api_client, db):
    # create a different contact and send explicit contact_id in payload
    from apps.core.models import Contact
    contact = Contact.objects.create(email='other@example.com', name_first='Other', name_last='Person')
    api = APIClient()
    # authenticate as staff to allow save
    staff = Contact.objects.create(email='staff3@example.com', name_first='Staff', name_last='Three', role='admin', is_staff=True)
    api.force_authenticate(user=staff)

    payload = {'model_name': 'email', 'data': {'email': 'explicit@link.test', 'name': 'home', 'contact_id': contact.id}}
    resp = api.post('/wcapi/save', payload, format='json')
    assert resp.status_code in (200, 201)
    data = _json(resp)
    created_id = data.get('id') or (data.get('data') or {}).get('id')
    assert created_id
    # The API should also indicate whether the created object was linked to the specified contact
    assert data.get('linked') is True

    contact.refresh_from_db()
    links = (contact.refs or {}).get('links') or {}
    emails = links.get('email') or []
    assert any(isinstance(e, dict) and e.get('id') == created_id and e.get('email') == 'explicit@link.test' for e in emails)
