import secrets

# Generated per run — no password literal in the repository.
TEST_PASSWORD = secrets.token_urlsafe(16)

import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.orgs.models import OrgBase, OrgType
from tests.utils import assert_envelope

User = get_user_model()

@pytest.mark.django_db
def test_wcapi_save_create_org():
    # An entitled user. Rewritten 2026-09-20: this used a role-less account, whose edit
    # enumeration does not name `company`, so the field was ignored (Bill: "the back end
    # should never read it as being there") and the insert then failed the
    # org_display_name_not_empty constraint — reported as "Integrity error". The
    # requirement worth keeping is that a create lands, not that anyone may make one.
    user = User.objects.create_superuser(email='saveorg@example.com', password=TEST_PASSWORD)
    c = Client(); assert c.login(email='saveorg@example.com', password=TEST_PASSWORD)
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
    # Entitled, for the same reason: a role that cannot edit `company` cannot rename one,
    # and the rename was being ignored while the response still said success. The
    # requirement worth keeping is that an update honours the version it was given.
    user = User.objects.create_superuser(email='saveorg2@example.com', password=TEST_PASSWORD)
    c = Client(); assert c.login(email='saveorg2@example.com', password=TEST_PASSWORD)
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
