"""Step 4 invariants — written as checks before the code that must pass them (Fable).

Bill, 2026-09-21/22: parts released to a workorder sit in quantity.in_process, pointed at by
item.metadata.on_assembly; a shortage is an open inventory_deficit Pending, so the shelf is
short by exactly the open deficit; a not-tracked item (labor, freight estimates) holds nothing.
~/Allie/readmes/assessments/2026-09-20/step3-workorders-plan.md §4, §1b.6, §8 step 4
"""
import pytest

pytestmark = pytest.mark.django_db


def _item(**quantity):
    from apps.products.models import Item
    q = {'on_hand': 0, 'allocated': 0, 'available': 0}
    q.update(quantity)
    return Item.objects.create(name='Step4', quantity=q)


def _move(item, **changes):
    """Move buckets the only way they move: an applied inventory Pending."""
    from apps.core.models.pending import Pending
    p = Pending.objects.create(model_name='item', record_id=str(item.pk),
                               purpose='inventory_qty_change', changes=changes)
    assert p.is_processed()
    item.refresh_from_db()
    return p


def _checks(item):
    from apps.core.services.balance_checker import check_balances
    result = check_balances(scope=('inventory',), item_id=item.pk)
    return {f['check'] for f in result['findings']}, result


def _deficit(item, qty, applied=()):
    from apps.core.models.pending import DEFICIT_PURPOSE, Pending
    p = Pending(model_name='item', record_id=str(item.pk), purpose=DEFICIT_PURPOSE,
                changes={'deficit_qty': qty, 'provisional_unit_cost': 2.0},
                metadata={'incremental_apply': [{'qty': q} for q in applied]})
    p.save()
    assert not p.is_processed()          # not an inventory purpose: it stays open
    return p


def test_in_process_is_a_bucket_the_applier_moves_and_a_save_keeps():
    item = _item()
    _move(item, in_process=4)
    assert item.quantity['in_process'] == 4
    item.name = 'Step4 renamed'
    item.save()                          # a full save must not drop the bucket
    item.refresh_from_db()
    assert item.quantity['in_process'] == 4


def test_in_process_without_its_on_assembly_pointer_is_a_finding():
    item = _item()
    _move(item, in_process=4)
    checks, _ = _checks(item)
    assert 'inventory.in_process' in checks
    item.metadata = {**(item.metadata or {}), 'on_assembly': [{'wo': 1, 'wo_line': 2, 'quantity': 4}]}
    item.save(update_fields=['metadata'])
    checks, _ = _checks(item)
    assert 'inventory.in_process' not in checks


def test_an_open_deficit_accounts_for_the_short_shelf():
    """30 on the shelf, 40 issued: on_hand −10, layers 0, deficit 10 → 0 = −10 + 10."""
    item = _item()
    _move(item, on_hand=-10)
    checks, _ = _checks(item)
    assert 'inventory.layers' in checks                 # nothing explains the gap yet
    _deficit(item, 10)
    checks, _ = _checks(item)
    assert 'inventory.layers' not in checks
    assert 'inventory.deficit_stale' not in checks      # still negative: a known defect, not a fault


def test_a_partly_filled_deficit_counts_only_what_remains():
    from decimal import Decimal
    item = _item()
    _move(item, on_hand=-9)
    p = _deficit(item, 11, applied=[2])
    assert p.incremental_remaining('deficit_qty') == Decimal('9')
    checks, _ = _checks(item)
    assert 'inventory.layers' not in checks


def test_a_deficit_still_open_once_stock_is_back_is_a_fault():
    item = _item()
    _deficit(item, 5)
    checks, _ = _checks(item)                           # on_hand 0 ≥ 0 with 5 open
    assert 'inventory.deficit_stale' in checks


def test_a_not_tracked_item_holding_anything_is_a_finding():
    item = _item()
    item.is_not_tracked = True
    item.save()
    checks, result = _checks(item)
    assert result['balanced'], result['findings']
    _move(item, on_wo=5)
    checks, _ = _checks(item)
    assert 'inventory.not_tracked_stock' in checks
