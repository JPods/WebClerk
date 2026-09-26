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
def test_wcapi_save_deep_merges_the_leaves_and_refuses_a_key_that_is_no_field():
    """A save deep-merges the envelope leaves the role may write and ignores an envelope
    branch no role is given (Bill, 2026-09-20: "if it is not enumerated as edit, the back
    end should never read it"). A top-level key that is no field of the model is refused
    with coaching, never dropped (Bill, 2026-09-25).
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

    refused = wcapi_save(c, data=json.dumps({
        'model_name': 'domain', 'id': obj.id, 'version': data1.get('version'),
        'prefs': {'pinned': False}, 'unknownFieldX': 'x',
    }), content_type='application/json')
    assert refused.status_code == 400, refused.content
    assert refused.json()['error']['code'] == 'unknown_field'
    assert 'unknownFieldX' in refused.json()['message']
    obj.refresh_from_db()
    assert obj.prefs['pinned'] is True, 'a refused save writes nothing'

    resp2 = wcapi_save(c, data=json.dumps({
        'model_name': 'domain', 'id': obj.id, 'version': data1.get('version'),
        'prefs': {'pinned': False, 'ui': {'theme': 'dark'}},
    }), content_type='application/json')
    assert resp2.status_code == 200, resp2.content

    obj.refresh_from_db()
    assert obj.prefs['pinned'] is False, 'the written leaf changed'
    assert obj.prefs['tags'] == ['ops'], 'the leaf not sent was kept (deep merge)'
    assert 'ui' not in obj.prefs, 'an untyped branch is not a leaf any role may write'
