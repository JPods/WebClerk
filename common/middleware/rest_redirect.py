"""
RestToWcapiMiddleware — intercepts legacy REST paths (/api/...) and
redirects them to the unified wcapi gateway.

Mapping examples (from 03-wcapi-gateway.md):
  /api/invoices/                    → /wcapi/get/?model_name=invoice
  /api/contacts/                    → /wcapi/get/?model_name=contact
  /api/core/contacts/list           → /wcapi/get/?model_name=contact
  /api/invoices/123/                → /wcapi/get/?model_name=invoice&id=123
  /api/transactions/invoices/123/   → /wcapi/get/?model_name=invoice&id=123

Strategy:
  1. Only intercept paths starting with /api/ (excluding admin, docs schema, etc.)
  2. Strip the /api/ prefix and any known app-namespace segments
     (orgs/, transactions/, products/, core/, docs/, communications/, etc.)
  3. Extract the model name (last "word" segment) and optional numeric ID
  4. Ignore trailing action verbs like /list, /detail (they map to GET)
  5. Redirect GET → /wcapi/get/; POST/PUT/PATCH → /wcapi/save/;
     DELETE → /wcapi/delete/
  6. Preserve original query-string parameters

Related files:
  wc3  readmes/03-wcapi-gateway.md          – gateway overview & endpoint reference
  wc3  tests/test_rest_redirect.py           – 46 tests for this middleware
  wc3  apps/core/services/wcapi_registry.py  – runtime model registry
  r25  src/api/restToWcapi.ts                – client-side REST→wcapi converter
  r25  src/api/modelNameResolver.ts          – canonical model-name resolution
  r25  src/pages/tools/WhitelistTester.tsx    – interactive REST + wcapi tester
  r25  readmes/api-migration-rest-to-wcapi.md – migration tracker
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urlencode, urlparse, parse_qs

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, QueryDict

logger = logging.getLogger(__name__)

# Known app-namespace path segments that appear between /api/ and the model name.
# These are stripped to isolate the actual resource name.
_APP_PREFIXES = frozenset({
    "orgs", "transactions", "products", "core", "docs",
    "communications", "accounts", "support", "sync",
})

# Trailing "action" segments that don't represent a distinct resource —
# they simply mean "list" or "detail" and map to /wcapi/get/.
_LIST_ACTIONS = frozenset({"list", "detail"})

# Paths under /api/ that should NOT be redirected (they have dedicated views
# with business logic that doesn't map to simple CRUD).
_EXEMPT_PREFIXES = (
    "/api/docs/stats",                          # doc stats view
    "/api/docs/qa/",                            # QA endpoints (also under wcapi)
    "/api/transactions/transfers/",             # transfer operations (validate, execute, bulk)
    "/api/transactions/payments/process",       # payment processing
    "/api/transactions/payments/apply",         # payment application
    "/api/transactions/payments/webhooks/",     # webhook receivers
    "/api/transactions/payments/reconcile",     # payment reconciliation
    "/api/transactions/inventory/",             # inventory reserve/release
)

# Action segments after an ID that indicate a business-logic endpoint,
# not a simple CRUD resource.  E.g. /api/transactions/orders/5/convert-to-invoice/
_ACTION_VERBS = frozenset({
    "convert-to-order", "convert-to-invoice", "convert-to-purchase",
    "reserve-inventory", "receive-goods", "totals", "payment-status",
})

# Regex: a segment that is purely numeric (record ID).
_NUMERIC_RE = re.compile(r"^\d+$")


def _singularize(name: str) -> str:
    """Naive singularization matching wcapi_registry._singularize."""
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("ses"):
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def _parse_rest_path(path: str):
    """
    Parse a REST-style path into (model_name, record_id | None).

    Returns (None, None) if the path cannot be interpreted.

    Examples:
        /api/invoices/          → ("invoice", None)
        /api/invoices/123/      → ("invoice", "123")
        /api/transactions/invoices/123/ → ("invoice", "123")
        /api/core/contacts/list → ("contact", None)
    """
    # Strip /api/ prefix and trailing slashes
    trimmed = path.strip("/")
    if trimmed.startswith("api/"):
        trimmed = trimmed[4:]
    elif trimmed == "api":
        return None, None

    segments = [s for s in trimmed.split("/") if s]
    if not segments:
        return None, None

    # Remove known app-prefix segments from the front
    while segments and segments[0].lower() in _APP_PREFIXES:
        segments.pop(0)

    if not segments:
        return None, None

    # Remove trailing action verbs (list, detail)
    while segments and segments[-1].lower() in _LIST_ACTIONS:
        segments.pop()

    if not segments:
        return None, None

    # If the trailing segment is a business-logic action verb
    # (e.g. /orders/5/convert-to-invoice/), bail — don't redirect.
    if segments[-1].lower() in _ACTION_VERBS:
        return None, None

    # Check for trailing numeric ID
    record_id = None
    if _NUMERIC_RE.match(segments[-1]):
        record_id = segments.pop()

    if not segments:
        return None, None

    # The last remaining segment is the resource name (possibly plural)
    resource = segments[-1].lower()
    model_name = _singularize(resource)

    # Normalise hyphens to underscores (e.g. "bill-of-material" → "bill_of_material")
    model_name = model_name.replace("-", "_")

    return model_name, record_id


def _build_wcapi_url(method: str, model_name: str, record_id: str | None,
                     original_qs: str) -> str:
    """Build the target wcapi URL with query parameters."""
    # Map HTTP method → wcapi endpoint
    if method in ("POST", "PUT", "PATCH"):
        endpoint = "/wcapi/save/"
    elif method == "DELETE":
        endpoint = "/wcapi/delete/"
    else:
        endpoint = "/wcapi/get/"

    # Start with original query params (filters, search, pagination, etc.)
    params = QueryDict(original_qs, mutable=True)

    # Inject model_name (don't overwrite if caller already included it)
    if "model_name" not in params:
        params["model_name"] = model_name

    # Inject id for detail requests
    if record_id and "id" not in params:
        params["id"] = record_id

    qs = params.urlencode()
    return f"{endpoint}?{qs}" if qs else endpoint


class RestToWcapiMiddleware:
    """
    Django middleware that intercepts /api/... REST calls and 301-redirects
    them to the equivalent /wcapi/ gateway endpoint.

    Enable via settings.MIDDLEWARE and optionally control with:
      REST_REDIRECT_ENABLED = True/False   (default True)
      REST_REDIRECT_LOG     = True/False   (log each redirect)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "REST_REDIRECT_ENABLED", True):
            return self.get_response(request)

        path = request.path or "/"

        # Only intercept /api/ paths
        if not path.startswith("/api/"):
            return self.get_response(request)

        # Skip exempt paths (dedicated views that should remain)
        for prefix in _EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        model_name, record_id = _parse_rest_path(path)
        if model_name is None:
            # Cannot parse — let Django handle normally (may 404)
            return self.get_response(request)

        target = _build_wcapi_url(
            request.method,
            model_name,
            record_id,
            request.META.get("QUERY_STRING", ""),
        )

        if getattr(settings, "REST_REDIRECT_LOG", False):
            logger.info(
                "REST→wcapi redirect: %s %s → %s", request.method, path, target
            )

        return HttpResponsePermanentRedirect(target)
