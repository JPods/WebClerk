"""
Helpers for httpOnly refresh-token cookies.

The refresh token is stored in an httpOnly cookie scoped to the
token_refresh endpoint path.  This eliminates localStorage-based
XSS attack surface while keeping the access token in-memory only
on the frontend.
"""
from __future__ import annotations

from django.conf import settings
from rest_framework.response import Response

# ── Cookie config ────────────────────────────────────────────────
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/wcapi/"          # sent on /wcapi/token_refresh/ and /wcapi/logout/
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days — matches SIMPLE_JWT REFRESH_TOKEN_LIFETIME
REFRESH_COOKIE_SAMESITE = "Lax"          # Lax allows same-site navigations; Strict blocks them
REFRESH_COOKIE_HTTPONLY = True
REFRESH_COOKIE_SECURE = not getattr(settings, "DEBUG", False)


def set_refresh_cookie(response: Response, refresh_token: str) -> Response:
    """Attach the refresh token as an httpOnly cookie on the response."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        path=REFRESH_COOKIE_PATH,
        httponly=REFRESH_COOKIE_HTTPONLY,
        samesite=REFRESH_COOKIE_SAMESITE,
        secure=REFRESH_COOKIE_SECURE,
    )
    return response


def clear_refresh_cookie(response: Response) -> Response:
    """Remove the refresh token cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite=REFRESH_COOKIE_SAMESITE,
    )
    return response
