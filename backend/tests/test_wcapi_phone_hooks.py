import json
import pytest
from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from apps.communications.models import Phone
from tests.utils import assert_envelope

User = get_user_model()

@pytest.mark.django_db
@pytest.mark.hooks
def test_phone_pre_and_post_hooks_success(monkeypatch):
    user = User.objects.create_user(email='phook@example.com', password='pw12345', name_first='P', name_last='User', username='')
    c = Client(); assert c.login(email='phook@example.com', password='pw12345')
    payload = {
        'model_name': 'phone',  #chaned from t_n
        'number': '5551234',
        'country_code': '+1',
        'name': 'Desk'
    }
    # enable universal validation so api_validate_payload runs
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200, resp.content
    data = assert_envelope(resp.json(), expect_status='success')
    assert any('phone saved' in m for m in data.get('messages', []))
    assert Phone.objects.filter(number='5551234').exists()

@pytest.mark.django_db
@pytest.mark.hooks
def test_phone_pre_save_rejects_short_number():
    user = User.objects.create_user(email='phook2@example.com', password='pw12345', name_first='P', name_last='User', username='')
    c = Client(); assert c.login(email='phook2@example.com', password='pw12345')
    payload = {
        'model_name': 'phone',  #chaned from t_n
        'number': '12',  # too short triggers pre_save_hook rejection
        'country_code': '+1'
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json(); assert_envelope(body, expect_status='fail')
    assert 'number: too short' in body.get('message','')

@pytest.mark.django_db
@pytest.mark.hooks
def test_phone_api_validate_country_code_error():
    user = User.objects.create_user(email='phook3@example.com', password='pw12345', name_first='P', name_last='User', username='')
    c = Client(); assert c.login(email='phook3@example.com', password='pw12345')
    payload = {
        'model_name': 'phone',  #chaned from t_n
        'number': '5559999',
        'country_code': '1'  # missing leading + triggers api_validate_payload error
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json(); assert_envelope(body, expect_status='fail')
    details = (body.get('error') or {}).get('details', [])
    assert any('country_code' in e for e in details)
