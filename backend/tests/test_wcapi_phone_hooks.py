import json
import pytest
from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from apps.communications.models import Phone
from tests.utils import assert_envelope, wcapi_save
import secrets

# Generated per run — no password literal in the repository.
TEST_PASSWORD = secrets.token_urlsafe(16)

User = get_user_model()

@pytest.mark.django_db
@pytest.mark.hooks
def test_phone_pre_and_post_hooks_success(monkeypatch):
    user = User.objects.create_user(email='phook@example.com', password=TEST_PASSWORD, name_first='P', name_last='User', username='', role='admin')  # hooks, not access
    c = Client(); assert c.login(email='phook@example.com', password=TEST_PASSWORD)
    payload = {
        'model_name': 'phone',  #chaned from t_n
        'number': '5551234',
        'country_code': '+1',
        'name': 'Desk'
    }
    # enable universal validation so api_validate_payload runs
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = wcapi_save(c, data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200, resp.content
    data = assert_envelope(resp.json(), expect_status='success')
    phone = Phone.objects.get(number='5551234')
    # The after hook (CommunicationBehaviour) links the phone to the person who saved it.
    user.refresh_from_db()
    linked = ((user.refs or {}).get('links') or {}).get('phone') or []
    assert any(isinstance(l, dict) and l.get('id') == phone.pk for l in linked), user.refs

@pytest.mark.django_db
@pytest.mark.hooks
def test_phone_pre_save_rejects_short_number():
    user = User.objects.create_user(email='phook2@example.com', password=TEST_PASSWORD, name_first='P', name_last='User', username='', role='admin')  # hooks, not access
    c = Client(); assert c.login(email='phook2@example.com', password=TEST_PASSWORD)
    payload = {
        'model_name': 'phone',  #chaned from t_n
        'number': '12',  # too short: PhoneBehaviour.before_save refuses
        'country_code': '+1'
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = wcapi_save(c, data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json(); assert_envelope(body, expect_status='fail')
    assert 'number: too short' in body.get('message','')

@pytest.mark.django_db
@pytest.mark.hooks
def test_phone_api_validate_country_code_error():
    user = User.objects.create_user(email='phook3@example.com', password=TEST_PASSWORD, name_first='P', name_last='User', username='', role='admin')  # hooks, not access
    c = Client(); assert c.login(email='phook3@example.com', password=TEST_PASSWORD)
    payload = {
        'model_name': 'phone',  #chaned from t_n
        'number': '5559999',
        'country_code': '1'  # missing leading + triggers api_validate_payload error
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = wcapi_save(c, data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json(); assert_envelope(body, expect_status='fail')
    details = (body.get('error') or {}).get('details', [])
    assert any('country_code' in e for e in details)
