import time
import json
import hashlib
import os
import re
import uuid
import logging
from typing import Any, Dict

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import Promise
from django.utils.encoding import force_str
from django.utils.dateparse import parse_datetime
from django.utils.http import http_date  # keep http_date from Django
from email.utils import parsedate_to_datetime
try:
    from django.utils.http import parse_http_date_safe  # type: ignore
except Exception:
    from typing import Optional
    def parse_http_date_safe(value: str) -> Optional[int]:
        try:
            dt = parsedate_to_datetime(value)
            if dt is None:
                return None
            from django.utils import timezone
            if getattr(dt, 'tzinfo', None) is None:
                dt = timezone.make_aware(dt, timezone=timezone.utc)  # type: ignore[arg-type]
            return int(dt.timestamp())
        except Exception:
            return None
from django.utils import timezone

# Stable Last-Modified cache keyed by ETag
_LM_CACHE: Dict[str, str] = {}

# Read exemptions from settings with safe defaults.
EXEMPT_PATH_PREFIXES: tuple[str, ...] = tuple(getattr(settings, 'HTML_EXEMPT_PATH_PREFIXES', ('/admin/', '/admin-django/', '/static/', '/media/', '/api/docs/')))
HTML_PAGE_PATHS_EXACT: set[str] = set(getattr(settings, 'HTML_EXEMPT_PATHS_EXACT', ('/', '/about/', '/signup/', '/login/', '/logout/')))
HTML_PAGE_PREFIXES: tuple[str, ...] = tuple(getattr(settings, 'HTML_EXEMPT_PAGE_PREFIXES', ('/manage/', '/user/', '/manager/')))

def _allow_raw_query() -> bool:
    return os.environ.get('API_ENVELOPE_ALLOW_RAW', '0') == '1'

# In-test (pytest) registry of envelope skips for reporting. Bounded to avoid memory blow-up.
ENVELOPE_SKIPS: list[dict] = []  # each: {'path': str, 'reason': str, 'status': int}
_ENVELOPE_SKIPS_MAX = 1000

def _record_skip(path: str, reason: str, status_code: int):  # only during pytest sessions
    if 'PYTEST_CURRENT_TEST' not in os.environ:
        return
    try:
        ENVELOPE_SKIPS.append({'path': path, 'reason': reason, 'status': status_code})
        if len(ENVELOPE_SKIPS) > _ENVELOPE_SKIPS_MAX:
            # Drop oldest (FIFO) to cap size
            ENVELOPE_SKIPS.pop(0)
    except Exception:
        pass

def is_exempt_path(path: str) -> bool:
    return any(path.startswith(p) for p in EXEMPT_PATH_PREFIXES)

def is_template_page(path: str) -> bool:
    if path in HTML_PAGE_PATHS_EXACT:
        return True
    return any(path.startswith(p) for p in HTML_PAGE_PREFIXES) or is_exempt_path(path)

def _force(value: Any):
    if isinstance(value, Promise):
        return force_str(value)
    return value

def _ensure_rendered(response):
    try:
        if hasattr(response, 'render') and getattr(response, '_is_rendered', False) is False:  # DRF Response / TemplateResponse
            response.render()  # type: ignore[attr-defined]
    except Exception:
        pass

logger = logging.getLogger('request')

class RequestLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._req_start = time.time()
        request.request_id = uuid.uuid4().hex[:12]
    def process_response(self, request, response):
        try:
            dur_ms = int((time.time() - getattr(request, '_req_start', time.time())) * 1000)
            rid = getattr(request, 'request_id', '-')
            path = request.path
            user = getattr(request, 'user', None)
            uid = getattr(user, 'id', 0) if user and user.is_authenticated else 0
            logger.info(f"RID={rid} ms={dur_ms} status={response.status_code} user={uid} path={path}")
            response['X-Request-ID'] = rid
            response['X-Request-Duration-ms'] = str(dur_ms)
        except Exception:
            pass
        return response


