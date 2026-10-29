"""Select lists support, they do not police (Bill, 2026-10-29): each model's lists live in its
definition; a person is asked before a new value joins a list, code adds it, staff edit lists."""
import pytest
from django.utils.crypto import get_random_string
from rest_framework.test import APIClient

from apps.core.models import Action, Setting
from apps.core.models.log import Log
from apps.core.services import access, select_lists
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db


@pytest.fixture
def action_lists():
    Setting.objects.filter(purpose='wc:model', parent_model='action').delete()
    make_setting(purpose='wc:model', parent_model='action', name='action', config={
        'access': access.default_access('action'),
        'selectlists': {'purpose': [{'value': 'alice', 'label': 'Alice'}],
                        'kanban_column': [{'value': 'Backlog', 'label': 'Backlog'},
                                          {'value': 'Complete', 'label': 'Complete'}]}})
    access.clear_cache()


def _person(django_user_model, *, staff):
    person = django_user_model.objects.create_user(
        email=f'{get_random_string(8).lower()}@example.com', password=get_random_string(20),
        role='admin', is_staff=staff)
    return person


def _as(person, data):
    return save_record(Actor(user=person, kind='user', source='wcapi'), data, model_key='action')


def test_code_adds_a_new_value_and_logs_it(action_lists):
    save_record(Actor.system(), {'action': {'en': 'from code'}, 'kanban_column': 'Review'},
                model_key='action')
    assert 'Review' in select_lists.lists('action')['kanban_column']
    assert Log.objects.filter(purpose='audit', action='list_changed',
                              config__name='action.kanban_column').exists()


def test_a_person_is_asked_first(action_lists, django_user_model):
    staff = _person(django_user_model, staff=True)
    with pytest.raises(Refused) as refused:
        _as(staff, {'action': {'en': 'new column'}, 'kanban_column': 'Review'})
    assert refused.value.code == 'value_not_listed'
    assert refused.value.details['unlisted'] == {'kanban_column': 'Review'}
    assert refused.value.details['may_add'] == {'kanban_column': True}
    assert 'Add it to the list' in refused.value.message
    select_lists.add_value('action', 'kanban_column', 'Review', actor=Actor(user=staff, kind='user'))
    _as(staff, {'action': {'en': 'new column'}, 'kanban_column': 'Review'})


def test_only_staff_change_lists(action_lists, django_user_model):
    clerk = _person(django_user_model, staff=False)
    with pytest.raises(Refused) as refused:
        _as(clerk, {'action': {'en': 'x'}, 'kanban_column': 'Review'})
    assert refused.value.details['may_add'] == {'kanban_column': False}
    assert 'ask a staff member' in refused.value.message
    with pytest.raises(Refused, match='Only staff'):
        select_lists.add_value('action', 'kanban_column', 'Review', actor=Actor(user=clerk, kind='user'))


def test_the_list_endpoint_adds_and_replaces(action_lists, django_user_model):
    client = APIClient()
    client.force_authenticate(_person(django_user_model, staff=True))
    r = client.post('/wcapi/_selectlist/', {'model': 'action', 'field': 'kanban_column', 'add': 'Review'},
                    format='json')
    assert r.status_code == 200, r.content
    r = client.post('/wcapi/_selectlist/', {'model': 'action', 'field': 'kanban_column', 'options': [
        {'value': 'Complete', 'label': 'Done'}, {'value': 'Backlog', 'label': 'Backlog'}]}, format='json')
    assert [o['value'] for o in r.json()['data']['options']] == ['Complete', 'Backlog']
    client.force_authenticate(_person(django_user_model, staff=False))
    r = client.post('/wcapi/_selectlist/', {'model': 'action', 'field': 'kanban_column', 'add': 'X'},
                    format='json')
    assert r.status_code == 403


def test_a_stored_value_is_left_alone_and_empty_is_free(action_lists):
    old = Action.objects.create(action={'en': 'older'}, kanban_column='legacy')
    save_record(Actor.system(), {'id': old.pk, 'status': 'open'}, model_key='action')
    assert 'legacy' not in select_lists.lists('action')['kanban_column']
    save_record(Actor.system(), {'action': {'en': 'no purpose'}, 'purpose': ''}, model_key='action')
