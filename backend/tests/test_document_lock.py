"""A document locked by hand (Bill, 2026-09-29).

A person locks it; the lock records who and when (metadata.health.lock), status is 'locked';
an admin or superuser unlocks it and the status comes back. While locked only comments and
payments go through. Spec: ~/Allie/readmes/assessments/2026-09-29-document-lock-spec.md
"""
import pytest

from apps.core.models import Contact
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.core.services.verbs import run_command
from apps.transactions.models import Order, OrderLine

pytestmark = pytest.mark.django_db


def _grant_sales_on_orders():
    from apps.core.models.setting import Setting
    from apps.core.services import access
    setting = Setting.objects.filter(purpose='wc:model', parent_model='order').first()
    config = dict(setting.config or {})
    acc = dict(config.get('access') or {})
    acc['roles'] = {**(acc.get('roles') or {}),
                    'sales': {'view': ['id', 'status', 'attention'], 'edit': ['attention'],
                              'scope': {}, 'create': True, 'delete': False}}
    config['access'] = acc
    setting.config = config
    setting._setting_update_authorized = True
    setting.save(update_fields=['config'])
    access.clear_cache()


@pytest.fixture
def people():
    _grant_sales_on_orders()
    def person(email, **kw):
        return Actor(user=Contact.objects.create(email=email, name_first=email.split('@')[0], **kw))
    return {'sales': person('sam@example.com', role='sales'),
            'admin': person('ada@example.com', role='admin'),
            'su': person('su@example.com', is_superuser=True, is_staff=True)}


@pytest.fixture
def order():
    return Order.objects.create(status='open', security_level=1)


def _lock(actor, order, reason='Disputed pricing'):
    return run_command(actor, 'lock', 'order', order.pk, {'reason': reason})


def test_a_lock_records_who_when_why_and_the_status_it_replaced(people, order):
    _lock(people['admin'], order)
    order.refresh_from_db()
    lock = order.metadata['health']['lock']
    assert order.status == 'locked'
    assert lock['by']['name'] == 'ada' and lock['reason'] == 'Disputed pricing'
    assert lock['status_before'] == 'open' and lock['dt'] > 0


def test_a_locked_document_refuses_edits_with_who_and_why(people, order):
    _lock(people['admin'], order)
    order.refresh_from_db()
    with pytest.raises(Refused) as refused:
        save_record(people['admin'], {'model_name': 'order', 'id': order.pk, 'attention': 'x'})
    assert refused.value.status == 409 and refused.value.code == 'document_locked'
    assert 'ada' in refused.value.message and 'Disputed pricing' in refused.value.message


def test_comments_still_go_through(people, order):
    _lock(people['admin'], order)
    order.refresh_from_db()
    save_record(people['admin'], {'model_name': 'order', 'id': order.pk,
                                  'comments': {'internal': [{'mgs': 'Waiting on the customer'}]}})


def test_a_locked_documents_lines_are_not_written(people, order):
    line = OrderLine.objects.create(order=order)
    _lock(people['admin'], order)
    with pytest.raises(Refused) as refused:
        save_record(people['admin'], {'model_name': 'order_line', 'id': line.pk,
                                      'quantity': {'active': 5}})
    assert refused.value.code == 'document_locked'


def test_commands_are_refused_but_unlock(people, order):
    _lock(people['admin'], order)
    with pytest.raises(Refused) as refused:
        run_command(people['admin'], 'convert', 'order', order.pk, {'to': 'invoice'})
    assert refused.value.code == 'document_locked'


def test_unlock_is_for_admins_and_superusers_and_restores_the_status(people, order):
    _lock(people['admin'], order)
    with pytest.raises(Refused) as refused:
        run_command(people['sales'], 'unlock', 'order', order.pk, {'reason': 'fixed'})
    assert refused.value.code == 'unlock_not_permitted'
    run_command(people['su'], 'unlock', 'order', order.pk, {'reason': 'Price agreed'})
    order.refresh_from_db()
    assert order.status == 'open'
    health = order.metadata['health']
    assert 'lock' not in health or not health['lock']
    closed = health['lock_history'][-1]
    assert closed['reason'] == 'Disputed pricing' and closed['unlock_reason'] == 'Price agreed'


def test_a_lock_needs_a_reason_and_cannot_be_doubled(people, order):
    with pytest.raises(Refused) as refused:
        run_command(people['admin'], 'lock', 'order', order.pk, {})
    assert refused.value.code == 'reason_required'
    _lock(people['admin'], order)
    with pytest.raises(Refused) as refused:
        _lock(people['admin'], order)
    assert refused.value.code in ('already_locked', 'document_locked')


def test_status_locked_and_the_lock_object_are_set_only_by_the_commands(people, order):
    with pytest.raises(Refused) as refused:
        save_record(people['su'], {'model_name': 'order', 'id': order.pk, 'status': 'locked'})
    assert refused.value.code == 'lock_by_command'
    with pytest.raises(Refused) as refused:
        save_record(people['su'], {'model_name': 'order', 'id': order.pk,
                                   'metadata': {'health': {'lock': {'reason': 'x'}}}})
    assert refused.value.code == 'lock_by_command'


def test_any_staff_who_may_edit_the_document_locks_it(people, order):
    _lock(people['sales'], order)
    order.refresh_from_db()
    assert order.status == 'locked' and order.metadata['health']['lock']['by']['name'] == 'sam'
