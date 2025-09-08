import pytest
pytestmark = pytest.mark.skip(reason='duplicate; consolidated into tests/test_model_name_endpoints.py')
from typing import cast
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.test import APIClient


@pytest.fixture()
def user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username='admin_tester', email='admin@test.local', password='pass'
    )


@pytest.mark.django_db
def test_model_name_list_and_detail(user):
    c = APIClient()
    c.force_authenticate(user=user)

    resp = cast(Response, c.get('/wcapi/model_name/list/'))
    assert resp.status_code == 200

    resp = cast(Response, c.get('/wcapi/model_name/list/'))
    assert resp.status_code == 200

    resp2 = cast(Response, c.get('/wcapi/model_name/detail/?model_name=proposal_line'))
    assert resp2.status_code == 200

    resp2 = cast(Response, c.get('/wcapi/model_name/detail/?model_name=proposal_line'))
    assert resp2.status_code == 200

    data = (resp2.data or {}).get('data')
    assert isinstance(data, dict), f"Expected response.data['data'] to be a dict, got {type(data).__name__}"
    payload = data.get('model')
    assert isinstance(payload, dict), f"Expected 'model' to be a dict in response, got {type(payload).__name__ if payload is not None else 'None'}"
    assert payload.get('model_name') == 'proposal_line'
    assert 'fields' in payload and isinstance(payload.get('fields'), dict)


@pytest.mark.django_db
def test_settings_normalizes_plural_model_name(user):
    c = APIClient()
    c.force_authenticate(user=user)

    bad = {
        "purpose": "view_edit",
        "model_name": "sales_order_lines",
        "is_active": True,
        "data": {"ADMIN": {"view": ["id"], "edit": []}},
    }

    resp = cast(Response, c.post('/settings/', bad, format='json'))
    assert resp.status_code in (200, 201)

    got = (resp.data or {}).get('data', {})
    assert isinstance(got, dict), f"Expected response.data['data'] to be a dict, got {type(got).__name__}"
    assert got.get('model_name') == 'sales_order_line'
