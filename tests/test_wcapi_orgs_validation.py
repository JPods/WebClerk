import json
import pytest
from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from apps.orgs.models import OrgBase, OrgType
from tests.utils import assert_envelope

User = get_user_model()

@pytest.mark.django_db
def test_wcapi_org_create_validation_enabled_success():
    user = User.objects.create_user(username='valsucc@example.com', email='valsucc@example.com', password='pw12345', name_first='Val', name_last='User')
    c = Client(); assert c.login(email='valsucc@example.com', password='pw12345')
    payload = {
        'model_name': 'org',  #chaned from t_n
        'org_type': 'customer',
        'display_name': 'Valid Co',
        'status': 'active'
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200, resp.content
    data = assert_envelope(resp.json(), expect_status='success')
    assert OrgBase.objects.filter(display_name='Valid Co').exists()

@pytest.mark.django_db
def test_wcapi_org_create_validation_enabled_failure():
    user = User.objects.create_user(username='valfail@example.com', email='valfail@example.com', password='pw12345', name_first='Val', name_last='User')
    c = Client(); assert c.login(email='valfail@example.com', password='pw12345')
    # invalid org_type
    payload = {
        'model_name': 'org',  #chaned from t_n
        'org_type': 'notatype',
        'display_name': 'Bad Co',
        'status': 'active'
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'Validation failed' in body.get('message','')
    details = (body.get('error') or {}).get('details', [])
    assert any('org_type' in e for e in details)

@pytest.mark.django_db
def test_wcapi_org_partial_update_validation_failure():
    user = User.objects.create_user(username='valpartial@example.com', email='valpartial@example.com', password='pw12345', name_first='Val', name_last='User')
    c = Client(); assert c.login(email='valpartial@example.com', password='pw12345')
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Patch Co', status='active')
    # supply invalid domains list entry (missing dot TLD)
    payload = {
        'model_name': 'org',  #chaned from t_n
        'id': org.id,
        'version': org.version,
        'domains': [{'domain': 'invalid_domain'}]
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    details = (body.get('error') or {}).get('details', [])
    assert any('domains' in e for e in details)

@pytest.mark.django_db
def test_wcapi_org_partial_update_validation_success():
    user = User.objects.create_user(username='valpartial2@example.com', email='valpartial2@example.com', password='pw12345', name_first='Val', name_last='User')
    c = Client(); assert c.login(email='valpartial2@example.com', password='pw12345')
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Patch Co2', status='active')
    payload = {
        'model_name': 'org',  #chaned from t_n
        'id': org.id,
        'version': org.version,
        'domains': [{'domain': 'example.com'}]
    }
    with override_settings(UNIVERSAL_API_VALIDATE=True):
        resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200, resp.content
    org.refresh_from_db()
    assert isinstance(org.domains, list) and org.domains[0]['domain'] == 'example.com'
