"""A received receipt posts the payable and its layers' value; a purchase posts nothing
(Bill, 2026-09-28/30; GL-by-layer step 4b).

Inventory comes from the layers (quantity x fixed landed cost, one pair per movement); the payable
from the receipt (what the vendor bills). Received Not Billed joins them; what is left in it is
landed cost someone else bills (freight), the accrual until that bill arrives.
"""
from decimal import Decimal

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]

COST = {'unit': 4.0, 'precision': 2}


def _run(verb, model, pk, data=None):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    return run_command(Actor.system(), verb, model, pk, data or {})


def _received_receipt(qty=10, freight=0):
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import Purchase, PurchaseLine, Receipt
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_po': 0, 'on_rc': 0,
                                                        'allocated': 0, 'available': 0})
    Warehouse.objects.get_or_create(code='MAIN', defaults={'name': 'Main', 'is_active': True})
    po = Purchase.objects.create()
    pol = PurchaseLine.objects.create(purchase=po, item={'item_id': item.pk, 'description': 'Widget'},
                                      quantity={'active': qty, 'staged': qty}, cost=dict(COST))
    out = _run('convert', 'purchase', po.pk, {'to': 'receipt', 'lines': [{'line_id': pol.pk}]})
    receipt = Receipt.objects.get(pk=out['receipt_id'])
    if freight:
        receipt.allocations = {**(receipt.allocations or {}), 'freight': freight}
        receipt.save()
    _run('receive', 'receipt', receipt.pk)
    receipt.refresh_from_db()
    return item, receipt


def _net(receipt, account):
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(source_id=receipt.pk, source_model__in=('receipt', 'receipt_reversal'),
                                    account=account)
    return round(sum((r.debit or 0) - (r.credit or 0) for r in rows), 2)


def test_a_received_receipt_posts_inventory_from_its_layer_and_the_payable():
    from apps.products.models.inventory_layer import InventoryMovement
    item, receipt = _received_receipt(qty=10)
    out = _run('journalize', 'receipt', receipt.pk)
    assert out['created'] == 4 and out['payable'] == 40.0 and out['inventory'] == 40.0
    assert _net(receipt, '1200-inventory') == 40.0
    assert _net(receipt, '2000-accounts_payable') == -40.0
    assert _net(receipt, '2050-received_not_billed') == 0.0
    receipt.refresh_from_db()
    assert receipt.dt_journaled > 0
    moves = InventoryMovement.objects.filter(parent_model='receiptline')
    assert moves.count() == 1 and all(m.dt_journaled > 0 for m in moves)


def test_freight_billed_by_someone_else_stays_in_received_not_billed():
    item, receipt = _received_receipt(qty=10, freight=5)
    _run('journalize', 'receipt', receipt.pk)
    inventory = _net(receipt, '1200-inventory')
    payable = -_net(receipt, '2000-accounts_payable')
    assert inventory == pytest.approx(payable + 5.0), (inventory, payable)
    assert _net(receipt, '2050-received_not_billed') == pytest.approx(-5.0)


def test_nothing_received_is_refused_and_journalized_twice_is_refused():
    from apps.core.services.door import Refused
    from apps.transactions.models import Purchase, PurchaseLine, Receipt
    item, receipt = _received_receipt(qty=4)
    _run('journalize', 'receipt', receipt.pk)
    with pytest.raises(Refused) as refused:
        _run('journalize', 'receipt', receipt.pk)
    assert refused.value.code == 'already_journalized'
    po = Purchase.objects.create()
    pol = PurchaseLine.objects.create(purchase=po, item={'item_id': item.pk, 'description': 'Widget'},
                                      quantity={'active': 2, 'staged': 2}, cost=dict(COST))
    planned = _run('convert', 'purchase', po.pk, {'to': 'receipt', 'lines': [{'line_id': pol.pk}]})
    with pytest.raises(Refused) as refused:
        _run('journalize', 'receipt', planned['receipt_id'])
    assert refused.value.code == 'nothing_received'


def test_unjournalize_reverses_and_unposts_the_movements_then_it_posts_again():
    from apps.products.models.inventory_layer import InventoryMovement
    item, receipt = _received_receipt(qty=10)
    _run('journalize', 'receipt', receipt.pk)
    _run('unjournalize', 'receipt', receipt.pk, {'reason': 'wrong vendor'})
    assert _net(receipt, '1200-inventory') == 0.0 and _net(receipt, '2000-accounts_payable') == 0.0
    assert all(m.dt_journaled == 0 for m in InventoryMovement.objects.filter(parent_model='receiptline'))
    _run('journalize', 'receipt', receipt.pk)
    assert _net(receipt, '1200-inventory') == 40.0


def test_a_purchase_posts_nothing_and_the_batch_journalizes_receipts():
    from apps.accounts.models import GlJournal
    from apps.accounts.services.journalize import batch_journalize
    item, receipt = _received_receipt(qty=3)
    result = batch_journalize(ida_prefix='zzz-')
    assert [r['receipt_ida'] for r in result['receipts']] == [receipt.ida]
    assert not GlJournal.objects.filter(source_model='purchase').exists()
