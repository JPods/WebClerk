"""
Custom token refresh view that reads the refresh token from an httpOnly cookie
instead of the request body.

Replaces SimpleJWT's stock TokenRefreshView in the URL config.
"""
from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.authentication import BaseAuthentication
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from common.api_responses import api_response
from apps.core.views.token_cookie import (
    REFRESH_COOKIE_NAME,
    set_refresh_cookie,
    clear_refresh_cookie,
)


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(
    summary="Refresh Access Token (Cookie)",
    description=(
        "Reads the refresh token from an httpOnly cookie, validates it, "
        "issues a new access token (and rotated refresh cookie). "
        "No request body is required — the cookie is sent automatically by the browser."
    ),
    request=None,
    responses={
        200: inline_serializer(
            name="TokenRefreshResponse",
            fields={"access": serializers.CharField()},
        ),
        401: inline_serializer(
            name="TokenRefreshError",
            fields={"message": serializers.CharField()},
        ),
    },
)
class CookieTokenRefreshView(APIView):
    """Token refresh endpoint that reads the refresh token from a cookie."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: tuple[type[BaseAuthentication], ...] = ()

    def post(self, request):
        raw_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        # Also accept body-based refresh for mobile clients
        if not raw_token:
            raw_token = (request.data or {}).get("refresh")

        if not raw_token:
            return api_response(
                data=None,
                message="No refresh token provided",
                status_code=401,
                error={"code": "no_refresh_token", "details": None},
            )

        try:
            old_refresh = RefreshToken(raw_token)

            # Extract the new access token
            access_token = str(old_refresh.access_token)

            # Rotate: blacklist old token, issue new refresh
            # (honours ROTATE_REFRESH_TOKENS and BLACKLIST_AFTER_ROTATION settings)
            if old_refresh.get("role"):
                role = old_refresh["role"]
            else:
                role = None

            # NOTE: We do NOT call old_refresh.blacklist().
            # Blacklisting creates a one-use token that fails on any concurrent
            # refresh attempt (second tab, bootstrapAuth + interceptor race,
            # page reload during API call).  The httpOnly cookie already
            # prevents XSS token theft; the old refresh expires naturally.
            # token_blacklist app is also removed from INSTALLED_APPS.

            # Derive a fresh refresh token from the user to get current claims
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(pk=old_refresh.payload.get("user_id"))
                if not user.is_active:
                    response = api_response(
                        data=None,
                        message="Account deactivated",
                        status_code=401,
                        error={"code": "account_inactive", "details": None},
                    )
                    response.delete_cookie("refresh_token", path="/")
                    return response
                new_refresh = RefreshToken.for_user(user)
                new_access = new_refresh.access_token
                new_access["role"] = getattr(user, "role", "user")
                new_refresh["role"] = getattr(user, "role", "user")
                access_token = str(new_access)
            except User.DoesNotExist:
                # User deleted — clear cookie and deny
                resp = api_response(
                    data=None,
                    message="User not found",
                    status_code=401,
                    error={"code": "user_not_found", "details": None},
                )
                clear_refresh_cookie(resp)
                return resp

            # Include refresh token expiration so the frontend can warn
            # the user before they lose their session unexpectedly.
            import datetime
            refresh_exp = datetime.datetime.fromtimestamp(
                new_refresh.payload["exp"], tz=datetime.timezone.utc
            ).isoformat()

            resp = api_response(
                data={"access": access_token, "refresh_expires": refresh_exp},
                message="token refreshed",
            )
            set_refresh_cookie(resp, str(new_refresh))
            return resp

        except TokenError as e:
            resp = api_response(
                data=None,
                message="Invalid or expired refresh token",
                status_code=401,
                error={"code": "invalid_token", "details": str(e)},
            )
            clear_refresh_cookie(resp)
            return resp
