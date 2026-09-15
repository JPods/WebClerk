"""Tests for WCAPI role-based write-field policy enforcement.

Covers:
- enforce_write_policy() stripping disallowed fields
- Admin / superuser bypass
- Employee role getting employee-level fields
- Default user role getting restricted fields
- Models without policies remain unrestricted
- SYSTEM_ONLY_FIELDS always stripped for non-admins
- PASSTHROUGH_KEYS never stripped
- Integration with SaveWcapiView (end-to-end POST)
"""
import pytest
from unittest.mock import MagicMock
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.utils.model_policies import (
    enforce_write_policy,
    write_allowlist,
    _roles_for,
    SYSTEM_ONLY_FIELDS,
    PASSTHROUGH_KEYS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_request(role="user", is_superuser=False, is_staff=False, is_authenticated=True):
    """Build a fake request with a user carrying the given role."""
    user = MagicMock()
    user.is_authenticated = is_authenticated
    user.is_superuser = is_superuser
    user.is_staff = is_staff
    user.role = role
    user.groups.values_list.return_value = []
    request = MagicMock()
    request.user = user
    return request


def _auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(user)
    token['role'] = getattr(user, 'role', 'user')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


# Minimal test policies for isolated unit tests
_TEST_POLICIES = {
    "contact": {
        "fields": {
            "write": {
                "default": ["email", "name_first"],
                "by_role": {
                    "admin": ["*"],
                    "employee": ["email", "name_first", "name_last", "role"],
                },
            },
        },
    },
    "order": {
        "fields": {
            "write": {
                "default": ["status", "comments"],
                "by_role": {
                    "admin": ["*"],
                    "employee": ["status", "priority", "customer_id", "comments"],
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Unit: _roles_for()
# ---------------------------------------------------------------------------

class TestRolesFor:
    def test_unauthenticated_returns_anonymous(self):
        req = _mock_request(is_authenticated=False)
        assert _roles_for(req) == ["anonymous"]

    def test_superuser_gets_admin(self):
        req = _mock_request(role="admin", is_superuser=True)
        roles = _roles_for(req)
        assert "admin" in roles

    def test_staff_gets_admin(self):
        req = _mock_request(role="employee", is_staff=True)
        roles = _roles_for(req)
        assert "admin" in roles

    def test_employee_role_included(self):
        req = _mock_request(role="employee")
        roles = _roles_for(req)
        assert "employee" in roles
        assert "user" in roles  # fallback always present

    def test_default_user_role(self):
        req = _mock_request(role="user")
        roles = _roles_for(req)
        assert roles == ["user"]

    def test_empty_role_gets_fallback_user(self):
        req = _mock_request(role="")
        roles = _roles_for(req)
        assert "user" in roles


# ---------------------------------------------------------------------------
# Unit: write_allowlist()
# ---------------------------------------------------------------------------

class TestWriteAllowlist:
    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_admin_gets_none_unrestricted(self):
        from apps.core.models import Contact
        req = _mock_request(is_superuser=True)
        result = write_allowlist(Contact, request=req)
        assert result is None  # None means all fields allowed

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_employee_gets_employee_fields(self):
        from apps.core.models import Contact
        req = _mock_request(role="employee")
        result = write_allowlist(Contact, request=req)
        assert set(result) == {"email", "name_first", "name_last", "role"}

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_default_user_gets_default_fields(self):
        from apps.core.models import Contact
        req = _mock_request(role="user")
        result = write_allowlist(Contact, request=req)
        assert set(result) == {"email", "name_first"}

    @override_settings(WCAPI_POLICIES_ENABLED=False)
    def test_disabled_returns_none(self):
        from apps.core.models import Contact
        req = _mock_request(role="user")
        result = write_allowlist(Contact, request=req)
        assert result is None

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_unconfigured_model_returns_none(self):
        """Models not in WCAPI_MODEL_POLICIES get None (unrestricted)."""
        from apps.products.models import Item
        req = _mock_request(role="user")
        result = write_allowlist(Item, request=req)
        assert result is None


# ---------------------------------------------------------------------------
# Unit: enforce_write_policy()
# ---------------------------------------------------------------------------

class TestEnforceWritePolicy:
    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_admin_passes_all_fields(self):
        from apps.core.models import Contact
        req = _mock_request(is_superuser=True)
        data = {"email": "a@b.com", "role": "admin", "is_superuser": True}
        filtered, denied = enforce_write_policy(Contact, data, request=req)
        assert filtered == data
        assert denied == []

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_employee_strips_disallowed_fields(self):
        from apps.core.models import Contact
        req = _mock_request(role="employee")
        data = {
            "email": "a@b.com",
            "name_first": "Alice",
            "name_last": "Smith",
            "role": "user",
            "is_superuser": True,        # NOT in employee allow list
            "security_level": 99,         # NOT in employee allow list
        }
        filtered, denied = enforce_write_policy(Contact, data, request=req)
        assert "email" in filtered
        assert "name_first" in filtered
        assert "name_last" in filtered
        assert "role" in filtered
        assert "is_superuser" not in filtered
        assert "security_level" not in filtered
        assert set(denied) == {"is_superuser", "security_level"}

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_user_gets_default_fields_only(self):
        from apps.core.models import Contact
        req = _mock_request(role="user")
        data = {
            "email": "a@b.com",
            "name_first": "Alice",
            "name_last": "Smith",  # NOT in default
            "role": "admin",      # NOT in default
        }
        filtered, denied = enforce_write_policy(Contact, data, request=req)
        assert set(filtered.keys()) == {"email", "name_first"}
        assert set(denied) == {"name_last", "role"}

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_system_fields_always_stripped_for_non_admin(self):
        from apps.core.models import Contact
        req = _mock_request(role="employee")
        data = {
            "email": "a@b.com",
            "dt_created": 999,
            "dt_modified": 999,
            "version": 5,
            "uuid": "fake-uuid",
        }
        filtered, denied = enforce_write_policy(Contact, data, request=req)
        assert "email" in filtered
        # System fields should be stripped
        for sf in ("dt_created", "dt_modified", "uuid"):
            assert sf not in filtered
            assert sf in denied
        # version is a PASSTHROUGH_KEY, so it passes
        assert "version" in filtered

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_passthrough_keys_always_kept(self):
        from apps.core.models import Contact
        req = _mock_request(role="user")
        data = {
            "model_name": "contact",
            "id": 42,
            "version": 1,
            "email": "a@b.com",
            "lines": [{"item": "X"}],
        }
        filtered, denied = enforce_write_policy(Contact, data, request=req)
        # Passthrough keys must survive
        assert filtered["model_name"] == "contact"
        assert filtered["id"] == 42
        assert filtered["version"] == 1
        assert filtered["lines"] == [{"item": "X"}]
        assert "email" in filtered

    @override_settings(WCAPI_POLICIES_ENABLED=False)
    def test_disabled_policies_pass_everything(self):
        from apps.core.models import Contact
        req = _mock_request(role="user")
        data = {"email": "a@b.com", "is_superuser": True, "role": "admin"}
        filtered, denied = enforce_write_policy(Contact, data, request=req)
        assert filtered == data
        assert denied == []

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES={})
    def test_unconfigured_model_unrestricted(self):
        """No policy for model → no filtering."""
        from apps.products.models import Item
        req = _mock_request(role="user")
        data = {"name": "Widget", "sku": "W-001", "price": {"base": 10}}
        filtered, denied = enforce_write_policy(Item, data, request=req)
        assert filtered == data
        assert denied == []


# ---------------------------------------------------------------------------
# Integration: SaveWcapiView end-to-end
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWcapiSaveWritePolicy:
    """Test that write policy is enforced through the actual WCAPI save endpoint."""

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_employee_save_strips_disallowed_contact_fields(self, django_user_model):
        """Employee saving a contact should not be able to set is_superuser."""
        employee = django_user_model.objects.create_user(
            email="emp@example.com", password="pass12345", role="employee",
        )
        # Create a target contact to update
        target = django_user_model.objects.create_user(
            email="target@example.com", password="pass12345", role="user",
        )
        client = _auth_client(employee)
        payload = {
            "model_name": "contact",
            "id": target.pk,
            "email": "updated@example.com",
            "name_first": "Updated",
            "is_superuser": True,  # should be stripped
        }
        resp = client.post("/wcapi/save/", payload, format="json")
        assert resp.status_code == 200, resp.data  # type: ignore[attr-defined]

        target.refresh_from_db()
        assert target.email == "updated@example.com"
        assert target.is_superuser is False  # was not applied

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_admin_save_can_set_any_field(self, django_user_model):
        """Admin should bypass write policy entirely."""
        admin = django_user_model.objects.create_superuser(
            email="admin@example.com", password="pass12345",
        )
        target = django_user_model.objects.create_user(
            email="target2@example.com", password="pass12345", role="user",
        )
        client = _auth_client(admin)
        payload = {
            "model_name": "contact",
            "id": target.pk,
            "email": "admin-updated@example.com",
            "role": "employee",
        }
        resp = client.post("/wcapi/save/", payload, format="json")
        assert resp.status_code == 200, resp.data  # type: ignore[attr-defined]

        target.refresh_from_db()
        assert target.email == "admin-updated@example.com"
        assert target.role == "employee"

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_user_save_limited_to_default_fields(self, django_user_model):
        """Default user can only write fields listed in 'default'."""
        user = django_user_model.objects.create_user(
            email="user@example.com", password="pass12345", role="user",
        )
        target = django_user_model.objects.create_user(
            email="target3@example.com", password="pass12345", role="user",
        )
        client = _auth_client(user)
        payload = {
            "model_name": "contact",
            "id": target.pk,
            "email": "user-updated@example.com",
            "name_first": "NewFirst",
            "name_last": "ShouldNotApply",  # not in default
            "role": "admin",                # not in default — must not apply
        }
        resp = client.post("/wcapi/save/", payload, format="json")
        assert resp.status_code == 200, resp.data  # type: ignore[attr-defined]

        target.refresh_from_db()
        assert target.email == "user-updated@example.com"
        # name_last and role should NOT have been updated
        assert target.role == "user"
