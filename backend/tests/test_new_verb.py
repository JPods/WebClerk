"""The `new` verb — the backend makes the record and hands it to the front end.

Bill, 2026-09-26: POST /wcapi/<model>/ saves an empty record, populated by the model's
Setting defaults and its hooks, marked ``config.is_new``; the hooks case on the mark; the
next save removes it. Plan: Allie readmes/assessments/2026-09-26-new-verb.md.
"""
import time

import pytest

from apps.core.models import Report, Setting
from apps.core.services import report_hooks as rh
from apps.core.services import verbs
from apps.core.services.behaviours import HookContext, ModelBehaviour, register
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record

pytestmark = pytest.mark.django_db


def _new(model='item', payload=None, actor=None):
    return verbs.run(actor or Actor.system(), 'new', model, dict(payload or {}))


def _defaults(model, defaults):
    setting = Setting.objects.filter(purpose='wc:model', parent_model=model).first()
    if setting is None:
        setting = Setting(purpose='wc:model', parent_model=model, name=model, config={})
    setting.prefs = {**(setting.prefs or {}), 'defaults': defaults}
    setting._setting_update_authorized = True
    setting._setting_create_authorized = True
    setting.save()


@pytest.fixture
def naked():
    """A code hook that populates only a naked record, as Bill's case reads."""
    seen = []

    class Populate(ModelBehaviour):
        def before_save(self, ctx: HookContext) -> None:
            is_new = bool((ctx.obj.config or {}).get('is_new'))
            seen.append(is_new)
            if is_new and not ctx.obj.name:
                ctx.obj.name = 'Populated by the hook'

    register('item', Populate())
    yield seen
    register('item', ModelBehaviour())


def test_new_saves_an_empty_record_marked_new():
    result = _new()
    assert result.created and result.obj_id
    assert result.obj.config['is_new'] is True
    assert result.record['config']['is_new'] is True, 'the front end is handed the mark'


def test_the_setting_defaults_populate_it_and_offset_days_are_dates():
    _defaults('item', {'name': 'From the Setting', 'description': '', 'dt_created_offset_days': ''})
    item = _new().obj
    assert item.name == 'From the Setting'

    _defaults('action', {'dt_deadline_offset_days': 7})
    before = int(time.time() * 1000)
    action = _new('action').obj
    week = 7 * 86_400_000
    assert before + week - 5_000 <= int(action.dt_deadline) <= int(time.time() * 1000) + week


def test_the_code_hook_sees_the_mark_and_the_next_save_does_not(naked):
    item = _new().obj
    assert item.name == 'Populated by the hook'
    save_record(Actor.system(), {'model_name': 'item', 'id': item.pk, 'description': 'typed'})
    item.refresh_from_db()
    assert naked == [True, False], 'the hook ran on new with the mark, on the save without'
    assert 'is_new' not in (item.config or {}), 'the next save removes the mark'


def test_a_user_before_hook_cases_on_the_mark():
    points = {'item.save_pre': {'may_set': ['metadata.review.*'], 'may_block': True}}
    registry = Setting(name='Hook Points', purpose=rh.HOOK_POINTS_PURPOSE, scope='system',
                       config={'points': points})
    registry._setting_create_authorized = True
    registry.save()
    report = Report(ida='RPT-NEW', name='RPT-NEW', category='function', config={'hooks': {
        'point': 'item.save_pre', 'athena': {'required': False},
        'before': [{'when': {'config.is_new': True},
                    'set': {'metadata.review.populated': 'yes'}}]}})
    report._hooks_authorized = True
    report.save()

    marked = _new().obj
    assert marked.metadata['review']['populated'] == 'yes'
    plain = save_record(Actor.system(), {'model_name': 'item', 'name': 'Plain'}).obj
    assert 'populated' not in ((plain.metadata or {}).get('review') or {})


def test_the_front_ends_echo_of_the_mark_does_not_keep_it():
    item = _new().obj
    save_record(Actor.system(), {'model_name': 'item', 'id': item.pk, 'name': 'Typed',
                                 'config': {'is_new': True}})
    item.refresh_from_db()
    assert 'is_new' not in (item.config or {})


