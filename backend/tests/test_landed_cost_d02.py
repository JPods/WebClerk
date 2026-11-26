"""D02 (Bill, 2026-09-21): one landed-cost engine.

Each landed cost spreads by its own basis (value default, weight, quantity) over the
lines the user has not pinned; pins must add up to the header amount; and the result
reaches the inventory layer, so stock is carried at what we owe.
~/Allie/readmes/assessments/2026-09-20/defects/D02-allocations-method-dead.md
"""
from __future__ import annotations

import pytest

from tests.utils import received_receipt_line
from django.core.exceptions import ValidationError

from apps.transactions.models import Receipt, ReceiptLine

pytestmark = pytest.mark.django_db


def _receipt(method=None, **landed):
    alloc = {'freight': 0, 'duty': 0, 'handling': 0, 'vat': 0,
             'method': {'freight': 'value', 'duty': 'value', 'handling': 'value', 'vat': 'value'}}
    alloc.update(landed)
    alloc['method'].update(method or {})
    return Receipt.objects.create(allocations=alloc)


def _line(receipt, n, qty, unit, **extra):
    cost = {'unit': unit, 'precision': 2}
    cost.update(extra.pop('cost', {}))
    return received_receipt_line(receipt=receipt, line_number=n, quantity={'active': qty},
                                      cost=cost, **extra)


def _shares(receipt, comp):
    return [l.totals['landed'][comp] for l in receipt.lines.order_by('line_number')]


def _spread(receipt, **body):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    out = run_command(Actor.system(), 'spread', 'receipt', receipt.pk, body)
    receipt.refresh_from_db()
    return out


def _receive_together(receipt, *rows, **physical):
    """Lines saved planned, then received in one save, as a document saved with its lines is."""
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    from apps.products.models import Item, Warehouse
    wh, _ = Warehouse.objects.get_or_create(code='D02AUTO', defaults={'name': 'D02 auto'})
    lines = [_planned_line(receipt, n, qty, unit, Item.objects.create(name=f'D02 auto {n}'), wh)
             for n, qty, unit in rows]
    save_record(Actor.system(), {'id': receipt.pk, 'lines': [
        {'id': l.pk, 'quantity': {'active': l.quantity['staged']}} for l in lines]}, model_key='receipt')
    receipt.refresh_from_db()
    return lines


def test_a_save_never_spreads_and_the_charges_are_still_owed():
    """Bill, 2026-11-25: a save changes what was typed and nothing else. Bill, 2026-11-26: nothing
    spreads on its own, not even the first time — "switch the auto spreading to a button. So users
    see what we are doing." Charges no line carries are named apart and stay in what is owed."""
    r = _receipt(freight=10, duty=4, handling=3)
    _receive_together(r, (10, 7, 6.00), (20, 4, 12.50))
    assert _shares(r, 'freight') == [0, 0]
    assert r.totals['unallocated'] == {'freight': 10.0, 'duty': 4.0, 'handling': 3.0, 'vat': 0.0}
    assert r.totals['total'] == 109.00
    assert 'spread' not in r.allocations, 'nothing was spread, so nothing is recorded'


def test_the_spread_says_what_it_did_and_records_it():
    r = _receipt(method={'duty': 'quantity'}, freight=10, duty=4)
    _receive_together(r, (10, 7, 6.00), (20, 4, 12.50))
    out = _spread(r)
    assert out['messages'] == ['freight 10.00 spread by value', 'duty 4.00 spread by quantity']
    record = r.allocations['spread']
    assert (record['freight']['by'], record['freight']['basis_used']) == ('command', 'value')
    assert record['duty']['basis_used'] == 'quantity' and record['freight']['dt'] > 0


def test_a_manual_charge_is_never_spread_for_the_person():
    """The variation the person owns (Bill, 2026-11-26: "our code should allow user-defined
    variations"): the command leaves a charge whose basis is manual alone; every share is typed."""
    r = _receipt(method={'freight': 'manual'}, freight=10, duty=4)
    a, _b = _receive_together(r, (10, 7, 6.00), (20, 4, 12.50))
    out = _spread(r)
    freight = next(d for d in out['spread'] if d['component'] == 'freight')
    assert freight['basis_used'] == 'manual' and 'typed' in freight['reason']
    assert 'freight 10.00 left as typed (manual)' in out['messages']
    assert _shares(r, 'freight') == [0, 0] and _shares(r, 'duty') == [1.83, 2.17]
    assert r.totals['unallocated']['freight'] == 10.0
    a.refresh_from_db()
    _type(a, freight=10.00)
    r.refresh_from_db()
    assert r.totals['unallocated']['freight'] == 0.0


