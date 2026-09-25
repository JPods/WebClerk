"""A key that is not a field is refused with coaching, never dropped (Bill, 2026-09-25).

The silent drop returned success for every UI save sent in a `record` wrapper and stored an
empty title for every card sent with the retired alias action_en.
"""
import pytest

from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record

pytestmark = pytest.mark.django_db


def _refusal(data):
    with pytest.raises(Refused) as e:
        save_record(Actor.system(), {'model_name': 'action', **data})
    return e.value


def test_a_retired_alias_is_refused_and_coached():
    r = _refusal({'action_en': 'blank card'})
    assert r.status == 400 and r.code == 'unknown_field'
    assert 'did you mean action.en' in r.message


def test_a_record_wrapper_is_refused_with_its_own_coaching():
    r = _refusal({'record': {'kanban_column': 'Doing'}})
    assert 'send the fields flat' in r.message


def test_every_unknown_key_is_named_at_once():
    r = _refusal({'bogus_one': 1, 'bogus_two': 2, 'action': {'en': 'x'}})
    assert 'bogus_one' in r.message and 'bogus_two' in r.message


def test_real_fields_and_signals_still_save():
    result = save_record(Actor.system(), {'model_name': 'action', 'action': {'en': 'real card'},
                                          '_note': 'signal'})
    from apps.core.models import Action
    rec = result.record if isinstance(result.record, dict) else {'id': result.record.pk}
    assert (Action.objects.get(pk=rec['id']).action or {}).get('en') == 'real card'


def test_a_client_naming_the_model_in_the_body_is_refused_at_the_rest_view(client, django_user_model):
    user = django_user_model.objects.create(email='unknown.keys@example.com', is_superuser=True,
                                            is_staff=True)
    client.force_login(user)
    r = client.post('/wcapi/action/', {'model_name': 'action', 'action': {'en': 'x'}},
                    content_type='application/json')
    assert r.status_code in (400, 401)
    if r.status_code == 400:
        assert 'the model is the path' in r.json()['message']
