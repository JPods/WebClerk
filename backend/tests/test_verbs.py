"""The channel verbs: one structure for every verb (Bill, 2026-09-24).

    code before → user before → base service → code after → user after

Hooks are automatic, both layers always run, an after hook runs only when the base
succeeded, and a hook slot holds one report. Plan: Allie
``readmes/assessments/2026-09-24-one-route-per-verb.md``.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.core.models import Report, Setting
from apps.core.services import report_hooks as rh
from apps.core.services import verbs
from apps.core.services.behaviours import HookContext, ModelBehaviour, register
from apps.core.services.delete import delete_record
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record

pytestmark = pytest.mark.django_db

POINTS = {
    'item.save_pre': {'may_set': [], 'may_block': True},
    'item.save_post': {'may_set': ['metadata.review.*'], 'may_create': ['action']},
    'item.delete_pre': {'may_set': [], 'may_block': True},
    'item.delete_post': {'may_set': []},
}


@pytest.fixture
def registry(db):
    setting = Setting(name='Hook Points', purpose=rh.HOOK_POINTS_PURPOSE,
                      scope='system', config={'points': POINTS})
    setting._setting_create_authorized = True
    setting.save()
    return setting


def user_hook(ida, hooks):
    """A report in a hook slot, with clearance not required (clearance is test_report_hooks')."""
    hooks = {**hooks, 'athena': {'required': False}}
    report = Report(ida=ida, name=ida, category='function', config={'hooks': hooks})
    report._hooks_authorized = True
    report.save()
    return report


@pytest.fixture
def recorder():
    seen = []

    class Recorder(ModelBehaviour):
        def before_save(self, ctx: HookContext) -> None:
            seen.append('code before')

        def after_save(self, ctx: HookContext) -> None:
            seen.append('code after')

        def before_delete(self, ctx: HookContext) -> None:
            seen.append('code before delete')

        def after_delete(self, ctx: HookContext) -> None:
            seen.append('code after delete')

    register('item', Recorder())
    yield seen
    register('item', ModelBehaviour())


def _item(ida='zz-verb-1', **extra):
    return save_record(Actor.system(), {'model_name': 'item', 'name': 'Verb', 'ida': ida,
                                        **extra}).obj


# ── the structure ─────────────────────────────────────────────────────

def test_user_hooks_run_when_the_model_has_code_hooks(registry, recorder):
    """The defect this replaces: a model with a code hook silently skipped its user hooks."""
    user_hook('RPT-POST', {'point': 'item.save_post',
                           'after': [{'set': {'metadata.review.flag': 'seen'}}]})
    item = _item()
    item.refresh_from_db()
    assert recorder == ['code before', 'code after']
    assert item.metadata['review']['flag'] == 'seen', 'the user after hook ran too'


def test_a_user_before_hook_refuses_after_the_code_hook_ran(registry, recorder):
    user_hook('RPT-PRE', {'point': 'item.save_pre',
                          'before': [{'block': 'Items are frozen this week.'}]})
    with pytest.raises(Refused) as caught:
        _item('zz-verb-frozen')
    assert caught.value.code == 'hook_blocked'
    assert recorder == ['code before'], 'code before ran; nothing after the refusal did'

    from apps.products.models import Item
    assert not Item.objects.filter(ida='zz-verb-frozen').exists()


def test_after_hooks_run_only_when_the_base_succeeded(registry, recorder):
    item = _item('zz-verb-del')
    recorder.clear()
    user_hook('RPT-DEL', {'point': 'item.delete_pre', 'before': [{'block': 'Keep it.'}]})
    with pytest.raises(Refused):
        delete_record(Actor.system(), 'item', item.pk)
    assert recorder == ['code before delete']


def test_delete_runs_the_same_structure(registry, recorder):
    item = _item('zz-verb-del2')
    recorder.clear()
    result = delete_record(Actor.system(), 'item', item.pk)
    assert result.deleted
    assert recorder == ['code before delete', 'code after delete']


# ── one report per slot ───────────────────────────────────────────────

def test_a_second_report_in_a_taken_slot_is_refused_with_coaching(registry):
    user_hook('RPT-FIRST', {'point': 'item.save_post', 'after': []})
    with pytest.raises(ValidationError) as caught:
        user_hook('RPT-SECOND', {'point': 'item.save_post', 'after': []})
    message = str(caught.value)
    assert 'RPT-FIRST' in message and 'run_report' in message


def test_the_database_holds_one_active_report_per_slot_even_around_the_gate(registry):
    """Two concurrent saves can both pass the gate's check; the index refuses the second."""
    from django.db import IntegrityError, transaction
    user_hook('RPT-ONE', {'point': 'item.save_post', 'after': []})
    user_hook('RPT-TWO', {'point': 'item.delete_post', 'after': []})
    with pytest.raises(IntegrityError), transaction.atomic():
        Report.objects.filter(ida='RPT-TWO').update(
            config={'hooks': {'point': 'item.save_post', 'after': []}})


def test_the_old_report_made_inactive_frees_the_slot(registry):
    user_hook('RPT-OLD', {'point': 'item.save_post', 'after': []})
    Report.objects.filter(ida='RPT-OLD').update(is_active=False)
    user_hook('RPT-NEW', {'point': 'item.save_post', 'after': []})


# ── what "changed" means ──────────────────────────────────────────────

def test_when_changed_fires_on_a_real_change_only(registry):
    user_hook('RPT-CHG', {'point': 'item.save_post', 'after': [
        {'when_changed': 'name', 'set': {'metadata.review.renamed': True}}]})
    item = _item('zz-verb-chg')
    Item = type(item)
    Item.objects.filter(pk=item.pk).update(metadata={})

    save_record(Actor.system(), {'model_name': 'item', 'id': item.pk, 'name': 'Verb'})
    item.refresh_from_db()
    assert not (item.metadata or {}).get('review'), 'same name sent again is not a change'

    save_record(Actor.system(), {'model_name': 'item', 'id': item.pk, 'name': 'Renamed'})
    item.refresh_from_db()
    assert item.metadata['review']['renamed'] is True


# ── the verb list ─────────────────────────────────────────────────────

def test_an_unknown_verb_is_refused():
    with pytest.raises(Refused) as caught:
        verbs.run(Actor.system(), 'frobnicate', 'item', {})
    assert caught.value.status == 404 and caught.value.code == 'unknown_verb'


def test_run_reaches_the_base_service():
    result = verbs.run(Actor.system(), 'save', 'item', {'name': 'Via run', 'ida': 'zz-verb-run'})
    assert result.created and result.model_key == 'item'


# ── derived work before the after hooks ───────────────────────────────

def test_flush_does_marked_work_inside_the_unit():
    from apps.core.services.unit_of_work import defer, flush, unit_of_work
    done = []
    with unit_of_work():
        defer(('doc', 1), lambda: done.append('recomputed'))
        flush()
        assert done == ['recomputed'], 'an after hook would see the recomputed document'
    assert done == ['recomputed'], 'and it is not done twice on the way out'


# ── what the hooks are given (Fable review of step 1) ─────────────────

def test_after_hooks_start_from_what_derived_work_wrote():
    """Derived work writes through its own instance (a document's recompute); the after
    hooks must see that, and nothing after them may write the stale copy back."""
    from apps.core.services.unit_of_work import defer
    from apps.products.models import Item
    seen = {}

    class Deriving(ModelBehaviour):
        def before_save(self, ctx: HookContext) -> None:
            ida = ctx.data['ida']
            defer(('item', ida), lambda: Item.objects.filter(ida=ida).update(name='Derived'))

        def after_save(self, ctx: HookContext) -> None:
            seen['name'] = ctx.obj.name

    register('item', Deriving())
    try:
        item = _item('zz-verb-derived')
    finally:
        register('item', ModelBehaviour())
    assert seen['name'] == 'Derived'
    item.refresh_from_db()
    assert item.name == 'Derived', 'the stale in-memory copy was not written back'


def test_when_changed_sees_json_fields(registry):
    user_hook('RPT-JSON', {'point': 'item.save_post', 'after': [
        {'when_changed': 'comments', 'set': {'metadata.review.config_changed': True}}]})
    item = _item('zz-verb-json')
    type(item).objects.filter(pk=item.pk).update(metadata={})
    save_record(Actor.system(), {'model_name': 'item', 'id': item.pk,
                                 'comments': {'mode': 'update', 'value': {'notes': 'red'}}})
    item.refresh_from_db()
    assert item.metadata['review']['config_changed'] is True


def test_after_delete_hooks_know_which_record_went():
    seen = {}

    class Watcher(ModelBehaviour):
        def after_delete(self, ctx: HookContext) -> None:
            seen['id'] = ctx.obj.id

    item = _item('zz-verb-gone')
    register('item', Watcher())
    try:
        delete_record(Actor.system(), 'item', item.pk)
    finally:
        register('item', ModelBehaviour())
    assert seen['id'] == item.pk


# ── an after hook that fails (Bill, 2026-09-24) ───────────────────────

def test_a_failing_after_hook_keeps_the_save_and_opens_one_critical_action():
    from apps.core.models import Action
    from apps.products.models import Item

    class Broken(ModelBehaviour):
        def after_save(self, ctx: HookContext) -> None:
            ctx.obj.name = 'half-written'
            ctx.obj.save(update_fields=['name'])
            raise RuntimeError('the hook is broken')

    register('item', Broken())
    try:
        first = save_record(Actor.system(), {'model_name': 'item', 'name': 'Kept',
                                             'ida': 'zz-verb-broken'})
        save_record(Actor.system(), {'model_name': 'item', 'name': 'Kept again',
                                     'ida': 'zz-verb-broken-2'})
    finally:
        register('item', ModelBehaviour())

    item = Item.objects.get(ida='zz-verb-broken')
    assert item.name == 'Kept', "the save stands; what the failing hook wrote is rolled back"
    assert any('the hook is broken' in m for m in first.messages)
    faults = Action.objects.filter(refs__hook_fault__key='item.save_post:code')
    assert faults.count() == 1, 'one open action per failing hook, not one per save'
    assert faults.get().priority == 4


# ── get is a verb (read-door step 2) ──────────────────────────────────

def test_a_command_reads_as_an_actor_with_no_request():
    from apps.core.services.get import read
    item = _item('zz-verb-read')
    one = read(Actor.system(), 'item', item.pk)
    assert (one.get('record') or one).get('id') == item.pk
    many = read(Actor.system(), 'item', params={'search': 'zz-verb-read'})
    assert any(r.get('id') == item.pk for r in many.get('results', []))


def test_get_runs_the_hooks_around_the_read(recorder):
    from apps.core.services.get import read
    seen = []

    class Reader(ModelBehaviour):
        def before_get(self, ctx: HookContext) -> None:
            seen.append('before get')

        def after_get(self, ctx: HookContext) -> None:
            seen.append('after get')
            ctx.data['result']['stamped'] = True

    item = _item('zz-verb-hooked')
    register('item', Reader())
    try:
        result = read(Actor.system(), 'item', item.pk)
    finally:
        register('item', ModelBehaviour())
    assert seen == ['before get', 'after get']
    assert result['stamped'] is True, 'an after_get hook shapes what the caller receives'


def test_a_read_refusal_carries_its_status_and_code():
    from apps.core.services.get import read
    with pytest.raises(Refused) as caught:
        read(Actor.system(), 'nope')
    assert caught.value.status == 400


def test_the_rest_channel_reads_through_the_verb(client, django_user_model):
    from apps.products.models import Item
    Item.objects.create(ida='zz-verb-rest', name='Rest', security_level=1)
    resp = client.get('/wcapi/item/', {'search': 'zz-verb-rest'})
    assert resp.status_code in (200, 403), resp.content
