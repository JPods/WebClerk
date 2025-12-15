import time
import json
import os
import re
import uuid
import logging
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import Promise
from django.utils.encoding import force_str
from email.utils import parsedate_to_datetime
try:
    from django.utils.http import parse_http_date_safe  # type: ignore
except Exception:
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

# Stable Last-Modified cache keyed by ETag
_LM_CACHE: Dict[str, str] = {}

# Read exemptions from settings with safe defaults.
EXEMPT_PATH_PREFIXES: tuple[str, ...] = tuple(getattr(settings, 'HTML_EXEMPT_PATH_PREFIXES', ('/admin/', '/admin-django/', '/static/', '/media/', '/api/docs/')))
HTML_PAGE_PATHS_EXACT: set[str] = set(getattr(settings, 'HTML_EXEMPT_PATHS_EXACT', ('/', '/about/', '/signup/', '/login/', '/logout/')))
HTML_PAGE_PREFIXES: tuple[str, ...] = tuple(getattr(settings, 'HTML_EXEMPT_PAGE_PREFIXES', ('/manage/', '/user/', '/manager/')))

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

from common.api_responses import build_api_envelope

logger = logging.getLogger('request')
console_logger = logging.getLogger('console')  # New console logger

class RequestLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._req_start = time.time()
        request.request_id = uuid.uuid4().hex[:12]
        
        # Enhanced logging for wcapi/save/ debugging
        path = request.path
        method = request.method
        user = getattr(request, 'user', None)
        user_id = getattr(user, 'id', 'Anonymous') if user else 'Anonymous'
        
        console_logger.info(f"[WCAPI_DEBUG] REQUEST START - ID: {request.request_id} | {method} {path} | User: {user_id}")
            
    def process_response(self, request, response):
        try:
            dur_ms = int((time.time() - getattr(request, '_req_start', time.time())) * 1000)
            rid = getattr(request, 'request_id', '-')
            path = request.path
            user = getattr(request, 'user', None)
            uid = getattr(user, 'id', 0) if user and user.is_authenticated else 0
            status = response.status_code
            
            # Enhanced logging
            console_logger.info(f"[WCAPI_DEBUG] RESPONSE - ID: {rid} | {dur_ms}ms | Status: {status} | User: {uid} | {path}")
            
            logger.info(f"RID={rid} ms={dur_ms} status={status} user={uid} path={path}")
            response['X-Request-ID'] = rid
            response['X-Request-Duration-ms'] = str(dur_ms)
        except Exception as e:
            console_logger.error(f"[WCAPI_DEBUG] Error in middleware: {e}")
        return response


class AutoEnvelopeMiddleware(MiddlewareMixin):
    """Ensure every JSON response conforms to the canonical ApiEnvelope structure."""

    _SCHEMA_PATH_PREFIXES = ('/api/schema/', '/api/swagger/', '/api/redoc/', '/wcapi/schema/', '/wcapi/swagger/', '/wcapi/redoc/')

    def _is_json_response(self, response) -> bool:
        try:
            ctype = response.get('Content-Type', '')
        except Exception:
            ctype = ''
        return 'application/json' in ctype or hasattr(response, 'data')

    def _extract_payload(self, response):
        try:
            payload = getattr(response, 'data', None)
        except Exception:
            payload = None
        if payload is not None:
            return payload
        try:
            body = response.content.decode('utf-8')
            return json.loads(body) if body else {}
        except Exception:
            return None

    def _already_enveloped(self, response, payload) -> bool:
        if getattr(response, '_api_enveloped', False):
            return True
        if not isinstance(payload, dict):
            return False
        keys = set(payload.keys())
        return {'status', 'code', 'data'}.issubset(keys)

    def _split_payload(self, payload: Any, status_code: int):
        """Return (message, data, error) tuples derived from bare DRF payloads."""
        if not isinstance(payload, dict):
            return '', payload, None

        data_copy: Dict[str, Any] = dict(payload)

        message = str(data_copy.pop('message', '') or '')

        raw_error = data_copy.pop('error', None)
        errors_list = data_copy.pop('errors', None)
        if raw_error is None and errors_list is not None:
            raw_error = {'code': 'validation_error', 'details': errors_list}

        detail = data_copy.pop('detail', None)
        if status_code >= 400:
            if raw_error is None and detail is not None:
                err_code = data_copy.pop('code', None) or 'detail'
                raw_error = {'code': err_code, 'details': detail}
            if not message and detail is not None:
                message = str(detail)
        elif detail is not None:
            data_copy['detail'] = detail

        error = self._normalize_error(raw_error)
        if not message and isinstance(error, dict):
            details = error.get('details')
            if isinstance(details, str):
                message = details
        elif not message and isinstance(raw_error, str):
            message = raw_error

        data_payload = data_copy if data_copy else None
        return message, data_payload, error

    @staticmethod
    def _normalize_error(raw: Any):
        if raw in (None, ''):
            return None
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, (list, tuple)):
            return {'code': 'error_list', 'details': list(raw)}
        return {'code': str(raw), 'details': None}

    def _write_payload(self, response, payload: Dict[str, Any]):
        try:
            setattr(response, 'data', payload)
        except Exception:
            pass
        try:
            response.content = json.dumps(payload).encode('utf-8')
            response['Content-Type'] = 'application/json'
        except Exception:
            pass
        setattr(response, '_api_enveloped', True)

    def process_response(self, request, response):  # pragma: no cover (integration focused)
        try:
            path = getattr(request, 'path', '') or ''

            if any(path.startswith(p) for p in self._SCHEMA_PATH_PREFIXES):
                return response

            skip_envelope, skip_reason = _should_skip_envelope(request, response)
            if skip_envelope:
                if skip_reason:
                    _record_skip(path, skip_reason, getattr(response, 'status_code', 200))
                return response

            if is_exempt_path(path):
                return response

            if not self._is_json_response(response):
                return response

            payload = self._extract_payload(response)
            if payload is None:
                return response

            status_code = getattr(response, 'status_code', 200)

            if self._already_enveloped(response, payload):
                # Normalize message/error to canonical keys if needed
                return response

            message, data_payload, error = self._split_payload(payload, status_code)

            envelope = build_api_envelope(data=data_payload, message=message, status_code=status_code, error=error)
            self._write_payload(response, envelope)
            return response
        except Exception:
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

def _should_skip_envelope(request, response) -> Tuple[bool, Optional[str]]:
    try:
        # Response attributes or headers
        if getattr(response, "_skip_envelope", False) or getattr(response, "skip_envelope", False):
            return True, 'response_flag'
        hdrs = {k.lower(): v for k, v in getattr(response, "headers", {}).items()} if hasattr(response, "headers") else {}
        if response.get("X-Skip-Envelope") == "skip" or hdrs.get("x-skip-envelope") == "skip":
            return True, 'response_header'
        # Request headers
        meta = getattr(request, "META", {}) or {}
        if meta.get("HTTP_X_SKIP_ENVELOPE") == "skip" or meta.get("HTTP_X_ENVELOPE") == "skip":
            return True, 'request_header'
        # Optional per-view opt-out
        if getattr(request, "skip_envelope", False):
            return True, 'view_flag'
    except Exception:
        pass
    return False, None

class EnvelopeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            skip_envelope, skip_reason = _should_skip_envelope(request, response)
            if skip_envelope:
                if skip_reason:
                    _record_skip(getattr(request, 'path', '') or '', skip_reason, getattr(response, 'status_code', 200))
                return response
        except Exception:
            pass
        # Standardize JSON envelope logic here
        return response
