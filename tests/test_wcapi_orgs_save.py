import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.orgs.models import OrgBase, OrgType

User = get_user_model()

@pytest.mark.django_db
def test_wcapi_save_create_org():
    user = User.objects.create_user(email='saveorg@example.com', password='pw12345', name_first='Saver', name_last='User', username='')
    c = Client(); assert c.login(email='saveorg@example.com', password='pw12345')
    payload = {
        'table_name': 'orgs',
        'org_type': 'customer',
        'display_name': 'Save Created Co',
        'status': 'active'
    }
    resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    body = resp.json(); assert body['status'] == 'success'
    org = OrgBase.objects.get(id=body['data']['id'])
    assert org.display_name == 'Save Created Co'

@pytest.mark.django_db
def test_wcapi_save_update_org_with_version():
    user = User.objects.create_user(email='saveorg2@example.com', password='pw12345', name_first='Saver', name_last='User', username='')
    c = Client(); assert c.login(email='saveorg2@example.com', password='pw12345')
    org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Update Co', status='active')
    v = org.version
    payload = {
        'table_name': 'orgs',
        'id': org.id,
        'version': v,
        'display_name': 'Update Co Renamed'
    }
    resp = c.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    org.refresh_from_db()
    assert org.display_name == 'Update Co Renamed'
