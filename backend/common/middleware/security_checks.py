"""Security enforcement middleware — HTTPS, alert thresholds, empty-result monitoring.

Implements controls documented in readmes/50-security-policy-webclerk.md:
  - §4: HTTPS-only enforcement (localhost dev exempt)
  - §7: Alert thresholds for failed auth, empty results, unsigned requests
  - §12: Connection sunset, Athena HMAC absent tracking

Established: 2026-09-10
"""
import logging
import time
from collections import defaultdict

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger('console')
security_logger = logging.getLogger('security')


# ── In-memory counters for alert thresholds ──────────────────────────
# These reset on server restart — acceptable for alerting (not enforcement).
# For persistence, move to Django cache or Redis.
_auth_failures = defaultdict(list)    # IP → [timestamps]
_empty_results = defaultdict(int)     # user_id → consecutive zero-result count
_unsigned_saves = defaultdict(int)    # user_id → count of saves without Athena token

# Thresholds
AUTH_FAIL_LIMIT = 10           # failures per IP
AUTH_FAIL_WINDOW = 300         # seconds (5 minutes)
EMPTY_RESULT_THRESHOLD = 5    # consecutive zero-result queries before alert
UNSIGNED_SAVE_LOG_INTERVAL = 10  # log every N unsigned saves per user


class HttpsEnforcementMiddleware:
    """Reject plain HTTP requests to wcapi and bundle endpoints.

    Localhost (127.0.0.1, ::1) is exempt for development.
    Django's SECURE_SSL_REDIRECT handles the general case; this is
    belt-and-suspenders for the API layer specifically.
    """

    PROTECTED_PREFIXES = ('/wcapi/', '/api/sync/')

    # Localhost addresses exempt from HTTPS requirement
    LOCALHOST = {'127.0.0.1', '::1', '::ffff:127.0.0.1', 'localhost'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Never enforce in DEBUG mode — dev servers use HTTP
        if getattr(settings, 'DEBUG', False):
            return self.get_response(request)

        # Only enforce on protected paths
        path = request.path or '/'
        if not any(path.startswith(p) for p in self.PROTECTED_PREFIXES):
            return self.get_response(request)

        # Check if request is HTTPS
        # request.is_secure() respects SECURE_PROXY_SSL_HEADER
        if request.is_secure():
            return self.get_response(request)

        # Exempt localhost development
        remote = request.META.get('REMOTE_ADDR', '')
        if remote in self.LOCALHOST:
            return self.get_response(request)

        # Exempt if SECURE_SSL_REDIRECT is already handling it
        # (avoid double-rejecting in production)
        if getattr(settings, 'SECURE_SSL_REDIRECT', False):
            return self.get_response(request)

        security_logger.warning(
            "[SECURITY] Rejected plain HTTP request to %s from %s",
            path, remote,
        )
        return JsonResponse({
            'success': False,
            'message': 'HTTPS required for all API requests',
            'error': {'code': 'https_required'},
        }, status=403)


class SecurityAlertMiddleware:
    """Track security-relevant events and log alerts at thresholds.

    Monitors:
      - Failed authentication attempts (brute force detection)
      - Empty query results for non-superusers (misconfigured org_ids)
      - Unsigned save requests (Athena HMAC absent)

    Runs after authentication middleware and after the response is generated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            self._check_auth_failure(request, response)
            self._check_empty_results(request, response)
            self._check_unsigned_save(request)
        except Exception:
            pass  # Security monitoring must never break the request

        return response

    def _check_auth_failure(self, request, response):
        """Track failed auth attempts per IP. Alert at threshold."""
        if response.status_code not in (401, 403):
            return

        ip = self._get_client_ip(request)
        now = time.time()

        # Clean old entries
        _auth_failures[ip] = [
            t for t in _auth_failures[ip]
            if now - t < AUTH_FAIL_WINDOW
        ]
        _auth_failures[ip].append(now)

        count = len(_auth_failures[ip])
        if count == AUTH_FAIL_LIMIT:
            security_logger.warning(
                "[SECURITY ALERT] %d failed auth attempts from %s in %d seconds — "
                "possible brute force. Path: %s",
                count, ip, AUTH_FAIL_WINDOW, request.path,
            )
            # Alice observation — fire and forget
            self._alice_observe(
                'auth_brute_force',
                f'{count} failed auth attempts from {ip} in {AUTH_FAIL_WINDOW}s',
            )

    def _check_empty_results(self, request, response):
        """Track non-superusers getting zero results. Alert at threshold."""
        if response.status_code != 200:
            return
        if request.method != 'GET':
            return

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return
        if getattr(user, 'is_superuser', False):
            return

        # A list read through the REST channel: GET /wcapi/<model>/ (named by its route —
        # the old /wcapi/get/ path is gone, and matching it left this alarm dead).
        from django.urls import Resolver404, resolve
        try:
            if resolve(request.path).url_name != 'wcapi-model':
                return
        except Resolver404:
            return

        # Try to detect empty results from response
        try:
            import json
            content = response.content.decode('utf-8', errors='ignore')
            data = json.loads(content)

            # Check various response shapes
            results = data.get('data', data.get('results', data.get('items', None)))
            if isinstance(results, dict):
                results = results.get('results')
            if results is not None and (isinstance(results, list) and len(results) == 0):
                _empty_results[user.id] += 1
                count = _empty_results[user.id]

                if count == EMPTY_RESULT_THRESHOLD:
                    security_logger.warning(
                        "[SECURITY ALERT] User %s (%s) received %d consecutive "
                        "empty results — possible misconfigured org_ids or role",
                        user.id,
                        getattr(user, 'email', '?'),
                        count,
                    )
                    self._alice_observe(
                        'empty_results_pattern',
                        f'User {user.id} got {count} consecutive empty results — '
                        f'check org_ids and role configuration',
                    )
            elif results is not None:
                # Got results — reset counter
                _empty_results[user.id] = 0
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            pass

    def _check_unsigned_save(self, request):
        """Track save requests without Athena validation token."""
        from common.middleware.athena_validation import is_save
        if not is_save(request):
            return

        validated = getattr(request, '_athena_validated', None)
        if validated is False:
            user = getattr(request, 'user', None)
            uid = getattr(user, 'id', 'anon') if user else 'anon'
            _unsigned_saves[uid] += 1

            if _unsigned_saves[uid] % UNSIGNED_SAVE_LOG_INTERVAL == 0:
                security_logger.info(
                    "[SECURITY] User %s has made %d saves without Athena "
                    "validation token (X-Athena-Validated header absent)",
                    uid, _unsigned_saves[uid],
                )

    @staticmethod
    def _get_client_ip(request):
        """Get client IP, respecting X-Forwarded-For behind proxy."""
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    @staticmethod
    def _alice_observe(event, message):
        """Fire-and-forget observation to Alice."""
        try:
            import subprocess
            import os
            script = "/opt/andi/scripts/alice-observe.py"
            if not os.path.exists(script):
                # Local dev — try Allie capture instead
                script = os.path.expanduser("~/Allie/scripts/allie-capture.py")
                if not os.path.exists(script):
                    return
                subprocess.Popen(
                    ["python3", script, "--source", "WC3",
                     "--event", event, "--message", message[:200]],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return
            subprocess.Popen(
                ["python3", script, "--event", event, "--message", message[:200]],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass
