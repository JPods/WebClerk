"""Which fields a caller may write: the role's edit enumeration, and nothing else.

Bill, 2026-09-23: the settings.py write lists (WCAPI_MODEL_POLICIES) are retired; the
role block's ``edit`` list — roles live in code — is the one field authority. A field not
enumerated is ignored, not refused (2026-09-20). System fields are written only by an admin;
carrier signals pass typed or are refused; a person editing their own contact may
also write the self-edit fields.
"""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact
from apps.core.services.door import Actor
from apps.core.services.save import SYSTEM_ONLY_FIELDS, _enumerated_edit

# Generated per run — no password literal in the repository.
TEST_PASSWORD = secrets.token_urlsafe(16)

pytestmark = pytest.mark.django_db


def _grant(model_key, role, block):
    """Give a role a block on one model. The test database carries only the install
    defaults (superuser, admin, agent): any other role sees nothing until granted."""
    from apps.core.models.setting import Setting
    from apps.core.services import access
    setting = Setting.objects.filter(purpose='wc:model', parent_model=model_key).first()
    config = dict(setting.config or {})
    acc = dict(config.get('access') or {})
    acc['roles'] = {**(acc.get('roles') or {}), role: block}
    config['access'] = acc
    setting.config = config
    setting._setting_update_authorized = True
    setting.save(update_fields=['config'])
    access.clear_cache()


def _auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(user)
    token['role'] = getattr(user, 'role', 'user')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


EMPLOYEE_CONTACT = {'view': ['@all'], 'edit': ['email', 'name_first'], 'scope': {},
                    'create': False}


# ── the filter itself ───────────────────────────────────────────────────

def test_only_enumerated_fields_are_kept():
    _grant('contact', 'employee', EMPLOYEE_CONTACT)
    actor = Actor(user=Contact.objects.create(email='e1@example.com', role='employee'))
    target = Contact.objects.create(email='t1@example.com')
    kept, denied = _enumerated_edit(actor, target, 'contact',
                                    {'email': 'x@example.com', 'name_first': 'A',
                                     'name_last': 'B', 'title': 'C'})
    assert kept == {'email': 'x@example.com', 'name_first': 'A'}
    assert sorted(denied) == ['name_last', 'title']


def test_system_fields_are_written_only_by_an_admin():
    _grant('contact', 'employee', {**EMPLOYEE_CONTACT, 'edit': ['@all']})
    employee = Actor(user=Contact.objects.create(email='e3@example.com', role='employee'))
    admin = Actor(user=Contact.objects.create(email='a1@example.com', role='admin'))
    target = Contact.objects.create(email='t2@example.com')
    payload = {field: 1 for field in SYSTEM_ONLY_FIELDS if field not in ('id', 'version')}
    kept, denied = _enumerated_edit(employee, target, 'contact', payload)
    assert kept == {} and set(denied) == set(payload)
    kept, _ = _enumerated_edit(admin, target, 'contact', {'ida': 'C-100'})
    assert kept == {'ida': 'C-100'}


def test_envelope_keys_and_signals_pass():
    _grant('contact', 'employee', EMPLOYEE_CONTACT)
    actor = Actor(user=Contact.objects.create(email='e2@example.com', role='employee'))
    target = Contact.objects.create(email='t3@example.com')
    kept, _ = _enumerated_edit(actor, target, 'contact',
                               {'model_name': 'contact', 'id': target.pk, 'version': 1,
                                '_dirty': True})
    assert kept == {'model_name': 'contact', 'id': target.pk, 'version': 1, '_dirty': True}


def test_a_strange_signal_is_refused():
    from common.schemas.carrier import CarrierError
    admin = Actor(user=Contact.objects.create(email='a2@example.com', role='admin'))
    with pytest.raises(CarrierError):
        _enumerated_edit(admin, Contact(), 'contact', {'__dict__': {'is_superuser': True}})


def test_a_login_with_no_role_writes_only_the_self_fields_of_its_own_contact():
    me = Contact.objects.create(email='me@example.com', role='user')
    kept, denied = _enumerated_edit(Actor(user=me), me, 'contact',
                                    {'name_last': 'New', 'customer_id': 5})
    assert kept == {'name_last': 'New'}
    assert denied == ['customer_id']


# ── through the door ────────────────────────────────────────────────────

class TestWcapiSave:

    def test_employee_may_not_set_authority_fields_on_a_contact(self, django_user_model):
        """is_superuser is authority, not a field: the contact guard refuses it outright,
        and the refusal is whole — the permitted field does not land either."""
        _grant('contact', 'employee', EMPLOYEE_CONTACT)
        employee = django_user_model.objects.create_user(
            email="emp@example.com", password=TEST_PASSWORD, role="employee")
        target = django_user_model.objects.create_user(
            email="target@example.com", password=TEST_PASSWORD, role="user",
            security_level=1)   # as the save door stamps a new contact; 0 is staff-only
        resp = _auth_client(employee).post("/wcapi/save/contact/", {
            "model_name": "contact", "id": target.pk,
            "email": "updated@example.com", "is_superuser": True,
        }, format="json")

        assert resp.status_code == 403, resp.data
        assert resp.data["error"]["code"] == "contact_account_guard"
        assert resp.data["error"]["details"] == "is_superuser"
        target.refresh_from_db()
        assert target.is_superuser is False
        assert target.email == "target@example.com"

    def test_admin_save_can_set_any_field(self, django_user_model):
        admin = django_user_model.objects.create_superuser(
            email="admin@example.com", password=TEST_PASSWORD)
        target = django_user_model.objects.create_user(
            email="target2@example.com", password=TEST_PASSWORD, role="user")
        resp = _auth_client(admin).post("/wcapi/save/contact/", {
            "model_name": "contact", "id": target.pk,
            "email": "admin-updated@example.com", "role": "employee",
        }, format="json")
        assert resp.status_code == 200, resp.data
        target.refresh_from_db()
        assert target.email == "admin-updated@example.com"
        assert target.role == "employee"

    def test_a_person_may_not_raise_their_own_role(self, django_user_model):
        """A person reaches their own contact (Bill, 2026-09-23); reaching it is not
        authority over it."""
        user = django_user_model.objects.create_user(
            email="user@example.com", password=TEST_PASSWORD, role="user")
        resp = _auth_client(user).post("/wcapi/save/contact/", {
            "model_name": "contact", "id": user.pk, "role": "admin",
        }, format="json")
        assert resp.status_code == 403, resp.data
        user.refresh_from_db()
        assert user.role == "user"

    def test_a_field_the_role_cannot_edit_is_ignored_not_refused(self, django_user_model):
        """Bill, 2026-09-20: *"If it is not enumerated as edit, the back end should never
        read it as being there regardless of if it is in the payload or not."* A form
        round-trips every field it was served, and view is a superset of edit — refusing
        those echoes would reject every save from the screen."""
        _grant('contact', 'employee', EMPLOYEE_CONTACT)
        employee = django_user_model.objects.create_user(
            email="emp2@example.com", password=TEST_PASSWORD, role="employee")
        target = django_user_model.objects.create_user(
            email="t4@example.com", password=TEST_PASSWORD, role="user",
            name_last="Unchanged", security_level=1)
        resp = _auth_client(employee).post("/wcapi/save/contact/", {
            "model_name": "contact", "id": target.pk,
            "name_first": "NewFirst",          # enumerated
            "name_last": "ShouldNotApply",     # not enumerated, not authority
        }, format="json")
        assert resp.status_code == 200, resp.data
        target.refresh_from_db()
        assert target.name_first == "NewFirst"
        assert target.name_last == "Unchanged"
