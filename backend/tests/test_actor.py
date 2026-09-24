"""The Actor: the one principal every door and every access check takes (read-door step 1).

Bill, 2026-09-23: only our own code is privileged; a sync bundle is guarded by its
Connection's role; a Connection holds a role in code plus the ids it speaks for — never
admin or superuser; an inactive Connection holds no role.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.core.models import Contact
from apps.core.services import access
from apps.core.services.door import Actor, as_actor
from apps.core.services.record_serialize import visible_queryset
from apps.orgs.models import OrgBase
from apps.sync.models.connection import Connection
from apps.transactions.models import Purchase

pytestmark = pytest.mark.django_db


def _connection(role='vendor', scope=None, status='active', is_active=True):
    return Connection.objects.create(name=f'conn-{role}', type='api', status=status,
                                     is_active=is_active, role=role, scope=scope or {})


def _grant(model_key, role, block):
    from apps.core.models.setting import Setting
    setting = Setting.objects.filter(purpose='wc:model', parent_model=model_key).first()
    config = dict(setting.config or {})
    acc = dict(config.get('access') or {})
    acc['roles'] = {**(acc.get('roles') or {}), role: block}
    config['access'] = acc
    setting.config = config
    setting._setting_update_authorized = True
    setting.save(update_fields=['config'])
    access.clear_cache()


# ── construction fails fast ─────────────────────────────────────────────

def test_an_unknown_kind_cannot_be_built():
    with pytest.raises(ValueError):
        Actor(kind='sytem')


def test_a_sync_actor_needs_its_connection_and_carries_no_user():
    with pytest.raises(ValueError):
        Actor(kind='sync')
    with pytest.raises(ValueError):
        Actor(kind='sync', connection=object(), user=object())


def test_only_system_is_privileged():
    assert Actor.system().is_guarded is False
    for actor in (Actor(user=object()), Actor(kind='staff', user=object()),
                  Actor.anonymous(), Actor.for_connection(object())):
        assert actor.is_guarded is True


def test_access_checks_refuse_a_bare_user():
    """A caller not yet converted fails loudly instead of being mis-scoped."""
    with pytest.raises(TypeError):
        as_actor(Contact(email='bare@example.com'))


# ── a Connection is guarded by its role ─────────────────────────────────

def test_a_sync_actor_links_to_no_contact():
    """A sync write must never be linked to whichever contact shares an id."""
    conn = _connection()
    assert Actor.for_connection(conn).user_id is None


def test_a_connection_role_is_its_actor_role():
    assert Actor.for_connection(_connection('vendor')).role == 'vendor'
    assert Actor.for_connection(_connection('rep')).role == 'rep'


def test_an_inactive_connection_holds_no_role():
    assert Actor.for_connection(_connection(status='paused')).role is None
    assert Actor.for_connection(_connection(is_active=False)).role is None


@pytest.mark.parametrize('role', ['admin', 'superuser', 'agent', 'wizard'])
def test_a_connection_cannot_hold_authority_roles(role):
    with pytest.raises(ValidationError):
        _connection(role)


@pytest.mark.parametrize('scope', [{'vendor': ['12']}, {'tenant': [1]}, {'vendor': 12},
                                   {'vendor': [True]}])
def test_a_connection_scope_is_org_types_and_integer_ids(scope):
    with pytest.raises(ValidationError):
        _connection(scope=scope)


def test_a_sync_actor_sees_only_the_rows_its_scope_names():
    """Gate 3 for a Connection: the same scope rule a vendor login uses, resolved against
    the ids the Connection speaks for."""
    _grant('purchase', 'vendor', {'view': ['id', 'status', 'vendor_id'], 'edit': [], 'create': False,
                                  'scope': {'vendor_id__in': '$user.org_ids.vendor'}})
    ours = OrgBase.objects.create(company='Our Vendor', org_type='vendor')
    theirs = OrgBase.objects.create(company='Other Vendor', org_type='vendor')
    mine = Purchase.objects.create(vendor_id=ours.pk, security_level=1)
    Purchase.objects.create(vendor_id=theirs.pk, security_level=1)

    actor = Actor.for_connection(_connection('vendor', {'vendor': [ours.pk]}))
    _cls, qs = visible_queryset('purchase', actor=actor)
    assert list(qs.values_list('pk', flat=True)) == [mine.pk]


def test_a_connection_with_no_role_sees_nothing():
    _grant('purchase', 'vendor', {'view': ['id', 'status'], 'edit': [], 'scope': {}})
    Purchase.objects.create(security_level=1)
    actor = Actor.for_connection(_connection(role=''))
    assert not visible_queryset('purchase', actor=actor)[1].exists()


# ── one admin test ──────────────────────────────────────────────────────

def test_admin_is_a_logins_own_authority_never_borrowed():
    admin = Contact.objects.create(email='adm@example.com', role='admin')
    agent = Contact.objects.create(email='agt@example.com', role='agent')
    assert access.is_admin(Actor(user=admin)) is True
    assert access.is_admin(Actor(user=agent, acting_as='admin')) is False   # borrowed
    assert access.is_admin(Actor.for_connection(_connection('employee'))) is False
    assert access.is_admin(Actor.anonymous()) is False
