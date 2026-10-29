"""Reset one part of a model's layout to the code default (Bill, 2026-10-29): staff only, the
other parts and the rest of the definition untouched, the old part kept in the Log."""
import pytest
from django.utils.crypto import get_random_string

from apps.core.models import Setting
from apps.core.models.log import Log
from apps.core.services import access, layouts
from apps.core.services.door import Actor, Refused
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db

BROKEN = {'default': {'columns': ['no_such_field']}}
MINE = {'default': {'sections': ['mine']}}


@pytest.fixture
def action_def():
    Setting.objects.filter(purpose='wc:model', parent_model='action').delete()
    d = make_setting(purpose='wc:model', parent_model='action', name='action', config={
        'access': access.default_access('action'),
        'selectlists': {'purpose': [{'value': 'alice', 'label': 'Alice'}]},
        'layout': {'list': BROKEN, 'form': MINE}})
    access.clear_cache()
    return d


def _person(django_user_model, *, staff):
    return django_user_model.objects.create_user(
        email=f'{get_random_string(8).lower()}@example.com', password=get_random_string(20),
        role='admin', is_staff=staff)


def test_staff_resets_one_part(action_def, django_user_model):
    staff = Actor(user=_person(django_user_model, staff=True), kind='user', source='wcapi')
    new = layouts.reset('action', 'list', actor=staff)
    config = Setting.objects.get(pk=action_def.pk).config
    assert new != BROKEN and config['layout']['list'] == new
    assert config['layout']['form'] == MINE
    assert config['selectlists']['purpose'][0]['value'] == 'alice'
    entry = Log.objects.filter(purpose='audit', action='layout_reset').latest('id')
    assert entry.config['changes']['list']['old'] == BROKEN


def test_only_staff_reset(action_def, django_user_model):
    person = Actor(user=_person(django_user_model, staff=False), kind='user', source='wcapi')
    with pytest.raises(Refused) as refused:
        layouts.reset('action', 'list', actor=person)
    assert refused.value.code == 'layout_edit_forbidden'
    assert Setting.objects.get(pk=action_def.pk).config['layout']['list'] == BROKEN


def test_unknown_part_is_refused(action_def):
    with pytest.raises(Refused) as refused:
        layouts.reset('action', 'menus', actor=Actor.system())
    assert refused.value.code == 'layout_part_unknown'
