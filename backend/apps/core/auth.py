from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _


class RoleValidatingJWTAuthentication(JWTAuthentication):
    """JWT auth that requires a valid role claim and matches it to the DB."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        token_role = validated_token.get('role')

        if token_role is None:
            raise exceptions.AuthenticationFailed(
                _('Token is missing required role claim.'),
                code='missing_role'
            )

        from apps.core.services.access import LOGIN_ROLES
        norm_token_role = str(token_role).lower()
        if norm_token_role not in LOGIN_ROLES:
            raise exceptions.AuthenticationFailed(
                _('Invalid role in token.'),
                code='invalid_role'
            )

        db_role = getattr(user, 'role', None)
        norm_db_role = str(db_role).lower() if db_role is not None else None

        if norm_db_role != norm_token_role:
            raise exceptions.AuthenticationFailed(
                _('Role mismatch: token role does not match current user role.'),
                code='role_mismatch'
            )

        # An agent may act as another role for this request (X-WC-Act-As).
        # DRF authenticates lazily, so this runs before any view reads the role.
        from apps.core.services.access import apply_act_as_user
        apply_act_as_user(user, self._request_meta)
        return user

    def authenticate(self, request):
        self._request_meta = getattr(request, 'META', {})
        return super().authenticate(request)
