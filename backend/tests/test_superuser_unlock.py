"""Superusers change every field but uuid and id; ida and system dt_ fields unlock (Bill, 2026-09-29).

"superusers should be able to edit all fields except uuid. id and ida should normally be locked,
but unlockable by superuser. If we do not have this, they will make changes in psql database."
id does not change at all ("ida is enough"). A locked field changes only when a superuser names
it in _unlock; everyone else is refused, admins included.
"""
import pytest

from apps.core.models import Action, Contact
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record

pytestmark = pytest.mark.django_db


@pytest.fixture
def actors():
    su = Contact.objects.create(email='su@example.com', is_superuser=True, is_staff=True)
    admin = Contact.objects.create(email='admin@example.com', role='admin', is_staff=True)
    return {'su': Actor(user=su), 'admin': Actor(user=admin)}


def _action():
    return Action.objects.create(status='open', security_level=1)


def test_a_superuser_changes_an_ida_they_unlock(actors):
    action = _action()
    save_record(actors['su'], {'model_name': 'action', 'id': action.pk, 'ida': 'A-FIXED',
                               '_unlock': ['ida']})
    action.refresh_from_db()
    assert action.ida == 'A-FIXED'


def test_an_ida_changed_without_unlock_is_refused(actors):
    action = _action()
    with pytest.raises(Refused) as refused:
        save_record(actors['su'], {'model_name': 'action', 'id': action.pk, 'ida': 'A-X'})
    assert refused.value.code == 'ida_locked' and '_unlock' in refused.value.message


def test_an_admin_no_longer_changes_an_ida(actors):
    action = _action()
    with pytest.raises(Refused) as refused:
        save_record(actors['admin'], {'model_name': 'action', 'id': action.pk, 'ida': 'A-Y',
                                      '_unlock': ['ida']})
    assert refused.value.code == 'unlock_superuser_only'


def test_an_echoed_ida_is_not_a_change(actors):
    action = _action()
    save_record(actors['admin'], {'model_name': 'action', 'id': action.pk, 'ida': action.ida,
                                  'status': 'active'})
    assert Action.objects.get(pk=action.pk).status == 'active'


def test_a_uuid_never_changes(actors):
    action = _action()
    with pytest.raises(Refused) as refused:
        save_record(actors['su'], {'model_name': 'action', 'id': action.pk,
                                   'uuid': '00000000-0000-0000-0000-000000000001'})
    assert refused.value.code in ('uuid_locked', 'unlock_unknown')


def test_unlock_names_only_locked_fields(actors):
    action = _action()
    for name in ('uuid', 'id', 'status', 'dt_modified'):
        with pytest.raises(Refused) as refused:
            save_record(actors['su'], {'model_name': 'action', 'id': action.pk, '_unlock': [name]})
        assert refused.value.code == 'unlock_unknown', name


def test_a_superuser_changes_a_field_no_role_lists(actors):
    """Every field but uuid and id, including the ones kept from every role's list."""
    action = _action()
    save_record(actors['su'], {'model_name': 'action', 'id': action.pk, 'health_rating': 3})
    assert Action.objects.get(pk=action.pk).health_rating == 3


def test_what_a_field_holds_is_still_checked(actors):
    """Reach is not validity: a typed envelope still refuses a key it does not declare."""
    action = _action()
    with pytest.raises(Refused):
        save_record(actors['su'], {'model_name': 'action', 'id': action.pk,
                                   'config': {'repair': {'note': 'set by hand'}}})
