"""Corrections through a count workorder — plan §16b/§16c (Bill, 2026-09-24/26).

"Adjustments only happen in a workorder." A count line carries what was counted; the line sets
its own book (staged) when first saved; its Pending is the variance, and a re-count posts only
the difference. An adjust line carries a change and its reason (comments.process). Found stock
lands in a layer of the line's own at the line's cost; missing stock comes off the layers. The
line never changes on_hand itself — its Pending's applier does — and once it has moved stock it
is the record: it cannot be deleted.
~/Allie/readmes/assessments/2026-09-24-one-route-per-verb.md §16b, §16c
"""
import pytest

from tests.test_stock_layers_follow_sales import _balanced, _issued, _on_hand, _stocked

pytestmark = pytest.mark.django_db


def _count_wo(**header):
    from apps.transactions.models import WorkOrder
    return WorkOrder.objects.create(kind='count', **header)


def _count(wo, item, counted, *, line_type='count', staged=None, cost=4.0, reason='', physical=None):
    from apps.transactions.models import WorkOrderLine
    quantity = {'active': counted}
    if staged is not None:
        quantity['staged'] = staged
    extra = {'physical': physical} if physical else {}
    comments = {'process': [{'user': 'Tester', 'mgs': reason}]} if reason else {}
    return WorkOrderLine.objects.create(
        workorder=wo, line_type=line_type, item={'item_id': item.pk, 'id_num': item.pk, 'description': item.name},
        quantity=quantity, cost={'unit': cost}, comments=comments, **extra)


def _recount(line, counted):
    line.refresh_from_db()
    line.quantity = {**line.quantity, 'active': counted}
    line.save()


def _events(line):
    line.refresh_from_db()
    return [e for e in line.events if isinstance(e, dict)]


def test_a_count_takes_its_own_book_and_posts_the_variance():
    item, _ = _stocked()                                   # 15 on hand
    line = _count(_count_wo(), item, 12, staged=99)        # the editor's staged is ignored
    line.refresh_from_db()
    assert line.quantity['staged'] == 15
    assert _on_hand(item) == 12
    assert _issued(item) == [3, 0, 0]                      # missing stock, consumed FIFO
    [event] = _events(line)
    assert (event['kind'], event['book'], event['counted'], event['variance']) == ('count', 15, 12, -3)
    assert event['moved_during_count'] is False
    assert line.quantity['remaining'] == 0
    assert _balanced(item)


def test_a_recount_posts_only_the_difference():
    item, _ = _stocked()
    line = _count(_count_wo(), item, 12)
    _recount(line, 14)                                     # 2 of the missing found after all
    assert _on_hand(item) == 14
    assert _issued(item) == [1, 0, 0]
    assert len(_events(line)) == 2
    assert _balanced(item)


def test_found_stock_lands_in_a_layer_of_its_own_at_the_line_cost():
    from apps.products.models.inventory_layer import InventoryLayer
    item, _ = _stocked()
    line = _count(_count_wo(), item, 18, cost=4.0)
    assert _on_hand(item) == 18
    line.refresh_from_db()
    layer = InventoryLayer.objects.get(pk=line.inventory_layer_id)
    assert float(layer.quantity['received']) == 3 and float(layer.cost['landed']) == 4.0
    _recount(line, 16)                                     # less found: its own layer comes down
    layer.refresh_from_db()
    # A layer's received is fixed (Bill, 2026-09-28): what comes down is issued from it.
    assert float(layer.quantity['received']) == 3 and float(layer.remaining_qty()) == 1
    assert _on_hand(item) == 16
    assert _balanced(item)


def test_a_count_matching_the_book_still_records_that_it_happened():
    item, _ = _stocked()
    line = _count(_count_wo(), item, 15)
    [event] = _events(line)
    assert event['variance'] == 0 and event['qty'] == 0
    assert _on_hand(item) == 15


def test_an_adjust_line_needs_its_reason():
    from apps.core.services.door import Refused
    item, _ = _stocked()
    wo = _count_wo()
    with pytest.raises(Refused) as refused:
        _count(wo, item, -2, line_type='adjust')
    assert refused.value.code == 'reason_required'
    line = _count(wo, item, -2, line_type='adjust', reason='dropped two')
    assert _on_hand(item) == 13
    [event] = _events(line)
    assert event['reason'] == 'dropped two'


def test_a_counted_line_cannot_be_deleted():
    from apps.core.services.door import Refused
    item, _ = _stocked()
    line = _count(_count_wo(), item, 12)
    with pytest.raises(Refused) as refused:
        line.delete()
    assert refused.value.code == 'count_recorded'


def test_the_book_never_moves_after_the_count():
    from apps.core.services.door import Refused
    item, _ = _stocked()
    line = _count(_count_wo(), item, 12)
    line.refresh_from_db()
    line.quantity = {**line.quantity, 'staged': 20}
    with pytest.raises(Refused) as refused:
        line.save()
    assert refused.value.code == 'count_book_fixed'


def test_a_count_naming_a_layer_takes_missing_stock_from_it():
    from apps.products.models.inventory_layer import InventoryLayer
    item, warehouse = _stocked()
    newest = InventoryLayer.objects.filter(item_id=item.pk).order_by('-id').first()
    _count(_count_wo(), item, 13, physical={'layer_id': newest.pk})
    assert _issued(item) == [0, 0, 2]
    assert _balanced(item)


def test_a_count_workorder_takes_only_count_and_adjust_lines_of_tracked_items():
    from apps.core.services.door import Refused
    from apps.products.models import Item
    item, _ = _stocked()
    wo = _count_wo()
    with pytest.raises(Refused) as refused:
        _count(wo, item, 3, line_type='product')
    assert refused.value.code == 'count_line_type'
    labor = Item.objects.create(name='Labor', flags={'not_tracked': True})
    with pytest.raises(Refused) as refused:
        _count(wo, labor, 3)
    assert refused.value.code == 'item_not_tracked'


def test_a_correction_saved_through_the_door_needs_the_person_responsible():
    from apps.core.services.door import Refused
    from apps.core.services.save_line_processing import process_lines
    item, _ = _stocked()
    wo = _count_wo()
    with pytest.raises(Refused) as refused:
        process_lines(wo, {'lines': [{'id': -1, 'line_type': 'count', 'quantity': {'active': 12},
                                      'item': {'item_id': item.pk}}]}, 'workorder', actor=None)
    assert refused.value.code == 'counter_required'
