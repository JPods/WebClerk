"""Authentication helpers for WebClerk tests.

Provides a consistent authenticated_client fixture so tests don't each
invent their own auth setup.
"""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


User = get_user_model()

_TEST_PASSWORD = 'testpass1111'


def make_superuser(username='testadmin', email='testadmin@example.com'):
    """Create or get a superuser for testing."""
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
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
