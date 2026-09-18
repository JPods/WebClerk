"""Batch delete tests using the wcapi endpoints.

Tests create records via /wcapi/save/ and delete them via /wcapi/delete/.
"""
import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.core.models import Setting
from tests.utils import assert_envelope

User = get_user_model()


@pytest.fixture
def admin_client():
    user = User.objects.create_user(
        email="batch-del-admin@example.com",
        password="pw12345",
        name_first="Batch",
        name_last="Admin",
        username="",
        is_staff=True,
        is_superuser=True,
    )
    c = Client()
    assert c.login(email="batch-del-admin@example.com", password="pw12345")
    return c


@pytest.mark.django_db
def test_batch_delete_by_ids(admin_client):
    """Create settings and delete them one at a time via /wcapi/delete/."""
    ids = []
    for i in range(3):
        resp = admin_client.post(
            "/wcapi/save/",
            data=json.dumps({
                "model_name": "setting",
                "name": f"batch_del_test_{i}",
                "purpose": "test",
                "is_active": True,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        data = assert_envelope(resp.json(), expect_status="success")
        ids.append(data["id"])
    assert all(ids)

    # Delete first two
    for rid in ids[:2]:
        del_resp = admin_client.post(
            "/wcapi/delete/",
            data=json.dumps({"model_name": "setting", "id": rid}),
            content_type="application/json",
        )
        assert del_resp.status_code == 200
        del_data = assert_envelope(del_resp.json(), expect_status="success")
        assert del_data.get("deleted") is True

    # Verify last one still exists
    assert Setting.objects.filter(id=ids[2]).exists()
    # Verify first two are gone
    assert not Setting.objects.filter(id__in=ids[:2]).exists()


@pytest.mark.django_db
def test_batch_delete_via_model_objects(admin_client):
    """Create settings via API, then verify DB-level deletion works."""
    ids = []
    for i in range(4):
        resp = admin_client.post(
            "/wcapi/save/",
            data=json.dumps({
                "model_name": "setting",
                "name": f"batch_filter_test_{i}",
                "purpose": "batch_test",
                "is_active": True,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = assert_envelope(resp.json(), expect_status="success")
        ids.append(data["id"])

    # Verify they exist
    assert Setting.objects.filter(id__in=ids).count() == 4

    # Delete all via API
    for rid in ids:
        del_resp = admin_client.post(
            "/wcapi/delete/",
            data=json.dumps({"model_name": "setting", "id": rid}),
            content_type="application/json",
        )
        assert del_resp.status_code == 200

    # Confirm none remain
    assert Setting.objects.filter(id__in=ids).count() == 0