def test_a_create_through_save_is_never_marked():
    """Convert, hook actions and the admin write complete records; only `new` marks."""
    item = save_record(Actor.system(), {'model_name': 'item', 'name': 'Whole',
                                        'config': {'is_new': True}}).obj
    assert 'is_new' not in (item.config or {})


def test_new_takes_no_values_and_no_id():
    with pytest.raises(Refused) as refused:
        _new(payload={'name': 'Typed', 'description': 'x'})
    assert refused.value.status == 400 and refused.value.code == 'new_takes_no_values'
    assert 'PUT the values' in refused.value.message
    with pytest.raises(Refused) as refused:
        _new(payload={'id': 5})
    assert refused.value.code == 'id_in_new'


def test_the_routes(client, django_user_model):
    admin = django_user_model.objects.create_user(email='new-admin@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    made = client.post('/wcapi/item/', {}, content_type='application/json')
    assert made.status_code in (200, 201), made.content
    item_id = made.json()['data']['id']
    assert made.json()['data']['record']['config']['is_new'] is True

    refused = client.post('/wcapi/item/', {'name': 'x'}, content_type='application/json')
    assert refused.status_code == 400
    assert refused.json()['error']['code'] == 'new_takes_no_values'

    saved = client.put(f'/wcapi/item/{item_id}/', {'name': 'Typed'},
                       content_type='application/json')
    assert saved.status_code == 200, saved.content
    assert 'is_new' not in (saved.json()['data']['record']['config'] or {})

    not_a_command = client.post(f'/wcapi/item/{item_id}/new/', {},
                                content_type='application/json')
    assert not_a_command.status_code == 404


def test_a_model_that_cannot_exist_empty_declares_what_new_takes():
    from apps.products.models import Item
    parent, child = Item.objects.create(name='P'), Item.objects.create(name='C')
    with pytest.raises(Refused) as refused:
        _new('bill_of_material')
    assert refused.value.code == 'new_requires'
    assert refused.value.details == ['parent_item_id', 'child_item_id']
    bom = _new('bill_of_material', {'parent_item_id': parent.pk, 'child_item_id': child.pk}).obj
    assert bom.config['is_new'] is True and bom.child_item_id == child.pk
    with pytest.raises(Refused) as refused:          # only what it declares; the rest is the save
        _new('bill_of_material', {'parent_item_id': parent.pk, 'child_item_id': child.pk,
                                  'quantity': 3})
    assert refused.value.code == 'new_takes_no_values'


def test_a_line_names_its_document_and_the_route_spelling_finds_its_behaviour():
    with pytest.raises(Refused) as refused:
        _new('order_line')
    assert refused.value.code == 'new_requires' and refused.value.details == ['order_id']


def test_a_new_org_is_named_until_someone_names_it():
    customer = _new('customer').obj
    assert customer.company == 'New Customer' and customer.org_type == 'customer'


def test_a_model_that_cannot_be_saved_empty_is_coached_never_a_500():
    with pytest.raises(Refused) as refused:
        _new('item_usage')
    assert refused.value.status == 400 and refused.value.code == 'new_incomplete'


@pytest.mark.parametrize('model', ['setting', 'report', 'action', 'touch', 'phone', 'email',
                                   'document', 'item', 'contact', 'invoice', 'order', 'cash'])
def test_the_models_the_front_end_makes_can_be_made_empty(model):
    """A field turned required would make every create from the front end a 400 (Fable)."""
    made = _new(model)
    assert made.obj_id and made.obj.config['is_new'] is True


def test_a_new_cash_filled_with_money_is_seeded_and_a_payservice_cash_is_not():
    """Cash.save seeds available/tendered on an insert; under `new` the insert is empty, so
    the save that fills it seeds them — only when the Cash holds money (Fable; allie-75)."""
    from decimal import Decimal
    manual = _new('cash').obj
    save_record(Actor.system(), {'model_name': 'cash', 'id': manual.pk, 'amount': '100.00',
                                 'method': 'check'})
    manual.refresh_from_db()
    assert manual.available == Decimal('100.00') and manual.tendered == Decimal('100.00')

    card = _new('cash').obj
    save_record(Actor.system(), {'model_name': 'cash', 'id': card.pk,
                                 'purpose': 'connection-payservice', 'method': 'card'})
    card.refresh_from_db()
    assert card.available == Decimal('0') and not card.holds_money
