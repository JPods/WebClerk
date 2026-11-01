"""Every list reads in one order (Bill, 2026-11-01; apps/core/services/list_order): what was
asked, else config.orderby, else sequence, else newest first; id breaks ties."""
import secrets
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact, Setting
from apps.core.services import definition, list_order
from apps.products.models import Item
from apps.products.models.bill_of_material import BillOfMaterial

pytestmark = pytest.mark.django_db


def _client():
    staff = Contact.objects.create_superuser(email='staff@example.com',
                                             password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    return client


def _ids(client, model, **params):
    r = client.get(f'/wcapi/{model}/', params, HTTP_HOST='localhost')
    assert r.status_code == 200, r.content
    return [row['id'] for row in r.json()['data']['results']]


def _set_orderby(model, orderby):
    s = Setting.objects.get(purpose='wc:model', parent_model=model)
    Setting.objects.filter(pk=s.pk).update(config={**(s.config or {}), 'orderby': orderby})
    definition.clear(model)


@pytest.fixture
def bom():
    """Two parents, each with lines 1 and 2, made out of order."""
    a, b = (Item.objects.create(name=f'zz {n}', kind=Item.KIND_PHYSICAL) for n in 'AB')
    rows = {}
    for parent, seq in ((b, 2), (a, 2), (b, 1), (a, 1)):
        part = Item.objects.create(name=f'zz part {parent.name} {seq}', kind=Item.KIND_PHYSICAL)
        rows[(parent.name, seq)] = BillOfMaterial.objects.create(
            parent_item=parent, child_item=part, quantity=Decimal('1'), sequence=seq).id
    return rows


def test_a_bom_reads_by_parent_then_sequence(bom):
    """The reason orderby leads sequence: by sequence alone every parent's line 1 comes first."""
    _set_orderby('bill_of_material', list_order.DEFAULT['bill_of_material'])
    assert _ids(_client(), 'bill_of_material') == [
        bom[('zz A', 1)], bom[('zz A', 2)], bom[('zz B', 1)], bom[('zz B', 2)]]


def test_sequence_orders_a_model_with_no_orderby(bom):
    _set_orderby('bill_of_material', [])
    ids = _ids(_client(), 'bill_of_material')
    assert ids[:2] == sorted([bom[('zz A', 1)], bom[('zz B', 1)]])


def test_what_is_asked_comes_first(bom):
    client = _client()
    assert _ids(client, 'bill_of_material', ordering='-sequence,parent_item_id') == [
        bom[('zz A', 2)], bom[('zz B', 2)], bom[('zz A', 1)], bom[('zz B', 1)]]


def test_a_company_orderby_is_followed(bom):
    _set_orderby('bill_of_material', ['-parent_item_id', 'sequence'])
    assert _ids(_client(), 'bill_of_material') == [
        bom[('zz B', 1)], bom[('zz B', 2)], bom[('zz A', 1)], bom[('zz A', 2)]]


def test_an_unknown_field_is_dropped_not_obeyed(bom):
    _set_orderby('bill_of_material', ['no_such_field'])
    ids = _ids(_client(), 'bill_of_material')
    assert ids[:2] == sorted([bom[('zz A', 1)], bom[('zz B', 1)]])     # falls to sequence


def test_newest_first_when_nothing_else_orders():
    client = _client()
    first = Item.objects.create(name='zz first', kind=Item.KIND_PHYSICAL)
    second = Item.objects.create(name='zz second', kind=Item.KIND_PHYSICAL)
    ids = _ids(client, 'item', id__in=f'{first.id},{second.id}')
    assert ids == [second.id, first.id]

