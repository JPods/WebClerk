"""Authentication helpers for WebClerk tests.

Provides a consistent authenticated_client fixture so tests don't each
invent their own auth setup.
"""
import secrets

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


User = get_user_model()

_TEST_PASSWORD = secrets.token_urlsafe(16)


def make_superuser(email='testadmin@example.com'):
    """Create or get a superuser for testing.

    Contact logs in by email (USERNAME_FIELD); it has no username column, so the old
    get_or_create(username=…) raised FieldError and every test on the
    authenticated_client / wcapi fixtures errored before it ran (found 2026-09-23).
    """
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'role': 'superuser',
        },
    )
    user.set_password(_TEST_PASSWORD)
    user.save(update_fields=['password'])
    return user


def make_authenticated_client(user=None):
    """Return an APIClient authenticated as the given user (or a new superuser).

    Uses force_authenticate — no token/session overhead in tests.
    """
    client = APIClient()
    if user is None:
        user = make_superuser()
    client.force_authenticate(user=user)
    return client
