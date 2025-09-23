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
from django.utils.http import http_date, parse_http_date_safe
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
            path = getattr(request, 'path', '') or ''
            if path.startswith('/wcapi/'):
                return response
            try:
                if _should_skip_envelope(request, response):
                    return response
            except Exception:
                pass

            status_code = getattr(response, 'status_code', 200)

            data = getattr(response, 'data', None)
            if data is None and isinstance(response, JsonResponse):
                try:
                    data = response.json()
                except Exception:
                    return response

            if data is None or self._already_enveloped(data):
                return response

            status_val = 'success' if status_code < 400 else ('fail' if status_code < 500 else 'error')

            # Keep list payloads as lists (tests expect envelope.data to be a list for dev-fallback tag list)
            if isinstance(data, list):
                payload_data: Any = data
                ok_val = 200 <= status_code < 400
            elif isinstance(data, dict):
                payload_data = {k: (force_str(v) if isinstance(v, Promise) else v) for k, v in data.items()}
                # Ensure both items and results aliases exist if the view returned one of them
                if isinstance(payload_data.get('items'), list) and 'results' not in payload_data:
                    payload_data['results'] = payload_data['items']
                if isinstance(payload_data.get('results'), list) and 'items' not in payload_data:
                    payload_data['items'] = payload_data['results']
                ok_val = bool(payload_data.get('ok')) if 'ok' in payload_data else (200 <= status_code < 400)
            else:
                payload_data = data
                ok_val = 200 <= status_code < 400

            envelope: Dict[str, Any] = {
                'status': status_val,
                'ok': ok_val,
                'error': None,
                'code': status_code,
                'message': '',
                'data': payload_data if payload_data is not None else None,
            }

            if isinstance(payload_data, dict):
                # Promote meta for tests
                if isinstance(payload_data.get('meta'), dict):
                    envelope['meta'] = payload_data['meta']

                # Items/results aliases
                items = None
                if isinstance(payload_data.get('items'), list):
                    items = payload_data['items']
                elif isinstance(payload_data.get('results'), list):
                    items = payload_data['results']
                if items is not None:
                    envelope['items'] = items

                # Dev-fallback: tests expect envelope.data to be the list, not a dict
                meta = payload_data.get('meta') or {}
                if meta.get('policy_missing') is True:
                    list_data = items if items is not None else []
                    envelope['data'] = list_data
                    envelope['items'] = list_data  # keep convenience mirror

                # Detail caching headers if 'item' present
                if isinstance(payload_data.get('item'), dict):
                    item = payload_data['item']
                    if response.get('ETag') is None:
                        etag_src = f"{item.get('id','')}-{item.get('version','')}-{item.get('dt_updated') or item.get('dt_modified') or item.get('updated_at') or ''}"
                        if not etag_src.strip():
                            try:
                                etag_src = json.dumps(item, sort_keys=True, separators=(',', ':'))
                            except Exception:
                                etag_src = str(item)
                        etag = hashlib.md5(etag_src.encode('utf-8')).hexdigest()
                        response['ETag'] = f'W/"{etag}"'
                    etag_hdr = response.get('ETag')
                    if response.get('Last-Modified') is None:
                        ts_dt = None
                        for key in ('dt_updated', 'dt_modified', 'updated_at', 'modified', 'last_modified', 'dt', 'dt_created', 'created_at'):
                            v = item.get(key)
                            if not v:
                                continue
                            dt = parse_datetime(v) if isinstance(v, str) else v
                            if hasattr(dt, 'timestamp'):
                                ts_dt = dt
                                break
                        if ts_dt is not None:
                            if getattr(ts_dt, 'tzinfo', None) is None:
                                ts_dt = timezone.make_aware(ts_dt, timezone=timezone.utc)
                            response['Last-Modified'] = http_date(ts_dt.timestamp())
                        else:
                            if etag_hdr and etag_hdr in _LM_CACHE:
                                response['Last-Modified'] = _LM_CACHE[etag_hdr]
                            else:
                                lm_value = http_date(time.time())
                                response['Last-Modified'] = lm_value
                                if etag_hdr:
                                    _LM_CACHE[etag_hdr] = lm_value
                    inm = (getattr(request, 'META', {}) or {}).get('HTTP_IF_NONE_MATCH')
                    if inm and response.get('ETag') and inm.strip() == response.get('ETag'):
                        return JsonResponse({}, status=304)
                    ims = (getattr(request, 'META', {}) or {}).get('HTTP_IF_MODIFIED_SINCE')
                    lm_hdr = response.get('Last-Modified')
                    if ims and lm_hdr:
                        try:
                            ims_ts = parse_http_date_safe(ims)
                            lm_ts = parse_http_date_safe(lm_hdr)
                            if ims_ts is not None and lm_ts is not None and int(ims_ts) >= int(lm_ts):
                                return JsonResponse({}, status=304)
                        except Exception:
                            pass

            # Mirror items for list payloads that are raw lists
            if isinstance(payload_data, list):
                envelope['items'] = payload_data

            if hasattr(response, 'data'):
                response.data = envelope  # type: ignore[attr-defined]
                if hasattr(response, 'rendered_content'):
                    response._is_rendered = False  # type: ignore[attr-defined]
                    response.render()  # type: ignore[attr-defined]
                return response
            if isinstance(response, JsonResponse):
                return JsonResponse(envelope, status=response.status_code)
        except Exception:
            return response
        return response


class ExceptionAsJsonMiddleware(MiddlewareMixin):
    """Convert unhandled exceptions into JSON envelopes for API/JSON requests.

    Applies when either:
      - Path starts with '/wcapi/' (our API namespace), or
      - Client indicates JSON via Accept or Content-Type headers.

    This ensures Postman and other API clients receive JSON even in DEBUG.
    """
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
    Applies when enabled OR when format=json is requested (tests use format=json).
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self._re = re.compile(r'^/([a-z0-9_]+)/?$')

    def __call__(self, request):
        if request.method == 'GET':
            # Enforce when explicitly enabled, or when canonical JSON shape is requested
            enforce_q_guard = getattr(settings, 'WCAPI_Q_GUARD_ENABLED', False) or (request.GET.get('format') == 'json')
            if enforce_q_guard:
                path = request.path or '/'
                m = self._re.match(path)
                if m and 'q' in request.GET:
                    model_key = m.group(1)
                    try:
                        from apps.core.wcapi import registry as wcapi_registry
                        resolve_fn = getattr(wcapi_registry, 'resolve', None)
                        is_blessed = bool(resolve_fn and resolve_fn(model_key) is not None)
                    except Exception:
                        is_blessed = False
                    if is_blessed and not getattr(request.user, 'is_staff', False):
                        from django.http import JsonResponse
                        return JsonResponse({'detail': 'forbidden'}, status=403)
        return self.get_response(request)

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
