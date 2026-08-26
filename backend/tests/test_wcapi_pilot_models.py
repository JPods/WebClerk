"""Pilot CRUD tests using the wcapi endpoints.

Tests use the actual /wcapi/save/, /wcapi/get/, and /wcapi/delete/ endpoints
with the standard envelope contract (model_name in flat payload).
"""
import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from tests.utils import assert_envelope

User = get_user_model()


@pytest.fixture
def admin_client():
    user = User.objects.create_user(
        email="pilot-admin@example.com",
        password="pw12345",
        name_first="Pilot",
        name_last="Admin",
        username="",
        is_staff=True,
        is_superuser=True,
    )
    c = Client()
    assert c.login(email="pilot-admin@example.com", password="pw12345")
    return c


@pytest.mark.django_db
def test_contact_crud(admin_client):
    # Create
    resp = admin_client.post(
        "/wcapi/save/",
        data=json.dumps({
            "model_name": "contact",
            "name_first": "Ada",
            "name_last": "Lovelace",
            "email": "ada@example.com",
            "status": "active",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    cid = data["id"]
    assert cid is not None

    # Read
    resp = admin_client.get("/wcapi/get/", {"model_name": "contact", "id": cid})
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    record = data.get("record") or {}
    assert record.get("id") == cid

    # Delete
    resp = admin_client.post(
        "/wcapi/delete/",
        data=json.dumps({"model_name": "contact", "id": cid}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    assert data.get("deleted") is True


@pytest.mark.django_db
def test_customer_crud(admin_client):
    # Create
    resp = admin_client.post(
        "/wcapi/save/",
        data=json.dumps({
            "model_name": "customer",
            "company": "Pilot Customer Co",
            "status": "active",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    oid = data["id"]
    assert oid is not None

    # Read
    resp = admin_client.get("/wcapi/get/", {"model_name": "customer", "id": oid})
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    record = data.get("record") or {}
    assert record.get("id") == oid

    # Delete
    resp = admin_client.post(
        "/wcapi/delete/",
        data=json.dumps({"model_name": "customer", "id": oid}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    assert data.get("deleted") is True


@pytest.mark.django_db
def test_setting_crud(admin_client):
    # Create
    resp = admin_client.post(
        "/wcapi/save/",
        data=json.dumps({
            "model_name": "setting",
            "name": "pilot_test_setting",
            "purpose": "test",
            "is_active": True,
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    sid = data["id"]
    assert sid is not None

    # Read
    resp = admin_client.get("/wcapi/get/", {"model_name": "setting", "id": sid})
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    record = data.get("record") or {}
    assert record.get("id") == sid

    # Delete
    resp = admin_client.post(
        "/wcapi/delete/",
        data=json.dumps({"model_name": "setting", "id": sid}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    assert data.get("deleted") is True
