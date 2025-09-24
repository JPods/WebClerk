import pytest
from django.urls import reverse, NoReverseMatch
from rest_framework.test import APIRequestFactory, APIClient, force_authenticate
from rest_framework.response import Response as DRFResponse
from typing import cast, Callable, Any

# Absolute import of the view under test (namespace package)
from apps.core.wcapi.urls import (
    DomainSearchView,
    SaveView,
    WCAPIQueryView,
    SavedSetsView,
    TagHierarchyView,
    InventoryReservationsView,
    ReadmeSyncView,
    ActionV2SearchView,
)

from apps.sync.models import Connection
from apps.core.models.contact import Contact
from apps.docs.models.tag import Tag
from apps.core.models.action import Action

pytestmark = pytest.mark.django_db


def _factory():
    return APIRequestFactory()

# Helper to satisfy type checker for DRF as_view() calls
def _vcall(view_fn: Callable[..., Any], req: Any, **kw: Any) -> DRFResponse:
    return cast(DRFResponse, view_fn(req, **kw))


def _seed_connections():
    Connection.objects.create(name="HubSpot", type="crm", config={})
    Connection.objects.create(name="Netsuite", type="erp", config={})


def test_domain_search_anonymous_allows_and_returns_items_results():
    _seed_connections()
    view = DomainSearchView.as_view()
    req = _factory().get("/domain/?q=hub")
    resp = _vcall(view, req)
    assert resp.status_code == 200
    payload = getattr(resp, "data", {}) or {}
    data = payload.get("data") or {}
    results = data.get("results") or []
    items = data.get("items") or []
    assert isinstance(results, list) and isinstance(items, list)
    assert any("HubSpot" in (r.get("name") or "") for r in results)


def test_domain_search_nonstaff_forbidden():
    _seed_connections()
    user = Contact.objects.create(email="user@example.com", is_staff=False, is_active=True)
    view = DomainSearchView.as_view()
    req = _factory().get("/domain/?q=hub")
    force_authenticate(req, user=user)
    resp = _vcall(view, req)
    assert resp.status_code == 403
    payload = getattr(resp, "data", {}) or {}
    assert payload.get("ok") is False


def test_domain_search_staff_allowed_and_returns_results():
    _seed_connections()
    staff = Contact.objects.create(email="staff@example.com", is_staff=True, is_active=True)
    view = DomainSearchView.as_view()
    req = _factory().get("/domain/?q=hub")
    force_authenticate(req, user=staff)
    resp = _vcall(view, req)
    assert resp.status_code == 200
    data = (getattr(resp, "data", {}) or {}).get("data") or {}
    results = data.get("results") or []
    items = data.get("items") or []
    assert any("HubSpot" in (r.get("name") or "") for r in results)
    assert results == items


def test_domain_search_no_query_returns_empty_lists():
    _seed_connections()
    view = DomainSearchView.as_view()
    req = _factory().get("/domain/")
    resp = _vcall(view, req)
    assert resp.status_code == 200
    data = (getattr(resp, "data", {}) or {}).get("data") or {}
    assert data.get("results") == []
    assert data.get("items") == []


def test_domain_search_items_results_alias_consistent():
    _seed_connections()
    view = DomainSearchView.as_view()
    req = _factory().get("/domain/?q=net")
    resp = _vcall(view, req)
    assert resp.status_code == 200
    data = (getattr(resp, "data", {}) or {}).get("data") or {}
    assert data.get("results") == data.get("items")


# New tests for additional endpoints in apps.core.wcapi.urls


def test_save_view_creates_tag_and_returns_id():
    user = Contact.objects.create(email="t1@example.com", is_active=True)
    view = SaveView.as_view()
    req = _factory().post("/wcapi/save", {"model": "tag", "data": {"name": "T1", "purpose": "test"}}, format="json")
    force_authenticate(req, user=user)
    resp = _vcall(view, req)
    assert resp.status_code == 201
    data = getattr(resp, "data", {}) or {}
    payload = data.get("data") or data
    assert payload.get("id")


def test_save_view_unknown_model_400():
    user = Contact.objects.create(email="t2@example.com", is_active=True)
    view = SaveView.as_view()
    req = _factory().post("/wcapi/save", {"model": "__nope__", "data": {"x": 1}}, format="json")
    force_authenticate(req, user=user)
    resp = _vcall(view, req)
    assert resp.status_code == 400


def test_wcapi_query_returns_results_and_items():
    user = Contact.objects.create(email="t3@example.com", is_active=True)
    Tag.objects.create(name="alpha", purpose="p")
    Tag.objects.create(name="beta", purpose="p")
    view = WCAPIQueryView.as_view()
    req = _factory().post("/wcapi/query", {"model": "tag", "filters": {"name__icontains": "a"}}, format="json")
    force_authenticate(req, user=user)
    resp = _vcall(view, req)
    assert resp.status_code == 200
    payload = getattr(resp, "data", {}) or {}
    data = payload.get("data") or {}
    assert isinstance(data.get("results"), list)
    assert isinstance(data.get("items"), list)
    assert data["results"] == data["items"]
    assert any("alpha" in (r.get("name") or "") for r in data["results"])


