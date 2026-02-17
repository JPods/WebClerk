import pytest
import json
from typing import Any, Dict, cast
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.test import APIClient

@pytest.fixture()
def user(db):
    User = get_user_model()
    # Superuser to ensure permissions for settings endpoints
    return User.objects.create_superuser(
        username='admin_tester', email='admin@test.local', password='pass'
    )

@pytest.mark.django_db
def test_model_name_list_and_detail(user):
    c = APIClient()
    c.force_authenticate(user=user)

    # list
    resp = cast(Response, c.get('/wcapi/model_name/list/'))
    assert resp.status_code == 200

    # call again to ensure stable/idempotent response
    resp = cast(Response, c.get('/wcapi/model_name/list/'))
    assert resp.status_code == 200

    # detail
    resp2 = cast(Response, c.get('/wcapi/model_name/detail/?model_name=proposal_line'))
    assert resp2.status_code == 200

    # repeat detail to ensure stability
    resp2 = cast(Response, c.get('/wcapi/model_name/detail/?model_name=proposal_line'))
    assert resp2.status_code == 200

    # envelope shape and payload
    assert isinstance(resp2.data, dict)
    data = resp2.data.get('data')
    assert isinstance(data, dict)
    payload = cast(Dict[str, Any], data.get('model'))
    assert isinstance(payload, dict)
    assert payload.get('model_name') == 'proposal_line'
    assert 'fields' in payload and isinstance(payload['fields'], dict)

@pytest.mark.django_db
def test_settings_normalizes_plural_model_name(user):
    c = APIClient()
    c.force_authenticate(user=user)

    bad = {
        "purpose": "view_edit",
        "model_name": "order_lines",  # plural on purpose
        "is_active": True,
        "data": {"ADMIN": {"view": ["id"], "edit": []}},
    }

    # Even if plural provided, API normalizes to singular and accepts; ensure singular stored
    resp = cast(Response, c.post('/settings/', bad, format='json'))
    assert resp.status_code in (200, 201)

    # repeat to ensure idempotence/acceptance
    resp = cast(Response, c.post('/settings/', bad, format='json'))
    assert resp.status_code in (200, 201)

    # envelope and normalized field
    assert isinstance(resp.data, dict)
    got_data = resp.data.get('data')
    assert isinstance(got_data, dict)
    assert got_data.get('model_name') == 'order_line'