def test_an_item_carries_a_class_for_each_charge_through_the_api(admin_client):
    """Bill, 2026-11-26: item.config.landed_class.<freight|duty|handling|vat>, a label most
    businesses leave blank. It saves and reads back through the door."""
    from apps.products.models import Item
    item = Item.objects.create(name='D02 classed')
    r = admin_client.put(f'/wcapi/item/{item.pk}/', {'config': {'landed_class': {'freight': 'bulk', 'duty': 'grain'}}},
                         content_type='application/json')
    assert r.status_code == 200, r.content
    r = admin_client.get(f'/wcapi/item/{item.pk}/')
    assert r.json()['data']['record']['config']['landed_class'] == {'freight': 'bulk', 'duty': 'grain'}
    r = admin_client.put(f'/wcapi/item/{item.pk}/', {'config': {'landed_class': {'insurance': 'x'}}},
                         content_type='application/json')
    assert r.status_code >= 400, 'a charge the receipt does not have is refused, not stored'


def test_unlike_items_on_one_receipt_are_named_and_still_spread():
    """Bill, 2026-11-26: "limit a receipt to like items ... corn, wheat, and gold". A coaching
    cue, never a refusal: the spread happens and its record names the classes it mixed."""
    from apps.products.models import Item
    r = _receipt(freight=10, duty=4)
    corn, gold = _receive_together(r, (10, 7, 6.00), (20, 4, 12.50))
    for line, freight in ((corn, 'bulk'), (gold, 'precious')):
        Item.objects.filter(pk=line.item_fk_id).update(config={'landed_class': {'freight': freight, 'duty': 'same'}})
    out = _spread(r)
    freight = next(d for d in out['spread'] if d['component'] == 'freight')
    duty = next(d for d in out['spread'] if d['component'] == 'duty')
    assert freight['classes'] == ['bulk', 'precious'] and 'like items' in freight['reason']
    assert 'classes' not in duty and duty['reason'] == '', 'the same duty class is like items'
    assert _shares(r, 'freight') == [4.57, 5.43]
    assert r.allocations['spread']['freight']['classes'] == ['bulk', 'precious']


def test_spread_by_value_is_the_default_and_the_money_ties():
    r = _receipt(freight=10, duty=4, handling=3)
    _line(r, 10, 7, 6.00)
    _line(r, 20, 4, 12.50)
    out = _spread(r)
    assert _shares(r, 'freight') == [4.57, 5.43]
    assert [l.cost['landed']['freight'] for l in r.lines.order_by('line_number')] == [4.57, 5.43]
    assert r.totals['total'] == 109.00
    assert r.totals['unallocated'] == {'freight': 0.0, 'duty': 0.0, 'handling': 0.0, 'vat': 0.0}
    assert out['unallocated'] == r.totals['unallocated']
    assert [d['basis_used'] for d in out['spread']] == ['value'] * 4


def test_quantity_is_honoured_when_the_record_asks_for_it():
    r = _receipt(method={'freight': 'quantity'}, freight=10)
    _line(r, 10, 7, 6.00)
    _line(r, 20, 4, 12.50)
    _spread(r)
    assert _shares(r, 'freight') == [6.36, 3.64]          # D02's table: not 4.57 / 5.43


def test_each_component_keeps_its_own_basis():
    r = _receipt(method={'freight': 'weight', 'duty': 'value'}, freight=10, duty=4)
    _line(r, 10, 7, 6.00, physical={'weight': {'value': 1, 'unit': 'kg'}})
    _line(r, 20, 4, 12.50, physical={'weight': {'value': 5, 'unit': 'kg'}})
    _spread(r)
    assert _shares(r, 'freight') == [2.59, 7.41]          # 7 kg / 20 kg
    assert _shares(r, 'duty') == [1.83, 2.17]             # 42 / 50 by value


def test_a_missing_weight_falls_back_to_value_and_says_so():
    r = _receipt(method={'freight': 'weight'}, freight=10)
    _line(r, 10, 7, 6.00, physical={'weight': {'value': 1, 'unit': 'kg'}})
    _line(r, 20, 4, 12.50)
    out = _spread(r, components=['freight'])
    assert _shares(r, 'freight') == [4.57, 5.43]
    (freight,) = out['spread']
    assert (freight['basis'], freight['basis_used']) == ('weight', 'value')
    assert 'line 20' in freight['reason']


def _type(line, **shares):
    line.cost = {**line.cost, 'landed': {**(line.cost.get('landed') or {}), **shares}}
    line.save()


