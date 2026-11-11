"""Calculated fields: defined in a model's definition, worked out by the server for the page a list
returns (Bill, 2026-11-01: users insert values they want calculated in rows)."""
import secrets
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact, Setting
from apps.products.models import Item
from apps.products.models.bill_of_material import BillOfMaterial

pytestmark = pytest.mark.django_db


def _client():
    client = APIClient()
    client.force_authenticate(Contact.objects.create_superuser(
        email='t-calc@example.com', password=secrets.token_urlsafe(16)))
    return client


def _definition(model):
    return Setting.objects.filter(purpose='wc:model', parent_model=model).order_by('id').first()


def _command(client, model, verb, body):
    d = _definition(model)
    return client.post(f'/wcapi/setting/{d.id}/{verb}/', body, format='json', HTTP_HOST='localhost')


def _list(client, model, ids):
    r = client.get(f'/wcapi/{model}/', {'id__in': ','.join(str(i) for i in ids)}, HTTP_HOST='localhost')
    assert r.status_code == 200, r.content
    return {row['id']: row for row in r.json()['data']['results']}


@pytest.fixture
def boms():
    a, b = (Item.objects.create(ida=f't-calc-{n}', name=n, kind=Item.KIND_PHYSICAL) for n in 'AB')
    for i, q in enumerate(('2', '3')):
        part = Item.objects.create(ida=f't-calc-part{i}', name=f'part{i}', kind=Item.KIND_PHYSICAL)
        BillOfMaterial.objects.create(parent_item=a, child_item=part, quantity=Decimal(q), sequence=i,
                                      op_data={'run_time': 10 * (i + 1)})
    return a, b


def test_a_list_shows_what_the_server_works_out(boms):
    a, b = boms
    client = _client()
    for name, spec in (('parts_qty', {'calc': 'sum', 'of': 'quantity', 'over': 'bom_parent'}),
                       ('parts', {'calc': 'count', 'over': 'bom_parent'})):
        r = _command(client, 'item', 'calculated', {'name': name, 'spec': spec})
        assert r.status_code == 200, r.content
    rows = _list(client, 'item', [a.id, b.id])
    assert rows[a.id]['parts_qty'] == 5 and rows[a.id]['parts'] == 2
    assert rows[b.id]['parts_qty'] is None and rows[b.id]['parts'] == 0


def test_the_offer_names_what_a_field_can_be_made_of(boms):
    r = _command(_client(), 'item', 'calculated_offer', {})
    assert r.status_code == 200, r.content
    offer = {o['over']: o for o in r.json()['data']['result']['offer']}
    assert 'quantity' in offer['bom_parent']['numbers']


def test_a_definition_that_cannot_be_worked_out_is_refused(boms):
    client = _client()
    for spec in ({'calc': 'sum', 'of': 'quantity', 'over': 'no_such'},
                 {'calc': 'median', 'of': 'quantity', 'over': 'bom_parent'},
                 {'calc': 'sum', 'of': 'child_ida', 'over': 'bom_parent'}):
        r = _command(client, 'item', 'calculated', {'name': 'bad', 'spec': spec})
        assert r.status_code == 400, (spec, r.content)
    r = _command(client, 'item', 'calculated', {'name': 'name', 'spec': {'calc': 'count', 'over': 'bom_parent'}})
    assert r.status_code == 400                                   # a real field's name


def test_removing_a_definition_removes_the_value(boms):
    a, _b = boms
    client = _client()
    _command(client, 'item', 'calculated', {'name': 'parts', 'spec': {'calc': 'count', 'over': 'bom_parent'}})
    _command(client, 'item', 'calculated', {'name': 'parts', 'spec': None})
    assert 'parts' not in _list(client, 'item', [a.id])[a.id]


def test_a_dot_path_reads_into_json(boms):
    a, _b = boms
    client = _client()
    r = _command(client, 'item', 'calculated',
                 {'name': 'run_minutes', 'spec': {'calc': 'sum', 'of': 'op_data.run_time', 'over': 'bom_parent'}})
    assert r.status_code == 200, r.content
    assert _list(client, 'item', [a.id])[a.id]['run_minutes'] == 30


def test_a_value_made_of_what_no_role_sees_is_not_shown(boms):
    """op_data.labor is no declared leaf: no role sees it, so neither does a sum of it."""
    a, _b = boms
    client = _client()
    _command(client, 'item', 'calculated',
             {'name': 'hidden', 'spec': {'calc': 'sum', 'of': 'op_data.labor', 'over': 'bom_parent'}})
    assert 'hidden' not in _list(client, 'item', [a.id])[a.id]