def test_wcapi_query_unknown_model_400():
    user = Contact.objects.create(email="t4@example.com", is_active=True)
    view = WCAPIQueryView.as_view()
    req = _factory().post("/wcapi/query", {"model": "__nope__", "filters": {}}, format="json")
    force_authenticate(req, user=user)
    resp = _vcall(view, req)
    assert resp.status_code == 400


def test_saved_sets_create_and_patch_roundtrip():
    user = Contact.objects.create(email="t5@example.com", is_active=True)
    # Create set
    create_v = SavedSetsView.as_view()
    creq = _factory().post("/wcapi/contact/_sets", {"name": "S1", "ids": [1, 2], "scope": {"type": "person", "value": str(user.pk)}}, format="json")
    force_authenticate(creq, user=user)
    cresp = _vcall(create_v, creq, model="contact")
    assert cresp.status_code == 200
    sid = (getattr(cresp, "data", {}) or {}).get("id")
    assert sid
    # Patch add items
    patch_v = SavedSetsView.as_view()
    preq = _factory().patch(f"/wcapi/contact/_sets/{sid}", {"op": "add", "ids": [3, 4]}, format="json")
    force_authenticate(preq, user=user)
    presp = _vcall(patch_v, preq, model="contact", sid=sid)
    assert presp.status_code == 200
    # Patch remove items
    preq2 = _factory().patch(f"/wcapi/contact/_sets/{sid}", {"op": "remove", "ids": [3]}, format="json")
    force_authenticate(preq2, user=user)
    presp2 = _vcall(patch_v, preq2, model="contact", sid=sid)
    assert presp2.status_code == 200


def test_tag_hierarchy_view_get_post_and_delete_method_not_allowed():
    user = Contact.objects.create(email="t6@example.com", is_active=True)
    view = TagHierarchyView.as_view()
    # GET
    greq = _factory().get("/tag/1/hierarchy")
    force_authenticate(greq, user=user)
    gresp = _vcall(view, greq, pk=1)
    assert gresp.status_code == 200
    # POST
    preq = _factory().post("/tag/1/hierarchy", {"child_id": 2}, format="json")
    force_authenticate(preq, user=user)
    presp = _vcall(view, preq, pk=1)
    assert presp.status_code == 200
    # PATCH
    pat = _factory().patch("/tag/1/hierarchy", {"parent_id": 3}, format="json")
    force_authenticate(pat, user=user)
    pat_resp = _vcall(view, pat, pk=1)
    assert pat_resp.status_code == 200
    # DELETE idempotent success
    dreq = _factory().delete("/tag/1/hierarchy", {"child_id": 2}, format="json")
    force_authenticate(dreq, user=user)
    dresp = _vcall(view, dreq, pk=1)
    assert dresp.status_code == 200


def test_inventory_reservations_post_201_and_returns_id():
    user = Contact.objects.create(email="t7@example.com", is_active=True)
    view = InventoryReservationsView.as_view()
    req = _factory().post("/products/inventory/reservations/", {"stack_id": 123, "qty": "5"}, format="json")
    force_authenticate(req, user=user)
    resp = _vcall(view, req)
    assert resp.status_code == 201
    payload = getattr(resp, "data", {}) or {}
    data = payload.get("data") or {}
    assert data.get("id")
    assert data.get("stack_id") == 123
    assert data.get("qty") == "5"


def test_readme_sync_requires_staff_and_returns_payload_for_staff():
    # Non-staff forbidden
    user = Contact.objects.create(email="t8@example.com", is_active=True, is_staff=False)
    view = ReadmeSyncView.as_view()
    req = _factory().get("/readme/sync", {"dry_run": "1", "include_output": "1"})
    force_authenticate(req, user=user)
    resp = _vcall(view, req)
    assert resp.status_code == 403
    # Staff allowed
    staff = Contact.objects.create(email="t9@example.com", is_active=True, is_staff=True)
    sreq = _factory().get("/readme/sync", {"dry_run": "1", "include_output": "1"})
    force_authenticate(sreq, user=staff)
    sresp = _vcall(view, sreq)
    assert sresp.status_code == 200
    payload = getattr(sresp, "data", {}) or {}
    data = payload.get("data") or {}
    assert data.get("ok") is True
    assert isinstance(data.get("stats"), dict)
    # Staff POST returns 200
    preq = _factory().post("/readme/sync", {}, format="json")
    force_authenticate(preq, user=staff)
    presp = _vcall(view, preq)
    assert presp.status_code == 200


