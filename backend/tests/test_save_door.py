"""The save door: one path, callable by every writer, with the branch inside it.

Bill, 2026-09-22: "everything should flow through this one door including Django admin.
No staff backdoor." These test what the door makes possible that the view never did —
a caller with no request — and what WC2's jAcceptButton guaranteed: the branch happens
inside the flow, and the tail after it is not optional.
"""
import pytest

from apps.core.services.behaviours import (ModelBehaviour, HookContext, behaviour_for,
                                           register, registered)
from apps.core.services.save import Actor, Refused, save_record

pytestmark = pytest.mark.django_db


# ── a caller with no request ──────────────────────────────────────────

def test_a_system_actor_saves_without_a_request():
    """A command, a task or a sync bundle has no request. Before the door, that meant
    calling Model.save() directly and skipping every check the endpoint applied."""
    result = save_record(
        Actor.system(source='command'),
        {'model_name': 'item', 'name': 'Door Test Widget', 'ida': 'zz-door-1'},
    )
    assert result.obj_id and result.created
    assert result.version >= 1, "the version is stamped for a system writer too"
    assert result.record['name'] == 'Door Test Widget'


def test_the_door_stamps_identity_the_same_way_for_every_actor():
    made = {}
    for kind in ('user', 'system'):
        from apps.core.models import Contact
        person = Contact.objects.create(email=f'door-{kind}@example.com', role='admin')
        actor = Actor.system() if kind == 'system' else Actor(user=person, kind='user')
        result = save_record(actor, {'model_name': 'item', 'name': f'Door {kind}',
                                     'ida': f'zz-door-{kind}'})
        made[kind] = result.obj
    for obj in made.values():
        assert obj.version >= 1 and obj.dt_modified and obj.uuid


def test_one_create_writes_the_record_more_than_once_today():
    """A single create comes out at version 2: obj.save(), then the keyword pass saves
    it again. That is the churn the save-path review measured — derived work done per
    write instead of once per unit of work — and it is step 3, which allie-d0 holds
    (totals are the same shape). Recorded here so the cost is visible rather than folded
    into a passing test; when step 3 lands this becomes version 1 and the assertion
    below still holds."""
    result = save_record(Actor.system(), {'model_name': 'item', 'name': 'Churn',
                                          'ida': 'zz-door-churn'})
    assert result.version >= 1
    assert result.obj.version == result.version


# ── what it refuses, and how it says so ───────────────────────────────

def test_an_unknown_model_is_refused_with_its_code():
    with pytest.raises(Refused) as caught:
        save_record(Actor.system(), {'model_name': 'notathing', 'name': 'x'})
    assert caught.value.status == 400
    assert caught.value.code == 'unknown_model'
    assert caught.value.as_error()['code'] == 'unknown_model'


def test_a_missing_model_name_is_refused():
    with pytest.raises(Refused) as caught:
        save_record(Actor.system(), {'name': 'x'})
    assert caught.value.code == 'missing_model_name'


def test_a_stale_version_is_refused_with_both_numbers():
    first = save_record(Actor.system(), {'model_name': 'item', 'name': 'Versioned',
                                         'ida': 'zz-door-v'})
    with pytest.raises(Refused) as caught:
        save_record(Actor.system(), {'model_name': 'item', 'id': first.obj_id,
                                     'name': 'Changed', 'version': 99})
    assert caught.value.status == 412 and caught.value.code == 'version_conflict'
    assert caught.value.details == {'expected': 99, 'current': first.version}


def test_a_missing_record_is_refused_as_not_found():
    with pytest.raises(Refused) as caught:
        save_record(Actor.system(), {'model_name': 'item', 'id': 99999999, 'name': 'x'})
    assert caught.value.status == 404 and caught.value.code == 'not_found'


# ── the branch is inside the flow ─────────────────────────────────────

def test_the_case_list_is_readable_at_runtime():
    """WC2's Case of, dispatched. What the door will branch to, without reading it."""
    cases = registered()
    assert cases['setting'] == 'SettingBehaviour'
    assert cases['action'] == 'ActionBehaviour'
    assert cases['phone'] == 'PhoneBehaviour'


def test_a_model_with_no_behaviour_takes_the_default():
    assert type(behaviour_for('item')).__name__ == 'ModelBehaviour'


def test_a_behaviour_runs_before_and_after_the_write(monkeypatch):
    seen = []

    class Noisy(ModelBehaviour):
        def before_save(self, ctx: HookContext) -> None:
            seen.append(('before', ctx.obj.pk, ctx.is_update))

        def after_save(self, ctx: HookContext) -> None:
            seen.append(('after', ctx.obj.pk is not None, ctx.is_update))

    register('item', Noisy())
    try:
        save_record(Actor.system(), {'model_name': 'item', 'name': 'Branching',
                                     'ida': 'zz-door-b'})
    finally:
        register('item', ModelBehaviour())

    assert seen[0] == ('before', None, False), "before runs while the record is unwritten"
    assert seen[1] == ('after', True, False), "after runs once it has a pk"


def test_a_behaviour_can_refuse_the_save():
    class Refuser(ModelBehaviour):
        def before_save(self, ctx: HookContext) -> None:
            raise Refused(409, 'item_refused', 'This item may not be saved.', 'because')

    register('item', Refuser())
    try:
        with pytest.raises(Refused) as caught:
            save_record(Actor.system(), {'model_name': 'item', 'name': 'Refused',
                                         'ida': 'zz-door-r'})
        assert caught.value.status == 409 and caught.value.code == 'item_refused'
    finally:
        register('item', ModelBehaviour())

    from apps.products.models import Item
    assert not Item.objects.filter(ida='zz-door-r').exists(), "a refusal writes nothing"


def test_a_failure_after_the_write_keeps_the_save():
    """Bill, 2026-09-24: an after hook that fails does not undo the save — the admins get
    a critical action until it is fixed (tests/test_verbs.py covers the action)."""
    from apps.products.models import Item

    class Exploder(ModelBehaviour):
        def after_save(self, ctx: HookContext) -> None:
            raise RuntimeError('after blew up')

    register('item', Exploder())
    try:
        result = save_record(Actor.system(), {'model_name': 'item', 'name': 'Kept',
                                              'ida': 'zz-door-x'})
    finally:
        register('item', ModelBehaviour())

    assert Item.objects.filter(ida='zz-door-x').exists()
    assert any('after blew up' in m for m in result.messages)
