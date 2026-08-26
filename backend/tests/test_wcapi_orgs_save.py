import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.orgs.models import OrgBase, OrgType
from tests.utils import assert_envelope

User = get_user_model()

@pytest.mark.django_db
def test_wcapi_save_create_org():
    user = User.objects.create_user(email='saveorg@example.com', password='pw12345', name_first='Saver', name_last='User', username='')
    c = Client(); assert c.login(email='saveorg@example.com', password='pw12345')
    payload = {
        'model_name': 'customer',
        'company': 'Save Created Co',
        'status': 'active'
    }
    resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status='success')
    org = OrgBase.objects.get(id=data['id'])
    assert org.company == 'Save Created Co'

@pytest.mark.django_db
def test_wcapi_save_update_org_with_version():
    user = User.objects.create_user(email='saveorg2@example.com', password='pw12345', name_first='Saver', name_last='User', username='')
    c = Client(); assert c.login(email='saveorg2@example.com', password='pw12345')
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company='Update Co', status='active')
    v = org.version
    payload = {
        'model_name': 'customer',
        'id': org.id,
        'version': v,
        'company': 'Update Co Renamed'
    }
    resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    assert_envelope(resp.json(), expect_status='success')
    org.refresh_from_db()
    assert org.company == 'Update Co Renamed'
