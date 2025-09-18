import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.communications.models.domain import Domain
from tests.utils import assert_envelope


User = get_user_model()


@pytest.mark.django_db
def test_wcapi_save_deep_merge_prefs_and_unknown_capture():
    """
    Posts two saves to /wcapi/save/ for a Domain record:
    - first creates with nested prefs dict
    - second posts a nested prefs.ui update and an unknown top-level field
    Expects deep-merge on dicts (existing keys preserved) and unknown field capture
    into prefs.userdefined.
    """
    # Auth
    user = User.objects.create_user(
        email='deepmerge@example.com', password='pw12345', name_first='Deep', name_last='Merge', username=''
    )
    c = Client(); assert c.login(email='deepmerge@example.com', password='pw12345')

    # 1) Create with nested prefs
    payload1 = {
        'model_name': 'domain',
        'path': 'https://example.com',
        'type': 'website',
        'prefs': {
            'ui': {'sidebar': 'open'},
            'flags': {'beta': True}
        },
    }
    resp1 = c.post('/wcapi/save/', data=json.dumps(payload1), content_type='application/json')
    assert resp1.status_code == 200
    data1 = assert_envelope(resp1.json(), expect_status='success')
    domain_id = data1['id']
    v1 = data1.get('version')

    obj = Domain.objects.get(id=domain_id)
    assert obj.prefs.get('ui', {}).get('sidebar') == 'open'
    assert obj.prefs.get('flags', {}).get('beta') is True

    # 2) Update with nested prefs.ui change and an unknown top-level field
    payload2 = {
        'model_name': 'domain',
        'id': domain_id,
        'version': v1,
        'prefs': {
            'ui': {'theme': 'dark'}  # should merge into existing ui dict, preserving 'sidebar'
        },
        'unknownFieldX': 'keep-me',  # should be captured into prefs.userdefined.unknownFieldX
    }
    resp2 = c.post('/wcapi/save/', data=json.dumps(payload2), content_type='application/json')
    assert resp2.status_code == 200
    data2 = assert_envelope(resp2.json(), expect_status='success')
    v2 = data2.get('version')

    obj.refresh_from_db()
    # Deep-merge expectations
    assert obj.prefs.get('ui', {}).get('sidebar') == 'open'
    assert obj.prefs.get('ui', {}).get('theme') == 'dark'
    assert obj.prefs.get('flags', {}).get('beta') is True
    # Unknown field capture expectations
    assert obj.prefs.get('userdefined', {}).get('unknownFieldX') == 'keep-me'
    # Version should bump on update if model tracks it
    if v1 is not None and v2 is not None:
        assert v2 >= v1