def test_a_typed_share_changes_that_line_only():
    """Bill, 2026-11-25: "changing a line's values ... does not recalculate other lines"."""
    r = _receipt(freight=10)
    a = _line(r, 10, 7, 6.00)
    _line(r, 20, 4, 12.50)
    _spread(r)
    a.refresh_from_db()
    _type(a, freight=8.00)
    r.refresh_from_db()
    assert _shares(r, 'freight') == [8.00, 5.43], 'the other line keeps its share'
    assert r.totals['unallocated']['freight'] == -3.43, 'the lines carry more than the charge'
    assert r.totals['total'] == 102.00, 'what is owed is the charge, however the lines carry it'
    # Running the spread again is how the lines are recalculated: it replaces what was typed.
    _spread(r)
    assert _shares(r, 'freight') == [4.57, 5.43]


def test_the_old_pin_is_refused_by_name():
    r = _receipt(freight=10)
    a = _line(r, 10, 7, 6.00)
    a.cost = {**a.cost, 'landed_override': {'freight': 8.00}}
    with pytest.raises(ValidationError, match='landed_override is gone'):
        a.save()


def test_one_word_for_every_component_is_refused():
    r = Receipt.objects.create(allocations={'freight': 10, 'method': 'value'})
    with pytest.raises(ValidationError, match='not a single word'):
        _line(r, 10, 1, 1.00)


def _planned_line(receipt, n, qty, unit, item, warehouse):
    return ReceiptLine.objects.create(receipt=receipt, line_number=n, item_fk=item, item={'id': item.pk},
                                      quantity={'active': 0, 'staged': qty}, warehouse=warehouse,
                                      cost={'unit': unit, 'precision': 2})