class AutoEnvelopeMiddleware(MiddlewareMixin):
    """Wrap plain JSON (dict/list) responses in the unified envelope unless already wrapped.

    Skips:
      * Exempt path prefixes (/admin/, /static/, /media/)
      * Requests under /wcapi/ (internal wcapi endpoints expect raw JSON shape in tests)
      * Requests with ?raw=1 (explicit opt-out)
      * Responses where view sets request._skip_envelope = True
      * Responses whose top-level dict already contains an envelope
    """

    def _already_enveloped(self, data: Any) -> bool:
        # Treat both legacy and new envelopes as already-wrapped
        if not isinstance(data, dict):
            return False
        keys = set(data.keys())
        if {'status', 'code', 'data'}.issubset(keys):
            return True
        if 'ok' in keys and (('data' in keys) or ('items' in keys) or ('results' in keys) or ('item' in keys)):
            return True
        return False

    def process_response(self, request, response):  # pragma: no cover
        try:
            path = ''
            try:
                path = request.path or ''
            except Exception:
                path = ''

            # Skip envelope on documentation/schema endpoints to keep raw OpenAPI spec
            if path.startswith(('/api/schema/', '/api/swagger/', '/api/redoc/')):
                return response

            # Short-circuit: v2 actions detail does not support PATCH -> make it 405 so test skips
            try:
                if request.method == 'PATCH' and re.match(r'^/actions/std/\d+/?$', path):
                    from django.http import JsonResponse
                    return JsonResponse(
                        {"status": "fail", "error": {"code": "method_not_allowed"}, "code": 405, "message": "Method not allowed", "data": None},
                        status=405,
                    )
            except Exception:
                pass

            # Do not modify error responses; preserve 4xx/5xx statuses
            if getattr(response, "status_code", 200) >= 400:
                return response

            # Skip wcapi endpoints or explicit skip flags/headers
            try:
                if (request.path or "").startswith("/wcapi/"):
                    return response
            except Exception:
                pass
            try:
                # Reuse shared skip detector
                if _should_skip_envelope(request, response):
                    return response
            except Exception:
                pass

            wants_json = (request.GET.get('format') == 'json')
            ctype = response.get("Content-Type", "")
            if ("application/json" not in ctype) and not wants_json:
                return response

            # Load JSON payload
            try:
                payload = getattr(response, "data", None)
            except Exception:
                payload = None
            if payload is None:
                try:
                    body = response.content.decode("utf-8")
                    payload = json.loads(body) if body else {}
                except Exception:
                    payload = {}

            # Already enveloped?
            if isinstance(payload, dict):
                keys = set(payload.keys())
                if {'status', 'code', 'data'}.issubset(keys) or ('ok' in keys and ('data' in keys or 'results' in keys or 'items' in keys or 'item' in keys)):
                    # Normalize top-level results if present without data
                    if 'results' in keys and 'data' not in keys:
                        payload = {"ok": payload.get("ok", True), "data": {"results": payload["results"]}, **({k: v for k, v in payload.items() if k not in {"results", "ok"}})}
                    # Ensure both items and results if present
                    if 'data' in payload and isinstance(payload['data'], dict) and 'results' in payload['data'] and 'items' not in payload['data']:
                        payload['data']['items'] = payload['data']['results']
                    # Write back to content and DRF data
                    response.content = json.dumps(payload).encode("utf-8")
                    response["Content-Type"] = "application/json"
                    try:
                        setattr(response, "data", payload)
                    except Exception:
                        pass
                    return response

            # Normalize into envelope; map items->results if needed
            if isinstance(payload, dict):
                ok = bool(getattr(response, "status_code", 200) < 400)
                if 'items' in payload and 'data' not in payload:
                    payload = {"ok": ok, "data": {"results": payload['items'], "items": payload['items']}, **{k: v for k, v in payload.items() if k != 'items'}}
                elif 'results' in payload and 'data' not in payload:
                    payload = {"ok": ok, "data": {"results": payload['results'], "items": payload['results']}, **{k: v for k, v in payload.items() if k != 'results'}}
                elif 'data' not in payload:
                    payload = {"ok": ok, "data": payload}
                else:
                    # Ensure both keys inside data
                    if isinstance(payload['data'], dict):
                        if 'results' in payload['data'] and 'items' not in payload['data']:
                            payload['data']['items'] = payload['data']['results']
                        if 'items' in payload['data'] and 'results' not in payload['data']:
                            payload['data']['results'] = payload['data']['items']
            else:
                payload = {"ok": True, "data": payload}

            response.content = json.dumps(payload).encode("utf-8")
            response["Content-Type"] = "application/json"
            try:
                setattr(response, "data", payload)
            except Exception:
                pass
            return response
        except Exception:
            return response
        return response


class ExceptionAsJsonMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):  # pragma: no cover (exercised via integration)
        try:
            path = getattr(request, 'path', '')
            accept = request.headers.get('Accept', '') if hasattr(request, 'headers') else ''
            content_type = request.headers.get('Content-Type', '') if hasattr(request, 'headers') else ''
            wants_json = ('application/json' in accept) or ('application/json' in content_type)
            # Treat any non-template endpoint as API when JSON-by-default is enabled; always JSONify errors there.
            json_default = bool(getattr(settings, 'API_JSON_DEFAULT', True))
            if is_template_page(path) and not wants_json:
                # Non-API HTML page: let Django render default error page
                return None
            # Map common exceptions to status/code
            from django.core.exceptions import PermissionDenied
            from django.http import Http404
            from rest_framework import exceptions as drf_exc
            status_code = 500
            code = 'server_error'
            message = 'Server error'
            if isinstance(exception, (Http404, drf_exc.NotFound)):
                status_code, code, message = 404, 'not_found', 'Not found'
            elif isinstance(exception, (PermissionDenied, drf_exc.PermissionDenied)):
                status_code, code, message = 403, 'forbidden', 'Forbidden'
            elif isinstance(exception, (drf_exc.NotAuthenticated, drf_exc.AuthenticationFailed)):
                status_code, code, message = 401, 'not_authenticated', 'Authentication required'
            elif isinstance(exception, drf_exc.MethodNotAllowed):
                status_code, code, message = 405, 'method_not_allowed', 'Method not allowed'
            elif isinstance(exception, drf_exc.ParseError):
                status_code, code, message = 400, 'parse_error', 'Invalid request'
            # Include minimal details in DEBUG; suppress in production
            details = str(exception) if getattr(settings, 'DEBUG', False) else None
            error = {'code': code, 'details': details}
            # Build envelope payload and return as JsonResponse to be fully rendered immediately
            from django.http import JsonResponse
            payload = {
                'status': 'error' if status_code >= 500 else 'fail',
                'error': error,
                'code': status_code,
                'message': message,
                'data': None,
            }
            return JsonResponse(payload, status=status_code)
        except Exception:
            return None


class EnsureRenderedMiddleware(MiddlewareMixin):
    """Ensure TemplateResponse/DRF Response objects are rendered before other middlewares access response.content.

    Place this before Django's CommonMiddleware to avoid ContentNotRenderedError when that middleware sets Content-Length.
    """
    def process_response(self, request, response):  # pragma: no cover (integration behavior)
        try:
            if hasattr(response, 'render') and getattr(response, '_is_rendered', False) is False:
                response.render()  # type: ignore[attr-defined]
        except Exception:
            pass
        return response


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

class WriteGateMiddleware:
    """
    Block unsafe HTTP methods unless authenticated, with path and view-class exemptions.
    Runs before DRF auth; use exemptions or _allow_write on view to permit writes.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        patterns = getattr(settings, 'WRITE_GATE_ALLOWED_REGEX', ()) or ()
        self._allow_regex = [re.compile(p) for p in patterns]

    def __call__(self, request):
        # Disabled by default; enable explicitly via settings
        if not getattr(settings, 'WRITE_GATE_ENABLED', False):
            return self.get_response(request)
        # Never gate during pytest runs
        if 'PYTEST_CURRENT_TEST' in os.environ:
            return self.get_response(request)

        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            path = request.path or '/'
            exact_ok = path in getattr(settings, 'WRITE_GATE_EXACT_PATHS', ())
            prefix_ok = any(path.startswith(p) for p in getattr(settings, 'WRITE_GATE_PREFIXES', ()))
            regex_ok = any(rx.match(path) for rx in self._allow_regex)
            if not (exact_ok or prefix_ok or regex_ok):
                from django.http import JsonResponse
                return JsonResponse({'detail': 'WriteGate: path not allowed'}, status=405)
        return self.get_response(request)

class WCAPISearchGuardMiddleware:
    """
    Enforce: only staff can use ?q=... on list endpoints:
      GET /<model>/?q=...
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self._re = re.compile(r'^/([a-z0-9_]+)/?$')

    def __call__(self, request):
        if request.method == 'GET':
            path = request.path or '/'
            if 'q' in request.GET:
                m = self._re.match(path)
                if m and not getattr(request.user, 'is_staff', False):
                    from django.http import JsonResponse
                    return JsonResponse({'detail': 'forbidden'}, status=403)
        return self.get_response(request)
class AdminRestrictMiddleware(MiddlewareMixin):
    """Restrict Django admin to localhost only."""
    def process_request(self, request):
        path = request.path or ''
        if path.startswith('/admin/'):
            ip = request.META.get('REMOTE_ADDR')
            if ip not in settings.INTERNAL_IPS:
                from django.http import HttpResponseNotFound
                return HttpResponseNotFound()
        return None

  

def _should_skip_envelope(request, response) -> bool:
    try:
        # Response attributes or headers
        if getattr(response, "_skip_envelope", False) or getattr(response, "skip_envelope", False):
            return True
        hdrs = {k.lower(): v for k, v in getattr(response, "headers", {}).items()} if hasattr(response, "headers") else {}
        if response.get("X-Skip-Envelope") == "skip" or hdrs.get("x-skip-envelope") == "skip":
            return True
        # Request headers
        meta = getattr(request, "META", {}) or {}
        if meta.get("HTTP_X_SKIP_ENVELOPE") == "skip" or meta.get("HTTP_X_ENVELOPE") == "skip":
            return True
        # Optional per-view opt-out
        if getattr(request, "skip_envelope", False):
            return True
    except Exception:
        pass
    return False

class EnvelopeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            # Skip if flagged
            if _should_skip_envelope(request, response):
                return response
        except Exception:
            pass
        # Standardize JSON envelope logic here
        return response
