"""Tests for RestToWcapiMiddleware — path parsing and redirect behaviour.

Related files:
  wc3  common/middleware/rest_redirect.py     – middleware under test
  wc3  readmes/03-wcapi-gateway.md            – gateway docs & REST→wcapi mapping table
  r25  src/api/restToWcapi.ts                 – client-side REST→wcapi converter
  r25  src/pages/tools/WhitelistTester.tsx     – interactive tester (includes REST redirect presets)
"""
import pytest
from django.test import RequestFactory, override_settings

from common.middleware.rest_redirect import (
    RestToWcapiMiddleware,
    _parse_rest_path,
    _build_wcapi_url,
)


# ── Unit tests for _parse_rest_path ──────────────────────────────────────────

class TestParseRestPath:
    """Verify model_name + id extraction from various REST URL shapes."""

    @pytest.mark.parametrize("path, expected_model, expected_id", [
        # Simple plural → singular
        ("/api/invoices/", "invoice", None),
        ("/api/contacts/", "contact", None),
        ("/api/customers/", "customer", None),
        ("/api/vendors/", "vendor", None),

        # With numeric ID
        ("/api/invoices/123/", "invoice", "123"),
        ("/api/contacts/42/", "contact", "42"),

        # App-namespaced paths
        ("/api/orgs/customers/", "customer", None),
        ("/api/orgs/customers/7/", "customer", "7"),
        ("/api/transactions/invoices/", "invoice", None),
        ("/api/transactions/invoices/123/", "invoice", "123"),
        ("/api/transactions/orders/", "order", None),
        ("/api/transactions/orders/99/", "order", "99"),
        ("/api/products/items/", "item", None),
        ("/api/core/contacts/", "contact", None),

        # Trailing action verbs (list / detail) are stripped
        ("/api/core/contacts/list", "contact", None),
        ("/api/orgs/customers/detail", "customer", None),

        # Deeply namespaced
        ("/api/transactions/invoices/123/", "invoice", "123"),

        # Hyphenated resources → snake_case
        ("/api/products/bill-of-materials/", "bill_of_material", None),
        ("/api/accounts/gl-accounts/", "gl_account", None),

        # Already singular
        ("/api/invoice/", "invoice", None),
        ("/api/invoice/5/", "invoice", "5"),

        # Edge: categories → category (ies → y)
        ("/api/categories/", "category", None),
        ("/api/products/categories/", "category", None),

        # Edge: addresses → address (ses rule strips "es")
        ("/api/addresses/", "address", None),

        # Action verbs after ID are NOT parsed (should return None)
        ("/api/transactions/orders/5/convert-to-invoice/", None, None),
        ("/api/transactions/proposals/3/convert-to-order/", None, None),
        ("/api/transactions/purchases/1/receive-goods/", None, None),

        # Unparseable
        ("/api/", None, None),
    ])
    def test_parsing(self, path, expected_model, expected_id):
        model, rid = _parse_rest_path(path)
        assert model == expected_model, f"model for {path}"
        assert rid == expected_id, f"id for {path}"


# ── Unit tests for _build_wcapi_url ──────────────────────────────────────────

class TestBuildWcapiUrl:
    def test_get_list(self):
        url = _build_wcapi_url("GET", "invoice", None, "")
        assert url == "/wcapi/get/?model_name=invoice"

    def test_get_detail(self):
        url = _build_wcapi_url("GET", "invoice", "123", "")
        assert url == "/wcapi/get/?model_name=invoice&id=123"

    def test_get_preserves_querystring(self):
        url = _build_wcapi_url("GET", "contact", None, "search=acme&limit=10")
        assert "model_name=contact" in url
        assert "search=acme" in url
        assert "limit=10" in url
        assert url.startswith("/wcapi/get/?")

    def test_post_goes_to_save(self):
        url = _build_wcapi_url("POST", "order", None, "")
        assert url.startswith("/wcapi/save/")

    def test_delete_goes_to_delete(self):
        url = _build_wcapi_url("DELETE", "order", "5", "")
        assert url.startswith("/wcapi/delete/")
        assert "id=5" in url


# ── Integration tests for the middleware ─────────────────────────────────────

@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def noop_response():
    """A no-op get_response that returns a plain 200."""
    from django.http import HttpResponse
    return lambda request: HttpResponse("OK", status=200)


class TestRestToWcapiMiddleware:
    def test_redirect_simple_list(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.get("/api/invoices/")
        response = mw(request)
        assert response.status_code == 301
        assert response["Location"] == "/wcapi/get/?model_name=invoice"

    def test_redirect_detail(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.get("/api/transactions/invoices/123/")
        response = mw(request)
        assert response.status_code == 301
        assert "model_name=invoice" in response["Location"]
        assert "id=123" in response["Location"]

    def test_redirect_with_existing_qs(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.get("/api/contacts/?search=acme&limit=20")
        response = mw(request)
        assert response.status_code == 301
        loc = response["Location"]
        assert "model_name=contact" in loc
        assert "search=acme" in loc
        assert "limit=20" in loc

    def test_non_api_path_passes_through(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.get("/wcapi/get/?model_name=invoice")
        response = mw(request)
        assert response.status_code == 200  # no redirect

    def test_admin_path_passes_through(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.get("/admin/")
        response = mw(request)
        assert response.status_code == 200

    @override_settings(REST_REDIRECT_ENABLED=False)
    def test_disabled_passes_through(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.get("/api/invoices/")
        response = mw(request)
        assert response.status_code == 200  # middleware skipped

    def test_post_redirects_to_save(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.post("/api/orgs/customers/", content_type="application/json")
        response = mw(request)
        assert response.status_code == 301
        assert "/wcapi/save/" in response["Location"]
        assert "model_name=customer" in response["Location"]

    def test_delete_redirects_to_delete(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.delete("/api/transactions/orders/42/")
        response = mw(request)
        assert response.status_code == 301
        assert "/wcapi/delete/" in response["Location"]
        assert "model_name=order" in response["Location"]
        assert "id=42" in response["Location"]

    def test_core_contacts_list(self, rf, noop_response):
        """The example from the gateway docs: /api/core/contacts/list."""
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.get("/api/core/contacts/list")
        response = mw(request)
        assert response.status_code == 301
        assert "model_name=contact" in response["Location"]

    # ── Exempt paths pass through ─────────────────────────────────────────

    def test_exempt_transfers(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.post("/api/transactions/transfers/validate/")
        response = mw(request)
        assert response.status_code == 200  # not redirected

    def test_exempt_inventory(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.post("/api/transactions/inventory/reserve/")
        response = mw(request)
        assert response.status_code == 200

    def test_exempt_payment_webhooks(self, rf, noop_response):
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.post("/api/transactions/payments/webhooks/stripe/")
        response = mw(request)
        assert response.status_code == 200

    def test_action_verb_not_redirected(self, rf, noop_response):
        """Business-logic actions (e.g. convert-to-order) should not redirect."""
        mw = RestToWcapiMiddleware(noop_response)
        request = rf.post("/api/transactions/orders/5/convert-to-invoice/")
        response = mw(request)
        assert response.status_code == 200
