"""Each model's purposes are its definition's list, enforced by the door (Bill, 2026-10-28)."""
import pytest

from apps.core.models import Action, Setting
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db


@pytest.fixture
def action_purposes():
    from apps.core.services import access
    Setting.objects.filter(purpose='wc:model', parent_model='action').delete()
    make_setting(purpose='wc:model', parent_model='action', name='action', config={
        'access': access.default_access('action'),
        'selectlists': {'purpose': [{'value': 'alice', 'label': 'Alice'},
                                    {'value': 'retrospection', 'label': 'Retrospection'}]}})
    access.clear_cache()


def _save(data):
    return save_record(Actor.system(), data, model_key='action')


def test_a_listed_purpose_is_accepted(action_purposes):
    result = _save({'action': {'en': 'listed'}, 'purpose': 'retrospection'})
    assert Action.objects.get(pk=result.obj_id).purpose == 'retrospection'


def test_an_unlisted_purpose_is_refused_with_the_list(action_purposes):
    with pytest.raises(Refused) as refused:
        _save({'action': {'en': 'unlisted'}, 'purpose': 'made_up'})
    assert refused.value.code == 'purpose_not_listed'
    assert 'alice, retrospection' in refused.value.message


def test_a_stored_purpose_is_left_alone_until_rewritten(action_purposes):
    old = Action.objects.create(action={'en': 'older'}, purpose='legacy')
    _save({'id': old.pk, 'status': 'open'})                       # purpose untouched: fine
    with pytest.raises(Refused):
        _save({'id': old.pk, 'purpose': 'still_made_up'})


def test_an_empty_purpose_and_an_unlisted_model_are_not_checked(action_purposes):
    _save({'action': {'en': 'no purpose'}, 'purpose': ''})
    Setting.objects.filter(purpose='wc:model', parent_model='action').update(config={})
    from apps.core.services import access
    access.clear_cache()
    _save({'action': {'en': 'no list'}, 'purpose': 'anything'})