@pytest.mark.usefixtures('chart_of_accounts')
def test_the_layers_follow_their_lines_until_the_receipt_is_journalized():
    """A received line's layer is carried at the line's landed cost: the unit plus the shares the
    line holds. Until the receipt is journalized the charges, the spread and a line's share are
    the user's to correct and the layers follow (Bill, 2026-11-25, replaces R3: "Users know things
    we do not and are responsible"). At journalize a charge no line carries posts to its own
    account, once the person confirms. Journalized: refused."""
    from apps.accounts.models import GlJournal
    from apps.accounts.services.journalize import journalize_receipt
    from apps.core.models.pending import Pending
    from apps.core.services.door import Actor, Refused
    from apps.core.services.save import save_record
    from apps.core.services.verbs import run_command
    from apps.products.models import Item, Warehouse
    item, other = Item.objects.create(name='D02 item'), Item.objects.create(name='D02 other')
    wh = Warehouse.objects.create(name='D02 WH', code='D02WH')
    r = _receipt(freight=10, duty=4)
    vendor = Receipt._meta.get_field('vendor').related_model.objects.create(company='D02 Vendor')
    Receipt.objects.filter(pk=r.pk).update(vendor_id=vendor.pk, terms='N30')   # complete: it will journalize
    first = _planned_line(r, 10, 7, 6.00, item, wh)
    second = _planned_line(r, 20, 4, 12.50, other, wh)
    save_record(Actor.system(), {'id': r.pk, 'lines': [
        {'id': first.pk, 'quantity': {'active': 7}}, {'id': second.pk, 'quantity': {'active': 4}}]},
        model_key='receipt')
    first.refresh_from_db()
    layer = first.inventory_layer
    assert layer.cost['unit_po'] == 6.00 and layer.cost['landed'] == 6.00, 'born at the unit: nothing spread yet'

    _spread(r)
    layer.refresh_from_db()
    # freight 4.57 / 7 = 0.6529, duty 1.83 / 7 = 0.2614
    assert layer.cost['freight'] == 0.6529 and layer.cost['duty'] == 0.2614
    assert layer.cost['landed'] == pytest.approx(6.00 + 0.6529 + 0.2614)
    assert layer.quantity['received'] == 7, 'a cost change moves no stock'

    # The freight bill was wrong: 10 becomes 21. The lines keep their shares until the spread runs.
    save_record(Actor.system(), {'id': r.pk, 'allocations': {**r.allocations, 'freight': 21}},
                model_key='receipt')
    r.refresh_from_db()
    layer.refresh_from_db()
    assert layer.cost['freight'] == 0.6529 and r.totals['unallocated']['freight'] == 11.0
    _spread(r, components=['freight'])                      # by value: 42 of 92 and 50 of 92
    layer.refresh_from_db()
    second.refresh_from_db()
    assert layer.cost['freight'] == pytest.approx(9.59 / 7, abs=1e-4)
    assert second.inventory_layer.cost['freight'] == pytest.approx(11.41 / 4, abs=1e-4)
    assert layer.cost['duty'] == 0.2614

    # The user types the first line's freight: 7.00. That layer follows; the other line stands.
    first.refresh_from_db()
    save_record(Actor.system(), {'id': r.pk, 'lines': [
        {'id': first.pk, 'cost': {**first.cost, 'landed': {**first.cost['landed'], 'freight': 7.00}}}]},
        model_key='receipt')
    layer.refresh_from_db()
    second.refresh_from_db()
    r.refresh_from_db()
    assert layer.cost['freight'] == 1.0
    assert second.inventory_layer.cost['freight'] == pytest.approx(11.41 / 4, abs=1e-4)
    assert r.totals['unallocated']['freight'] == 2.59
    changes = Pending.objects.filter(name__endswith='cost changed')
    assert changes.count() == 5, 'two layers at each spread, one at the typed share'
    assert all(p.is_processed() for p in changes)

    # Journalize: the 2.59 no line carries is named, and posts only when the person confirms.
    with pytest.raises(Refused) as refused:
        run_command(Actor.system(), 'journalize', 'receipt', r.pk, {})
    assert refused.value.code == 'unallocated_charges'
    assert journalize_receipt(r.pk) == {'created': 0, 'error': 'Unallocated charges',
                                        'unallocated': {'freight': 2.59}}
    posted = run_command(Actor.system(), 'journalize', 'receipt', r.pk, {'post_unallocated': True})
    assert posted['unallocated'] == {'freight': 2.59}
    apart = GlJournal.objects.filter(source_model='receipt', source_id=r.pk, event_id='unallocated:freight')
    assert sorted((float(g.debit or 0), float(g.credit or 0)) for g in apart) == [(0.0, 2.59), (2.59, 0.0)]
    assert all('unallocated freight' in g.note for g in apart)
    # One expense account for every kind of charge (Bill, 2026-11-26), not default_expense.
    assert sorted(g.account for g in apart) == ['2050-received_not_billed', '6560-unallocated_receipt']
    # Who and when, in the same place on the journal rows and on the receipt: comments.process.
    r.refresh_from_db()
    (entry,) = [e for e in r.comments['process'] if e.get('source') == 'journalize']
    assert entry['data']['post_unallocated'] is True and entry['data']['unallocated'] == {'freight': 2.59}
    assert entry['data']['dt'] > 0 and 'freight 2.59' in entry['mgs']
    rows = GlJournal.objects.filter(source_model='receipt', source_id=r.pk)
    for g in rows:
        (posted_by,) = g.comments['process']
        assert posted_by['source'] == 'journalize' and posted_by['data']['dt'] == g.dt_journaled
    assert round(sum(float(g.debit or 0) for g in rows), 2) == round(sum(float(g.credit or 0) for g in rows), 2)

    r.refresh_from_db()
    r.allocations = {**r.allocations, 'freight': 0}
    with pytest.raises(Refused) as refused:
        r.save()
    assert refused.value.code == 'receipt_journalized'
    with pytest.raises(Refused) as refused:
        run_command(Actor.system(), 'spread', 'receipt', r.pk, {})
    assert refused.value.code == 'receipt_journalized'
    layer.refresh_from_db()
    assert layer.cost['freight'] == 1.0, 'a journalized receipt keeps its layers'


def test_a_layer_shows_its_quantity_and_cost_and_refuses_a_direct_change(admin_client):
    """Bill, 2026-11-26: the layer's form was "very hard to see or find values" — the door let out
    only cost.freight and cost.handling. A layer now reads whole, and a save cannot change what
    the ledger's inventory is checked against."""
    r = _receipt(freight=10)
    line, _other = _receive_together(r, (10, 7, 6.00), (20, 4, 12.50))
    _spread(r)
    line.refresh_from_db()
    layer = line.inventory_layer
    got = admin_client.get(f'/wcapi/inventory_layer/{layer.pk}/').json()['data']['record']
    assert got['quantity']['received'] == 7
    assert got['cost']['unit_po'] == 6.00 and got['cost']['freight'] == 0.6529
    assert got['cost']['landed'] == pytest.approx(6.6529)
    refused = admin_client.put(f'/wcapi/inventory_layer/{layer.pk}/', {'cost': {'unit_po': 1.00}},
                               content_type='application/json')
    assert refused.status_code == 409, refused.content
    assert refused.json()['error']['code'] == 'layer_changes_with_stock'
    layer.refresh_from_db()
    assert layer.cost['unit_po'] == 6.00
    lot = admin_client.put(f'/wcapi/inventory_layer/{layer.pk}/', {'lot': 'L-77'}, content_type='application/json')
    assert lot.status_code == 200, lot.content
