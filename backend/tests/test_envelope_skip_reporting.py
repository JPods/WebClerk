import os, json
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_envelope_skip_registry_exposed(client, settings):
    """Ensure middleware records skip reasons during tests and we can introspect them.

    This gives visibility when running pytest -vv about any responses that were
    NOT auto-enveloped (raw escape, exempt paths, etc.).
    """
    # Trigger a known exempt path (/admin/) and a raw query on an API path
    client.get('/admin/login/?next=/admin/')
    api_path = '/domain/'
    r = client.get(api_path + '?raw=1')  # raw bypass now disabled by default
    body = r.json()
    assert body.get('status') in ('success','fail','error')  # still enveloped; 401 now 'fail'
    # Import registry from middleware
    from common.middleware import ENVELOPE_SKIPS
    assert any(s['reason'] == 'exempt_path' for s in ENVELOPE_SKIPS)
    # raw_query should never appear now that the opt-out path is removed
    assert not any(s['reason'] == 'raw_query' for s in ENVELOPE_SKIPS)
