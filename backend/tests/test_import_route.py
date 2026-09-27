"""Import on one route (plan §17.12–13; Bill, 2026-09-26).

Every row carries a uuid: known → update, unknown → a new record that keeps it. Alice's pre-import
changes nothing and shows look-alikes with their id, ida and uuid. Alice and Athena approve the
exact content. A superuser imports, all or nothing.
"""
import uuid

import pytest
from django.test import override_settings

from apps.core.models import Contact
from apps.products.models import Item
from apps.sync.models import Bundle, Connection

pytestmark = pytest.mark.django_db

ALICE, ATHENA = 'alice@wc.test', 'athena@wc.test'


@pytest.fixture(autouse=True)
def agents(settings):
    settings.ALICE_WC_EMAIL, settings.ATHENA_WC_EMAIL = ALICE, ATHENA


def _client(client, django_user_model, email, **kw):
    user = django_user_model.objects.create_user(email=email, password='x', username='', **kw)
    client.force_login(user)
    return client


def _bundle(records):
    conn = Connection.objects.create(name='Outside cleanup', type='manual')
    return Bundle.objects.create(connection=conn, direction='push', model_name='item',
                                 payload={'records': records})


def _cmd(client, bundle, verb):
    r = client.post(f'/wcapi/bundle/{bundle.pk}/{verb}/', {}, content_type='application/json')
    body = r.json()
    return r.status_code, (body.get('data') or {}).get('result', body.get('data')), body


def _approve_both(client, django_user_model, bundle):
    for email in (ALICE, ATHENA):
        client.logout()
        _client(client, django_user_model, email, role='agent')
        status, _, body = _cmd(client, bundle, 'approve')
        assert status == 200, body


def test_the_door_matches_by_uuid_and_a_new_record_keeps_its_uuid():
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    known = Item.objects.create(name='Known', sku='K-1')
    save_record(Actor.system(), {'model_name': 'item', 'uuid': str(known.uuid), 'name': 'Known (renamed)'})
    known.refresh_from_db()
    assert known.name == 'Known (renamed)'
    fresh = uuid.uuid4()
    result = save_record(Actor.system(), {'model_name': 'item', 'uuid': str(fresh), 'name': 'Fresh'})
    item = Item.objects.get(pk=result.obj_id)
    assert item.uuid == fresh and item.ida, 'a new record keeps its uuid; id and ida are assigned'


def test_a_bad_uuid_is_refused():
    from apps.core.services.door import Actor, Refused
    from apps.core.services.save import save_record
    with pytest.raises(Refused, match='is not a uuid'):
        save_record(Actor.system(), {'model_name': 'item', 'uuid': 'not-a-uuid', 'name': 'x'})


def test_the_pre_import_changes_nothing_and_shows_look_alikes(client, django_user_model):
    known = Item.objects.create(name='Widget', sku='W-100')
    b = _bundle([{'model_name': 'item', 'uuid': str(known.uuid), 'name': 'Widget v2'},
                 {'model_name': 'item', 'uuid': str(uuid.uuid4()), 'name': 'Widget', 'sku': 'W-101'}])
    _client(client, django_user_model, 'boss@wc.test', is_superuser=True, role='admin')
    count = Item.objects.count()
    status, result, body = _cmd(client, b, 'preview')
    assert status == 200, body
    assert Item.objects.count() == count and Item.objects.get(pk=known.pk).name == 'Widget', 'rolled back'
    assert result['summary']['update'] == 1 and result['summary']['new'] == 1
    look = result['rows'][1]['look_alikes'][0]
    assert (look['id'], look['uuid'], look['matched_on']) == (known.pk, str(known.uuid), 'name')


def test_alice_holds_look_alikes_and_athena_refuses_authority_fields(client, django_user_model):
    Item.objects.create(name='Gear', sku='G-1')
    b = _bundle([{'model_name': 'item', 'uuid': str(uuid.uuid4()), 'name': 'Gear', 'sku': 'G-2'}])
    _client(client, django_user_model, 'boss2@wc.test', is_superuser=True, role='admin')
    _cmd(client, b, 'preview')
    client.logout(); _client(client, django_user_model, ALICE, role='agent')
    status, _, body = _cmd(client, b, 'approve')
    assert status == 409 and body['error']['code'] == 'look_alikes'

    b2 = _bundle([{'model_name': 'contact', 'uuid': str(uuid.uuid4()), 'email': 'new@x.test', 'role': 'admin'}])
    client.logout(); _client(client, django_user_model, 'boss3@wc.test', is_superuser=True, role='admin')
    _cmd(client, b2, 'preview')
    client.logout(); _client(client, django_user_model, ATHENA, role='agent')
    status, _, body = _cmd(client, b2, 'approve')
    assert status == 409 and body['error']['code'] in ('authority_fields', 'preview_refusals')


