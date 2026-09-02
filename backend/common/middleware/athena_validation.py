"""AthenaValidationMiddleware — verify frontend validation tokens on write requests.

The frontend computes HMAC-SHA256(athena_key, canonical_payload) after envelope
validation passes. The athena_key lives in the JWT claims (issued at login).
This middleware verifies the HMAC — proving the request went through legitimate
frontend validation.

Three outcomes:
  1. Token present + valid   → request proceeds (normal)
  2. Token present + invalid → 400 reject (payload tampered after validation)
  3. Token absent            → request proceeds but flagged in audit trail
                               (API clients, curl, devtools — legitimate but unvalidated)

Athena does NOT block absent tokens — that would break API integrations.
She flags them so Alice can watch for patterns.

Header: X-Athena-Validated: <hex HMAC>

Established: 2026-09-02
"""
import hashlib
import hmac
import json
import logging

logger = logging.getLogger('console')

# Paths that require Athena validation (write endpoints)
ATHENA_PATHS = ('/wcapi/save/', '/wcapi/save')


class AthenaValidationMiddleware:
    """Verify frontend HMAC validation tokens on save requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method != 'POST' or request.path not in ATHENA_PATHS:
            return self.get_response(request)

        athena_header = request.META.get('HTTP_X_ATHENA_VALIDATED', '')

        if not athena_header:
            # No token — flag but allow (API clients don't send tokens)
            request._athena_validated = False
            return self.get_response(request)

        # Extract athena_key from JWT claims
        athena_key = self._get_athena_key(request)
        if not athena_key:
            # No key in JWT — can't verify, proceed unvalidated
            request._athena_validated = False
            return self.get_response(request)

        # Verify HMAC against request body
        try:
            body = request.body
            expected = hmac.new(
                athena_key.encode('utf-8'),
                body,
                hashlib.sha256,
            ).hexdigest()

            if hmac.compare_digest(athena_header, expected):
                request._athena_validated = True
            else:
                # Token present but wrong — payload was tampered after validation
                logger.warning(
                    "[ATHENA] Validation token mismatch for user %s on %s — "
                    "payload may have been modified after frontend validation",
                    getattr(request.user, 'id', 'anon'),
                    request.path,
                )
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'message': 'Athena: payload integrity check failed — '
                               'data was modified after validation',
                    'error': {
                        'code': 'athena_tamper',
                        'details': 'X-Athena-Validated token does not match payload',
                    },
                }, status=400)
        except Exception as e:
            logger.warning("[ATHENA] Verification error: %s", e)
            request._athena_validated = False

        return self.get_response(request)

    def _get_athena_key(self, request) -> str | None:
        """Extract athena_key from the JWT access token claims."""
        try:
            # DRF auth has already parsed the token by this point if
            # the middleware runs after AuthenticationMiddleware.
            # But we run before DRF, so parse the token ourselves.
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header.startswith('Bearer '):
                return None

            token_str = auth_header[7:]
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(token_str)
            return token.get('athena_key')
        except Exception:
            return None
