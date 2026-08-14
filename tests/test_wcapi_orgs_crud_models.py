import json
from io import StringIO
from datetime import timedelta
import pytest
from django.core.management import call_command
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.orgs.models import OrgBase, OrgType
from apps.core.models import Setting
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


@pytest.mark.django_db
def test_wcapi_get_supports_keyword_param(client):
    user = User.objects.create_user(
        email="keyword-search@example.com",
        password="pw12345",
        name_first="Keyword",
        name_last="Tester",
        username="",
    )
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client.force_login(user)

    target = OrgBase.objects.create(
        company="zzkwtest-west-supply",
        org_type=OrgType.CUSTOMER,
        status="active",
    )
    OrgBase.objects.create(
        company="different-east-supply",
        org_type=OrgType.CUSTOMER,
        status="active",
    )

    baseline = client.get(
        "/wcapi/get/",
        {
            "model_name": "customer",
            "limit": 50,
        },
    )
    assert baseline.status_code == 200
    baseline_data = assert_envelope(baseline.json(), expect_status="success")
    assert len(baseline_data.get("results") or []) >= 2

    resp = client.get(
        "/wcapi/get/",
        {
            "model_name": "customer",
            "keyword": "zzkwtest",
            "limit": 50,
        },
    )

    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    results = data.get("results") or []
    result_ids = {row.get("id") for row in results if isinstance(row, dict)}

    assert target.id in result_ids


@pytest.mark.django_db
def test_wcapi_get_applies_saved_search_for_matching_role(client):
    user = User.objects.create_user(
        email="saved-search-role@example.com",
        password="pw12345",
        name_first="Role",
        name_last="Member",
        role="sales",
        username="",
    )
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client.force_login(user)

    target = OrgBase.objects.create(company="zzsaved-role-001", org_type=OrgType.CUSTOMER, status="active")
    OrgBase.objects.create(company="zzsaved-role-002", org_type=OrgType.CUSTOMER, status="inactive")

    Setting.objects.create(
        name="sales_active_customers",
        purpose="wc:search",
        parent_model="customer",
        role="sales",
        data={
            "keyword": "zzsaved-role",
            "filters": {"status": "active"},
            "ordering": "company",
        },
        is_active=True,
    )

    resp = client.get(
        "/wcapi/get/",
        {
            "model_name": "customer",
            "saved_search": "sales_active_customers",
            "limit": 50,
        },
    )

    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    results = data.get("results") or []
    result_ids = {row.get("id") for row in results if isinstance(row, dict)}

    assert target.id in result_ids
    query_echo = data.get("query") or {}
    assert query_echo.get("saved_search", {}).get("name") == "sales_active_customers"
    assert query_echo.get("filters", {}).get("status") == "active"


@pytest.mark.django_db
def test_wcapi_get_saved_search_rejects_other_roles(client):
    user = User.objects.create_user(
        email="saved-search-mismatch@example.com",
        password="pw12345",
        name_first="Other",
        name_last="Role",
        role="support",
        username="",
    )
    client.force_login(user)

    Setting.objects.create(
        name="sales_only_search",
        purpose="wc:search",
        parent_model="customer",
        role="sales",
        data={"keyword": "zzsaved-role"},
        is_active=True,
    )

    resp = client.get(
        "/wcapi/get/",
        {
            "model_name": "customer",
            "saved_search": "sales_only_search",
        },
    )

    assert resp.status_code == 403
    body = resp.json()
    assert_envelope(body, expect_status="fail")
    assert body.get("error", {}).get("code") == "saved_search_forbidden"


@pytest.mark.django_db
def test_wcapi_save_saved_search_requires_admin(client):
    user = User.objects.create_user(
        email="saved-search-writer@example.com",
        password="pw12345",
        name_first="Writer",
        name_last="User",
        role="user",
        username="",
    )
    client.force_login(user)

    resp = client.post(
        "/wcapi/save/",
        data=json.dumps(
            {
                "model_name": "setting",
                "name": "non_admin_saved_search",
                "purpose": "wc:search",
                "parent_model": "customer",
                "role": "sales",
                "data": {"keyword": "acme"},
            }
        ),
        content_type="application/json",
    )

    assert resp.status_code == 403
    body = resp.json()
    assert_envelope(body, expect_status="fail")
    assert body.get("error", {}).get("code") == "saved_search_admin_required"


@pytest.mark.django_db
def test_wcapi_save_saved_search_allows_admin(client):
    user = User.objects.create_user(
        email="saved-search-admin@example.com",
        password="pw12345",
        name_first="Admin",
        name_last="Writer",
        role="admin",
        username="",
        is_staff=True,
        is_superuser=True,
    )
    client.force_login(user)

    resp = client.post(
        "/wcapi/save/",
        data=json.dumps(
            {
                "model_name": "setting",
                "name": "admin_saved_search",
                "purpose": "wc:search",
                "parent_model": "customer",
                "role": "sales",
                "data": {"keyword": "acme", "filters": {"status": "active"}},
            }
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    data = assert_envelope(body, expect_status="success")
    setting_id = data.get("id") or data.get("record", {}).get("id")
    assert setting_id is not None

    saved = Setting.objects.get(id=setting_id)
    assert saved.purpose == "wc:search"
    assert saved.parent_model == "customer"


@pytest.mark.django_db
def test_wcapi_search_presets_lists_role_visible_and_global(client):
    user = User.objects.create_user(
        email="search-presets-sales@example.com",
        password="pw12345",
        name_first="Sales",
        name_last="User",
        role="sales",
        username="",
    )
    client.force_login(user)

    visible_sales = Setting.objects.create(
        name="sales_pipeline",
        purpose="wc:search",
        parent_model="customer",
        role="sales",
        data={"keyword": "pipeline"},
        is_active=True,
    )
    visible_global = Setting.objects.create(
        name="global_customers",
        purpose="wc:search",
        parent_model="customer",
        role="all",
        data={"keyword": "customer"},
        is_active=True,
    )
    hidden_support = Setting.objects.create(
        name="support_only",
        purpose="wc:search",
        parent_model="customer",
        role="support",
        data={"keyword": "ticket"},
        is_active=True,
    )

    resp = client.get("/wcapi/search-presets/", {"model_name": "customer"})
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    result_ids = {row.get("id") for row in (data.get("results") or []) if isinstance(row, dict)}

    assert visible_sales.id in result_ids
    assert visible_global.id in result_ids
    assert hidden_support.id not in result_ids


@pytest.mark.django_db
def test_wcapi_search_presets_admin_sees_all_roles(client):
    admin = User.objects.create_user(
        email="search-presets-admin@example.com",
        password="pw12345",
        name_first="Admin",
        name_last="User",
        role="admin",
        username="",
        is_staff=True,
        is_superuser=True,
    )
    client.force_login(admin)

    support_setting = Setting.objects.create(
        name="support_only_admin_visible",
        purpose="wc:search",
        parent_model="customer",
        role="support",
        data={"keyword": "support"},
        is_active=True,
    )

    resp = client.get("/wcapi/search-presets/", {"model_name": "customer"})
    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    result_ids = {row.get("id") for row in (data.get("results") or []) if isinstance(row, dict)}

    assert support_setting.id in result_ids


@pytest.mark.django_db
def test_wcapi_get_saved_search_uses_request_keyword_and_period_params(client):
    user = User.objects.create_user(
        email="saved-search-request-keyword@example.com",
        password="pw12345",
        name_first="Preset",
        name_last="Runtime",
        username="",
    )
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client.force_login(user)

    inside = OrgBase.objects.create(company="zzruntime-west", org_type=OrgType.CUSTOMER, status="active")
    outside_window = OrgBase.objects.create(company="zzruntime-west", org_type=OrgType.CUSTOMER, status="active")
    wrong_keyword = OrgBase.objects.create(company="other-east", org_type=OrgType.CUSTOMER, status="active")

    start_ms = int(timezone.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    end_ms = start_ms + 86_400_000 - 1
    prior_ms = start_ms - 86_400_000

    inside.dt_created = start_ms + 1000
    inside.save(update_fields=["dt_created"])
    outside_window.dt_created = prior_ms
    outside_window.save(update_fields=["dt_created"])
    wrong_keyword.dt_created = start_ms + 2000
    wrong_keyword.save(update_fields=["dt_created"])

    Setting.objects.create(
        name="runtime_customer_search",
        purpose="wc:search",
        parent_model="customer",
        role="all",
        data={
            "request_keyword": "company_token",
            "search_fields": ["display_name"],
            "request_filters": {
                "begin": {"field": "dt_created", "lookup": "gte"},
                "end": {"field": "dt_created", "lookup": "lte"},
            },
        },
        is_active=True,
    )

    resp = client.get(
        "/wcapi/get/",
        {
            "model_name": "customer",
            "saved_search": "runtime_customer_search",
            "company_token": "zzruntime",
            "begin": str(start_ms),
            "end": str(end_ms),
            "limit": 50,
        },
    )

    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    result_ids = {row.get("id") for row in (data.get("results") or []) if isinstance(row, dict)}

    assert inside.id in result_ids
    assert outside_window.id not in result_ids
    assert wrong_keyword.id not in result_ids
    assert data.get("query", {}).get("request_keyword") == "zzruntime"


@pytest.mark.django_db
def test_wcapi_get_saved_search_uses_relative_period_defaults(client):
    user = User.objects.create_user(
        email="saved-search-relative-period@example.com",
        password="pw12345",
        name_first="Relative",
        name_last="Period",
        username="",
    )
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client.force_login(user)

    now = timezone.localtime(timezone.now())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month = (month_start - timedelta(days=1)).replace(day=1)

    current = OrgBase.objects.create(company="zzcurrent-month", org_type=OrgType.CUSTOMER, status="active")
    previous = OrgBase.objects.create(company="zzprevious-month", org_type=OrgType.CUSTOMER, status="active")

    current.dt_created = int((month_start + timedelta(hours=1)).timestamp() * 1000)
    current.save(update_fields=["dt_created"])
    previous.dt_created = int(previous_month.timestamp() * 1000)
    previous.save(update_fields=["dt_created"])

    Setting.objects.create(
        name="current_month_customers",
        purpose="wc:search",
        parent_model="customer",
        role="all",
        data={
            "relative_period": {"field": "dt_created", "preset": "current_month"},
            "search_fields": ["display_name"],
            "keyword": "zz",
        },
        is_active=True,
    )

    resp = client.get(
        "/wcapi/get/",
        {
            "model_name": "customer",
            "saved_search": "current_month_customers",
            "limit": 50,
        },
    )

    assert resp.status_code == 200
    data = assert_envelope(resp.json(), expect_status="success")
    result_ids = {row.get("id") for row in (data.get("results") or []) if isinstance(row, dict)}

    assert current.id in result_ids
    assert previous.id not in result_ids


@pytest.mark.django_db
def test_seed_search_presets_command_is_idempotent():
    output = StringIO()
    call_command("seed_search_presets", stdout=output)
    first_run = output.getvalue()

    assert "created=" in first_run
    assert Setting.objects.filter(purpose="wc:search", parent_model="invoice", name="current_month").exists()
    assert Setting.objects.filter(purpose="wc:search", parent_model="action", name="assigned_to_is_active_priority").exists()

    count_after_first = Setting.objects.filter(purpose="wc:search", role="all").count()

    output = StringIO()
    call_command("seed_search_presets", stdout=output)
    second_run = output.getvalue()
    count_after_second = Setting.objects.filter(purpose="wc:search", role="all").count()

    assert "updated=" in second_run
    assert count_after_second == count_after_first
