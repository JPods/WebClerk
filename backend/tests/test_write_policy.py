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
import secrets

# Generated per run — no password literal in the repository.
TEST_PASSWORD = secrets.token_urlsafe(16)

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

def _mock_user(role="user", is_superuser=False, is_staff=False, is_authenticated=True):
    """A fake user carrying the given role.

    The write path takes the user, not the request: every writer goes through one save
    door now, and most of them have no request (Bill, 2026-09-22).
    """
    user = MagicMock()
    user.is_authenticated = is_authenticated
    user.is_superuser = is_superuser
    user.is_staff = is_staff
    user.role = role
    user.groups.values_list.return_value = []
    return user


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
        user = _mock_user(is_authenticated=False)
        assert _roles_for(user) == ["anonymous"]

    def test_superuser_gets_admin(self):
        user = _mock_user(role="admin", is_superuser=True)
        roles = _roles_for(user)
        assert "admin" in roles

    def test_staff_gets_admin(self):
        user = _mock_user(role="employee", is_staff=True)
        roles = _roles_for(user)
        assert "admin" in roles

    def test_employee_role_included(self):
        user = _mock_user(role="employee")
        roles = _roles_for(user)
        assert "employee" in roles
        assert "user" in roles  # fallback always present

    def test_default_user_role(self):
        user = _mock_user(role="user")
        roles = _roles_for(user)
        assert roles == ["user"]

    def test_empty_role_gets_fallback_user(self):
        user = _mock_user(role="")
        roles = _roles_for(user)
        assert "user" in roles


# ---------------------------------------------------------------------------
# Unit: write_allowlist()
# ---------------------------------------------------------------------------

class TestWriteAllowlist:
    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_admin_gets_none_unrestricted(self):
        from apps.core.models import Contact
        user = _mock_user(is_superuser=True)
        result = write_allowlist(Contact, user=user)
        assert result is None  # None means all fields allowed

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_employee_gets_employee_fields(self):
        from apps.core.models import Contact
        user = _mock_user(role="employee")
        result = write_allowlist(Contact, user=user)
        assert set(result) == {"email", "name_first", "name_last", "role"}

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_default_user_gets_default_fields(self):
        from apps.core.models import Contact
        user = _mock_user(role="user")
        result = write_allowlist(Contact, user=user)
        assert set(result) == {"email", "name_first"}

    @override_settings(WCAPI_POLICIES_ENABLED=False)
    def test_disabled_returns_none(self):
        from apps.core.models import Contact
        user = _mock_user(role="user")
        result = write_allowlist(Contact, user=user)
        assert result is None

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_unconfigured_model_returns_none(self):
        """Models not in WCAPI_MODEL_POLICIES get None (unrestricted)."""
        from apps.products.models import Item
        user = _mock_user(role="user")
        result = write_allowlist(Item, user=user)
        assert result is None


# ---------------------------------------------------------------------------
# Unit: enforce_write_policy()
# ---------------------------------------------------------------------------

class TestEnforceWritePolicy:
    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_admin_passes_all_fields(self):
        from apps.core.models import Contact
        user = _mock_user(is_superuser=True)
        data = {"email": "a@b.com", "role": "admin", "is_superuser": True}
        filtered, denied = enforce_write_policy(Contact, data, user=user)
        assert filtered == data
        assert denied == []

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_employee_strips_disallowed_fields(self):
        from apps.core.models import Contact
        user = _mock_user(role="employee")
        data = {
            "email": "a@b.com",
            "name_first": "Alice",
            "name_last": "Smith",
            "role": "user",
            "is_superuser": True,        # NOT in employee allow list
            "security_level": 99,         # NOT in employee allow list
        }
        filtered, denied = enforce_write_policy(Contact, data, user=user)
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
        user = _mock_user(role="user")
        data = {
            "email": "a@b.com",
            "name_first": "Alice",
            "name_last": "Smith",  # NOT in default
            "role": "admin",      # NOT in default
        }
        filtered, denied = enforce_write_policy(Contact, data, user=user)
        assert set(filtered.keys()) == {"email", "name_first"}
        assert set(denied) == {"name_last", "role"}

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_system_fields_always_stripped_for_non_admin(self):
        from apps.core.models import Contact
        user = _mock_user(role="employee")
        data = {
            "email": "a@b.com",
            "dt_created": 999,
            "dt_modified": 999,
            "version": 5,
            "uuid": "fake-uuid",
        }
        filtered, denied = enforce_write_policy(Contact, data, user=user)
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
        user = _mock_user(role="user")
        data = {
            "model_name": "contact",
            "id": 42,
            "version": 1,
            "email": "a@b.com",
            "lines": [{"item": "X"}],
        }
        filtered, denied = enforce_write_policy(Contact, data, user=user)
        # Passthrough keys must survive
        assert filtered["model_name"] == "contact"
        assert filtered["id"] == 42
        assert filtered["version"] == 1
        assert filtered["lines"] == [{"item": "X"}]
        assert "email" in filtered

    @override_settings(WCAPI_POLICIES_ENABLED=False)
    def test_disabled_policies_pass_everything(self):
        from apps.core.models import Contact
        user = _mock_user(role="user")
        data = {"email": "a@b.com", "is_superuser": True, "role": "admin"}
        filtered, denied = enforce_write_policy(Contact, data, user=user)
        assert filtered == data
        assert denied == []

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES={})
    def test_unconfigured_model_unrestricted(self):
        """No policy for model → no filtering."""
        from apps.products.models import Item
        user = _mock_user(role="user")
        data = {"name": "Widget", "sku": "W-001", "price": {"base": 10}}
        filtered, denied = enforce_write_policy(Item, data, user=user)
        assert filtered == data
        assert denied == []


# ---------------------------------------------------------------------------
# Integration: SaveWcapiView end-to-end
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWcapiSaveWritePolicy:
    """Test that write policy is enforced through the actual WCAPI save endpoint."""

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_employee_may_not_set_authority_fields_on_a_contact(self, django_user_model):
        """is_superuser is authority, not a field: the contact guard refuses it outright.

        Rewritten 2026-09-20. This asserted a 200 with is_superuser silently dropped — the
        filter behaviour. The requirement it protects (an employee must not make anyone a
        superuser) is real and is now enforced more strongly: the save is refused and the
        caller is told which field did it.
        """
        employee = django_user_model.objects.create_user(
            email="emp@example.com", password=TEST_PASSWORD, role="employee",
        )
        target = django_user_model.objects.create_user(
            email="target@example.com", password=TEST_PASSWORD, role="user",
        )
        client = _auth_client(employee)
        resp = client.post("/wcapi/save/", {
            "model_name": "contact",
            "id": target.pk,
            "email": "updated@example.com",
            "is_superuser": True,
        }, format="json")

        assert resp.status_code == 403, resp.data  # type: ignore[attr-defined]
        assert resp.data["error"]["code"] == "contact_account_guard"  # type: ignore[index]
        assert resp.data["error"]["details"] == "is_superuser"        # type: ignore[index]

        target.refresh_from_db()
        assert target.is_superuser is False
        # and the refusal is whole: the permitted field did not land either
        assert target.email == "target@example.com"

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_admin_save_can_set_any_field(self, django_user_model):
        """Admin should bypass write policy entirely."""
        admin = django_user_model.objects.create_superuser(
            email="admin@example.com", password=TEST_PASSWORD,
        )
        target = django_user_model.objects.create_user(
            email="target2@example.com", password=TEST_PASSWORD, role="user",
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
    def test_a_user_may_not_set_role_on_a_contact(self, django_user_model):
        """role is authority too, and the guard refuses rather than ignores."""
        user = django_user_model.objects.create_user(
            email="user@example.com", password=TEST_PASSWORD, role="user",
        )
        target = django_user_model.objects.create_user(
            email="target3@example.com", password=TEST_PASSWORD, role="user",
        )
        client = _auth_client(user)
        resp = client.post("/wcapi/save/", {
            "model_name": "contact", "id": target.pk, "role": "admin",
        }, format="json")

        assert resp.status_code == 403, resp.data  # type: ignore[attr-defined]
        target.refresh_from_db()
        assert target.role == "user"

    @override_settings(WCAPI_POLICIES_ENABLED=True, WCAPI_MODEL_POLICIES=_TEST_POLICIES)
    def test_a_field_the_role_cannot_edit_is_ignored_not_refused(self, django_user_model):
        """Bill, 2026-09-20: *"If it is not enumerated as edit, the back end should never
        read it as being there regardless of if it is in the payload or not."*

        name_last is outside this role's write list and is not authority, so it is simply
        not there as far as the save is concerned — the permitted fields still land. A form
        round-trips every field it was served and GET serves everything in `view`, which is
        a superset of `edit`; refusing those echoes would reject every save from the screen.
        What stops a user trying is the screen: a field the role cannot edit is locked and
        its label italic.
        """
        # On their own contact: the account guard allows a self email change, so this
        # exercises the edit enumeration rather than the guard in front of it.
        user = django_user_model.objects.create_user(
            email="user2@example.com", password=TEST_PASSWORD, role="user",
            name_last="Unchanged",
        )
        target = user
        client = _auth_client(user)
        resp = client.post("/wcapi/save/", {
            "model_name": "contact",
            "id": target.pk,
            "email": "user-updated@example.com",   # in default
            "name_first": "NewFirst",              # in default
            "name_last": "ShouldNotApply",         # not in default, not authority
        }, format="json")

        assert resp.status_code == 200, resp.data  # type: ignore[attr-defined]
        target.refresh_from_db()
        assert target.email == "user-updated@example.com"
        assert target.name_first == "NewFirst"
        assert target.name_last == "Unchanged"
