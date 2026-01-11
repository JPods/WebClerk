from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _


class RoleValidatingJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that validates the role in the token against the database.
    If the role in the token doesn't match the current role in the database, authentication fails.
    """

    def get_user(self, validated_token):
        """
        Override get_user to validate role from token against database.
        """
        user = super().get_user(validated_token)

        # Get role from token
        token_role = validated_token.get('role')

        if token_role is not None:
            # Get current role from database
            db_role = getattr(user, 'role', None)

            # If roles don't match, authentication fails
            if token_role != db_role:
                raise exceptions.AuthenticationFailed(
                    _('Role mismatch: token role does not match current user role.'),
                    code='role_mismatch'
                )

        return user