def test_import_needs_both_approvals_of_this_content_and_a_superuser(client, django_user_model):
    known = Item.objects.create(name='Bolt', sku='B-1')
    fresh = uuid.uuid4()
    b = _bundle([{'model_name': 'item', 'uuid': str(known.uuid), 'name': 'Bolt M8'},
                 {'model_name': 'item', 'uuid': str(fresh), 'name': 'Nut M8', 'sku': 'N-8'}])
    boss = 'boss4@wc.test'
    _client(client, django_user_model, boss, is_superuser=True, role='admin')
    status, _, body = _cmd(client, b, 'import')
    assert status == 409 and body['error']['code'] == 'approval_required'
    _cmd(client, b, 'preview')
    _approve_both(client, django_user_model, b)

    client.logout(); _client(client, django_user_model, 'clerk@wc.test', role='admin')   # admin, not superuser
    status, _, body = _cmd(client, b, 'import')
    assert status == 403 and body['error']['code'] == 'superuser_required'

    client.logout(); client.force_login(django_user_model.objects.get(email=boss))
    status, result, body = _cmd(client, b, 'import')
    assert status == 200 and (result['created'], result['updated']) == (1, 1), body
    assert Item.objects.get(pk=known.pk).name == 'Bolt M8'
    assert Item.objects.get(uuid=fresh).sku == 'N-8'


def test_a_changed_bundle_voids_its_approvals(client, django_user_model):
    b = _bundle([{'model_name': 'item', 'uuid': str(uuid.uuid4()), 'name': 'Washer'}])
    boss = 'boss5@wc.test'
    _client(client, django_user_model, boss, is_superuser=True, role='admin')
    _cmd(client, b, 'preview')
    _approve_both(client, django_user_model, b)
    Bundle.objects.filter(pk=b.pk).update(payload={'records': [
        {'model_name': 'item', 'uuid': str(uuid.uuid4()), 'name': 'Something else'}]})
    client.logout(); client.force_login(django_user_model.objects.get(email=boss))
    status, _, body = _cmd(client, b, 'import')
    assert status == 409 and body['error']['code'] == 'approval_required'


def test_one_refused_row_imports_nothing(client, django_user_model, monkeypatch):
    from apps.core.services.door import Refused
    from apps.sync.services import bundle_import
    a, z = uuid.uuid4(), uuid.uuid4()
    b = _bundle([{'model_name': 'item', 'uuid': str(a), 'name': 'First'},
                 {'model_name': 'item', 'uuid': str(z), 'name': 'Second'}])
    boss = 'boss6@wc.test'
    _client(client, django_user_model, boss, is_superuser=True, role='admin')
    _cmd(client, b, 'preview')
    _approve_both(client, django_user_model, b)
    real = bundle_import._row_for_door

    def refuse_second(row):
        if row['uuid'] == str(z):
            raise Refused(400, 'test_refusal', 'refused for the test', {})
        return real(row)
    monkeypatch.setattr(bundle_import, '_row_for_door', refuse_second)
    client.logout(); client.force_login(django_user_model.objects.get(email=boss))
    status, _, body = _cmd(client, b, 'import')
    assert status == 400 and 'Row 1' in body['message'] and 'Nothing was imported' in body['message']
    assert not Item.objects.filter(uuid__in=[a, z]).exists()


def test_lines_match_by_uuid_so_a_second_import_adds_nothing():
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Order, OrderLine
    buyer = OrgBase.objects.create(company='Line Buyer', org_type='customer', is_active=True)
    order_uuid, line_uuid = uuid.uuid4(), uuid.uuid4()
    row = {'model_name': 'order', 'uuid': str(order_uuid), 'customer_id': buyer.pk,
           'lines': [{'uuid': str(line_uuid), 'quantity': {'active': 2}, 'price': {'unit': 5.0}}]}
    save_record(Actor.system(), dict(row))
    save_record(Actor.system(), dict(row, lines=[dict(row['lines'][0], quantity={'active': 3})]))
    order = Order.objects.get(uuid=order_uuid)
    lines = OrderLine.objects.filter(order=order)
    assert lines.count() == 1 and lines.get().uuid == line_uuid
    assert lines.get().quantity.get('active') == 3


def test_a_hand_written_approval_does_not_count(client, django_user_model):
    """Fable: bundle.config is editable, so an approval must be one the route signed."""
    from apps.sync.services.bundle_import import _records, content_hash
    b = _bundle([{'model_name': 'item', 'uuid': str(uuid.uuid4()), 'name': 'Forged'}])
    h = content_hash(b, _records(b))
    forged = {'content_hash': h, 'approvals': {n: {'content_hash': h} for n in ('alice', 'athena')}}
    Bundle.objects.filter(pk=b.pk).update(config={'import_run': forged})
    _client(client, django_user_model, 'boss7@wc.test', is_superuser=True, role='admin')
    status, _, body = _cmd(client, b, 'import')
    assert status == 409 and body['error']['code'] == 'approval_required'


def test_a_person_with_alices_email_is_not_alice(client, django_user_model):
    b = _bundle([{'model_name': 'item', 'uuid': str(uuid.uuid4()), 'name': 'Imposter'}])
    _client(client, django_user_model, 'boss8@wc.test', is_superuser=True, role='admin')
    _cmd(client, b, 'preview')
    client.logout(); _client(client, django_user_model, ALICE, role='admin')
    status, _, body = _cmd(client, b, 'approve')
    assert status in (403, 404) and body['error']['code'] in ('approver_required', 'not_found')


def test_a_malformed_uuid_is_refused_by_the_preview(client, django_user_model):
    b = _bundle([{'model_name': 'item', 'uuid': 'nope', 'name': 'Bad'}])
    _client(client, django_user_model, 'boss9@wc.test', is_superuser=True, role='admin')
    status, _, body = _cmd(client, b, 'preview')
    assert status == 400 and body['error']['code'] == 'bad_uuid'
