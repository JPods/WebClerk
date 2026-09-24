import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.communications.models.domain import Domain
from tests.utils import assert_envelope
import secrets
from tests.utils import wcapi_save

# Generated per run — no password literal in the repository.
TEST_PASSWORD = secrets.token_urlsafe(16)


User = get_user_model()


@pytest.mark.django_db
def test_wcapi_save_deep_merge_prefs_and_unknown_capture():
    """A save deep-merges the envelope leaves the role may write, and ignores the rest.

    Before the one field authority (Bill, 2026-09-20/23: "if it is not enumerated as edit,
    the back end should never read it"), this test expected an untyped prefs.ui and an
    unknown top-level field to be stored — the second captured into prefs.userdefined.
    Neither is a leaf any role can be given, so both are ignored now.
    """
    user = User.objects.create_user(
        email='deepmerge@example.com', password=TEST_PASSWORD, name_first='Deep', name_last='Merge', username='', role='admin'  # tests merging, not access
    )
    c = Client(); assert c.login(email='deepmerge@example.com', password=TEST_PASSWORD)

    resp1 = wcapi_save(c, data=json.dumps({
        'model_name': 'domain', 'path': 'https://example.com', 'type': 'website',
        'prefs': {'pinned': True, 'tags': ['ops']},
    }), content_type='application/json')
    assert resp1.status_code == 200, resp1.content
    data1 = assert_envelope(resp1.json(), expect_status='success')
    obj = Domain.objects.get(id=data1['id'])
    assert obj.prefs['pinned'] is True and obj.prefs['tags'] == ['ops']

    resp2 = wcapi_save(c, data=json.dumps({
        'model_name': 'domain', 'id': obj.id, 'version': data1.get('version'),
        'prefs': {'pinned': False, 'ui': {'theme': 'dark'}},
        'unknownFieldX': 'ignored',
    }), content_type='application/json')
    assert resp2.status_code == 200, resp2.content

    obj.refresh_from_db()
    assert obj.prefs['pinned'] is False, 'the written leaf changed'
    assert obj.prefs['tags'] == ['ops'], 'the leaf not sent was kept (deep merge)'
    assert 'ui' not in obj.prefs, 'an untyped branch is not a leaf any role may write'
    assert 'unknownFieldX' not in (obj.prefs.get('userdefined') or {})
