import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.orgs.models import OrgBase, OrgType
from tests.utils import assert_envelope

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model_name, org_type",
    [
        ("org", OrgType.CUSTOMER),
        ("customer", OrgType.CUSTOMER),
        ("vendor", OrgType.VENDOR),
        ("rep", OrgType.REP),
        ("employee", OrgType.EMPLOYEE),
        ("manufacturer", OrgType.MANUFACTURER),
    ],
)
def test_wcapi_org_model_crud(model_name, org_type):
    user = User.objects.create_user(
        email=f"org-{model_name}@example.com",
        password="pw12345",
        name_first="Org",
        name_last="User",
        username="",
    )
    client = Client()
    assert client.login(email=user.email, password="pw12345")

    payload = {
        "model_name": model_name,
        "company": f"{model_name} co",
        "status": "active",
    }
    if model_name == "org":
        payload["org_type"] = org_type

    resp = client.post("/wcapi/save/", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    record_id = data["id"]

    org = OrgBase.objects.get(pk=record_id)
    assert org.company == f"{model_name} co"
    if model_name == "org":
        assert org.org_type == org_type

    # GET detail
    resp = client.get("/wcapi/get/", {"model_name": model_name, "id": record_id})
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    record = data.get("record") or {}
    assert record.get("id") == record_id

    # Update record
    update_payload = {
        "model_name": model_name,
        "id": record_id,
        "company": f"{model_name} co updated",
    }
    resp = client.post("/wcapi/save/", data=json.dumps(update_payload), content_type="application/json")
    assert resp.status_code == 200
    assert_envelope(resp.json(), expect_status="success")

    org.refresh_from_db()
    assert org.company == f"{model_name} co updated"

    # Delete part of record (status)
    delete_field_payload = {
        "model_name": model_name,
        "id": record_id,
        "status": {"mode": "delete"},
    }
    resp = client.post("/wcapi/save/", data=json.dumps(delete_field_payload), content_type="application/json")
    assert resp.status_code == 200
    assert_envelope(resp.json(), expect_status="success")

    org.refresh_from_db()
    assert org.status in (None, "")

    # Delete record
    resp = client.post(
        "/wcapi/delete/",
        data=json.dumps({"model_name": model_name, "id": record_id}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    assert data.get("deleted") is True
