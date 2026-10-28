"""Deletes through the wcapi channel: a Setting is never deleted there."""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.core.models import Setting

User = get_user_model()


@pytest.fixture
def admin_client():
    user = User.objects.create_user(
        email="batch-del-admin@example.com",
        password="pw12345",
        name_first="Batch",
        name_last="Admin",
        username="",
        is_staff=True,
        is_superuser=True,
    )
    c = Client()
    assert c.login(email="batch-del-admin@example.com", password="pw12345")
    return c


@pytest.mark.django_db
def test_settings_are_never_deleted_through_the_channel(admin_client):
    """Bill, 2026-10-28: Settings are the application's structure, protected from deletion
    through the normal channel — even an administrator's delete is refused, with coaching."""
    from tests.conftest import make_setting
    ids = [make_setting(name=f"protected_{i}", purpose="test", is_active=True).id for i in range(3)]
    for rid in ids:
        resp = admin_client.delete(f"/wcapi/setting/{rid}/")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "setting_protected"
    assert Setting.objects.filter(id__in=ids).count() == 3