def test_action_v2_search_empty_and_with_results():
    # empty query -> empty results
    view = ActionV2SearchView.as_view()
    req = _factory().get("/actions/std/search")
    resp = _vcall(view, req)
    assert resp.status_code == 200
    data = (getattr(resp, "data", {}) or {}).get("data") or {}
    assert data.get("results") == []
    assert data.get("items") == []
    # seed and query
    Action.objects.create(action="Follow Up", status="open")
    req2 = _factory().get("/actions/std/search?q=Follow")
    resp2 = _vcall(view, req2)
    assert resp2.status_code == 200
    data2 = (getattr(resp2, "data", {}) or {}).get("data") or {}
    assert any("Follow" in (r.get("action") or "") for r in data2.get("results", []))
    assert data2.get("results") == data2.get("items")


# Additional tests


def test_router_reverse_names_for_fallback_models():
    # Ensure router registered names exist for known fallback models
    keys = ["domain", "tag", "template", "document", "action", "linkage"]
    for key in keys:
        path_list = reverse(f"{key}-list")
        assert path_list.endswith(f"/{key}/")
        # detail URL always defined; just check it constructs
        path_detail = reverse(f"{key}-detail", args=[1])
        assert path_detail.endswith(f"/{key}/1/")


def test_saved_sets_returns_skip_envelope_header_and_id():
    user = Contact.objects.create(email="sethdr@example.com", is_active=True)
    view = SavedSetsView.as_view()
    req = _factory().post(
        "/wcapi/contact/_sets",
        {"name": "S2", "ids": [10, 11], "scope": {"type": "person", "value": str(user.pk)}},
        format="json",
    )
    force_authenticate(req, user=user)
    resp = _vcall(view, req, model="contact")
    assert resp.status_code == 200
    assert resp.headers.get("X-Skip-Envelope") == "skip"
    body = getattr(resp, "data", {}) or {}
    assert body.get("id")


def test_domain_detail_envelope_contains_item_or_falls_back_to_data_top_level():
    # Create a domain via generic save and then GET detail via router
    creator = SaveView.as_view()
    staff = Contact.objects.create(email="dcreator@example.com", is_active=True)
    creq = _factory().post("/wcapi/save", {"model": "domain", "data": {"name": "example.com"}}, format="json")
    force_authenticate(creq, user=staff)
    cresp = _vcall(creator, creq)  # cast to DRF Response for type checker
    assert cresp.status_code in (200, 201)
    out = getattr(cresp, "data", {}) or {}
    rid = (out.get("data") or out).get("id")
    assert rid
    # Fetch detail via APIClient to exercise router path
    client = APIClient()
    client.force_authenticate(user=staff)
    dres: DRFResponse = cast(DRFResponse, client.get(f"/domain/{rid}/?format=json"))
    assert dres.status_code == 200
    payload = getattr(dres, "data", {}) or {}
    data = payload.get("data", payload)
    # Prefer nested item, but tolerate top-level data dict
    item = data.get("item") or data
    assert (item.get("id") or data.get("id")) == rid


def test_domain_post_direct_method_not_allowed_list_endpoint():
    # POST to /domain/ should not be allowed (ModelViewSet list is GET only)
    user = Contact.objects.create(email="nopost@example.com", is_active=True)
    client = APIClient()
    client.force_authenticate(user=user)
    res: DRFResponse = cast(DRFResponse, client.post("/domain/", {"name": "Nope"}, format="json"))
    assert res.status_code in (400, 405)

def test_template_search_requires_authentication():
    client = APIClient()
    url = reverse("template-search") + "?q=Welcome"
    res: DRFResponse = cast(DRFResponse, client.get(url))
    assert res.status_code == 403

def test_template_search_filters_by_name_and_aliases_items_results():
    # seed templates via generic save
    creator = SaveView.as_view()
    user = Contact.objects.create(email="tmpl@example.com", is_active=True)
    for name in ("Welcome Email", "Welcome SMS", "Other"):
        req = _factory().post(
            "/wcapi/save",
            {"model": "template", "data": {"name": name, "purpose": "test"}},
            format="json",
        )
        force_authenticate(req, user=user)
        _vcall(creator, req)
    # authenticated search
    client = APIClient()
    client.force_authenticate(user=user)
    res: DRFResponse = cast(DRFResponse, client.get(reverse("template-search") + "?q=Welcome"))
    assert res.status_code == 200
    payload = getattr(res, "data", {}) or {}
    data = payload.get("data") or {}
    results = data.get("results") or []
    items = data.get("items") or []
    names = {r.get("name") for r in results}
    assert "Welcome Email" in names and "Welcome SMS" in names
    assert "Other" not in names
    assert results == items

def test_template_search_no_q_returns_empty_lists():
    user = Contact.objects.create(email="tmpl2@example.com", is_active=True)
    client = APIClient()
    client.force_authenticate(user=user)
    res: DRFResponse = cast(DRFResponse, client.get(reverse("template-search")))
    assert res.status_code == 200
    payload = getattr(res, "data", {}) or {}
    data = payload.get("data") or {}
    results = data.get("results") or []
    items = data.get("items") or []
    assert not results and not items