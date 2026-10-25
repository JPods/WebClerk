"""The screen mirrors the server's totals before a save (Bill, 2026-10-25: users see changes
as they make them, without saving).

Changing a quantity on an order left Financials showing the stored totals until save. The
screen now asks POST /wcapi/<model>/<id>/totals/ — compute_totals on its unsaved header and
lines — so what it shows is what the save will store, on every document with lines, and
asking writes nothing.
"""
from __future__ import annotations

import pytest
from django.utils.crypto import get_random_string
from rest_framework.test import APIClient

from apps.core.services.door import resolve_model
from apps.transactions.services.pricing.totals_compute import is_sell_side, recalculate_totals
from apps.transactions.services.totals_preview import TOTALS_MODELS


@pytest.fixture
def staff_client(django_user_model):
    user = django_user_model.objects.create_superuser(
        email='preview@example.com', password=get_random_string(20),
        name_first='P', name_last='User')
    client = APIClient()
    client.force_authenticate(user)
    return client


def _document(model_key):
    """A document with one line of 15 at 12.71 (cost 8.97), its totals stored."""
    doc = resolve_model(model_key)[0].objects.create(finance={'sales_tax_rate': 10})
    line = {'line_number': 1, 'quantity': {'active': 15},
            'cost': {'unit': 8.97, 'precision': 2}}
    if is_sell_side(model_key):
        line['price'] = {'unit': 12.71, 'precision': 2}
    # bulk_create, not save: a receipt's received quantity is the receive command's to set.
    doc.lines.model.objects.bulk_create([doc.lines.model(**line, **{doc.lines.field.name: doc})])
    recalculate_totals(doc.pk, model_key)
    doc.refresh_from_db()
    return doc


def _screen_lines(doc, qty):
    return [{'id': l.id, 'line_number': l.line_number, 'line_type': l.line_type,
             'quantity': {**l.quantity, 'active': qty},
             'price': getattr(l, 'price', None), 'cost': l.cost}
            for l in doc.lines.all()]


def _ask(client, model_key, doc, body):
    r = client.post(f'/wcapi/{model_key}/{doc.id}/totals/', body, format='json')
    assert r.status_code == 200, r.content
    return r.json()['data']['result']


@pytest.mark.parametrize('model_key', TOTALS_MODELS)
def test_the_preview_is_what_the_save_stores_and_writes_nothing(staff_client, model_key):
    doc = _document(model_key)
    stored = dict(doc.totals)

    preview = _ask(staff_client, model_key, doc,
                   {'header': {'finance': doc.finance}, 'lines': _screen_lines(doc, 9)})

    doc.refresh_from_db()
    assert doc.totals == stored                       # asking wrote nothing
    line = doc.lines.get()
    assert line.quantity['active'] == 15

    # Straight to the row, for the same reason.
    type(line).objects.filter(pk=line.pk).update(quantity={**line.quantity, 'active': 9})
    recalculate_totals(doc.pk, model_key)
    doc.refresh_from_db()
    for k in ('amount', 'tax', 'cost', 'margin', 'total'):
        assert preview['totals'][k] == doc.totals[k], (model_key, k)
    assert preview['line_totals'][str(line.id)]['amount'] == doc.totals['amount']


def test_a_new_line_on_the_screen_is_priced_by_its_temporary_id(staff_client):
    doc = _document('quote')
    lines = _screen_lines(doc, 15) + [
        {'id': -1, 'line_number': 2, 'quantity': {'active': 2},
         'price': {'unit': 10, 'precision': 2}, 'cost': {'unit': 4, 'precision': 2}}]
    body = _ask(staff_client, 'quote', doc, {'header': {}, 'lines': lines})
    assert body['line_totals']['-1']['amount'] == 20.0
    assert body['totals']['amount'] == 210.65         # 15 × 12.71 + 2 × 10


def test_a_body_without_lines_is_coached(staff_client):
    doc = _document('order')
    r = staff_client.post(f'/wcapi/order/{doc.id}/totals/', {'header': {}}, format='json')
    assert r.status_code == 400
    assert r.json()['error']['code'] == 'totals_needs_header_and_lines'
