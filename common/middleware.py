import time, uuid, logging, os
from django.utils.deprecation import MiddlewareMixin
from typing import Any, Dict
from django.http import JsonResponse
from django.utils.functional import Promise
from django.utils.encoding import force_str

EXEMPT_PATH_PREFIXES: tuple[str, ...] = (
    '/admin/', '/static/', '/media/'
)

def _allow_raw_query() -> bool:
    """Return True if ?raw=1 bypass is allowed (env gated)."""
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

def _force(value: Any):
    if isinstance(value, Promise):
        return force_str(value)
    return value

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
      * Requests with ?raw=1 (explicit opt-out)
      * Responses where view sets request._skip_envelope = True
      * Responses whose top-level dict already contains status success/error
    """

    def process_response(self, request, response):  # pragma: no cover (glue; exercised indirectly)
        try:
            path = getattr(request, 'path', '')
            if is_exempt_path(path):
                _record_skip(path, 'exempt_path', getattr(response, 'status_code', 0))
                return response
            if getattr(request, '_skip_envelope', False):
                _record_skip(path, 'skip_flag', getattr(response, 'status_code', 0))
                return response
            if _allow_raw_query() and getattr(request, 'GET', {}).get('raw') == '1':
                # Transitional raw: still envelope but record skip & also surface underlying structure at top-level for tests
                _record_skip(path, 'raw_query', getattr(response, 'status_code', 0))
                # fall through to normal wrapping logic (do not early return)
            data = None
            if hasattr(response, 'data'):
                data = response.data
            elif isinstance(response, JsonResponse):
                try:
                    data = response.json()
                except Exception:
                    _record_skip(path, 'json_error', getattr(response, 'status_code', 0))
                    return response
            else:
                _record_skip(path, 'non_json_response', getattr(response, 'status_code', 0))
                return response
            if isinstance(data, dict) and data.get('status') in ('success', 'error'):
                # Already enveloped – no legacy key bubbling (removed 2025-09-02). Return untouched.
                return response
            status_code = getattr(response, 'status_code', 200)
            envelope: Dict[str, Any] = {'status': 'success' if status_code < 400 else 'error'}
            if isinstance(data, list):
                envelope['data'] = data
            elif isinstance(data, dict):
                envelope['data'] = {k: _force(v) for k, v in data.items()}
            else:
                envelope['data'] = data
            if hasattr(response, 'data'):
                try:  # type: ignore[attr-defined]
                    response.data = envelope  # type: ignore[attr-defined]
                    if hasattr(response, 'rendered_content'):
                        try:
                            response._is_rendered = False  # type: ignore[attr-defined]
                            response.render()  # type: ignore[attr-defined]
                        except Exception:
                            pass
                except Exception:
                    return response
                return response
            if isinstance(response, JsonResponse):
                return JsonResponse(envelope, status=response.status_code)
        except Exception:
            return response
        return response
