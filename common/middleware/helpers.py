"""Shared middleware helpers — skip-envelope logic, path checks, etc."""
import os
import json
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.utils.functional import Promise
from django.utils.encoding import force_str

try:
    from django.utils.http import parse_http_date_safe  # type: ignore
except Exception:
    from email.utils import parsedate_to_datetime

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
        if hasattr(response, 'render') and getattr(response, '_is_rendered', False) is False:
            response.render()
    except Exception:
        pass


def _should_skip_envelope(request, response) -> Tuple[bool, Optional[str]]:
    try:
        if getattr(response, "_skip_envelope", False) or getattr(response, "skip_envelope", False):
            return True, 'response_flag'
        hdrs = {k.lower(): v for k, v in getattr(response, "headers", {}).items()} if hasattr(response, "headers") else {}
        if response.get("X-Skip-Envelope") == "skip" or hdrs.get("x-skip-envelope") == "skip":
            return True, 'response_header'
        meta = getattr(request, "META", {}) or {}
        if meta.get("HTTP_X_SKIP_ENVELOPE") == "skip" or meta.get("HTTP_X_ENVELOPE") == "skip":
            return True, 'request_header'
        if getattr(request, "skip_envelope", False):
            return True, 'view_flag'
    except Exception:
        pass
    return False, None
