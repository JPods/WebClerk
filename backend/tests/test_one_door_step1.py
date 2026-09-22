"""One door, step 1: the rules the door stands on (Bill, 2026-09-22; Fable's build order).

- No model has a deleted flag: soft delete is removed everywhere, so a delete is a delete.
- A journalized document cannot be deleted, and no line can be added to it or deleted from it.
- A save that names its fields still writes the version bump.
- A line keeps a snapshot of the values it was loaded with (Bill's WC2 collection of
  initial line values), in plain values that an in-place edit cannot reach.
~/Allie/readmes/assessments/2026-09-22-one-door-line-pendings.md §7-9
"""
import pytest

from apps.transactions.models.hard_delete import JournalizedDeleteRefused

pytestmark = pytest.mark.django_db


def _order_with_line(qty=5):
    from apps.products.models import Item
    from apps.transactions.models import Order, OrderLine
    item = Item.objects.create(ida='DOOR-1', name='DOOR-1')
    order = Order.objects.create(status='open')
    line = OrderLine.objects.create(order=order, item_fk=item, item={'id': item.pk},
                                    quantity={'active': qty}, status='open')
    return order, line


def _journalize(header):
    type(header).objects.filter(pk=header.pk).update(is_locked=True)
    header.refresh_from_db()


def test_no_model_can_be_soft_deleted_or_restored():
    """The flag and its two methods are gone from every model, not only transactions."""
    from apps.core.models import Contact
    from apps.products.models import Item
    from apps.transactions.models import Cash
    order, line = _order_with_line()
    for record in (order, line, Cash(amount=10), Contact(), Item()):
        assert not hasattr(record, 'is_deleted')
        assert not hasattr(record, 'soft_delete')
        assert not hasattr(record, 'restore')


def test_a_hard_delete_goes_through():
    from apps.transactions.models import Order, OrderLine
    order, line = _order_with_line()
    line.delete()
    assert not OrderLine.objects.filter(pk=line.pk).exists()
    order.delete()
    assert not Order.objects.filter(pk=order.pk).exists()


def test_a_journalized_document_cannot_be_deleted_nor_its_lines():
    from django.db import transaction
    from apps.transactions.models import OrderLine
    order, line = _order_with_line()
    _journalize(order)
    attempts = (
        (order.delete, 'credit memo'),
        (line.delete, 'journalized'),
        (lambda: OrderLine.objects.filter(pk=line.pk).delete(), 'journalized'),   # queryset too
        (lambda: OrderLine.objects.create(order=order, item={'id': line.item_fk_id},
                                          quantity={'active': 1}, status='open'), 'journalized'),
    )
    for attempt, words in attempts:
        with pytest.raises(JournalizedDeleteRefused, match=words), transaction.atomic():
            attempt()
    assert OrderLine.objects.filter(order=order).count() == 1


def test_reconciled_cash_cannot_be_deleted():
    from apps.transactions.models import Cash
    cash = Cash.objects.create(amount=10)
    Cash.objects.filter(pk=cash.pk).update(reconciled=True)
    cash.refresh_from_db()
    with pytest.raises(JournalizedDeleteRefused, match='reconciled'):
        cash.delete()


def test_a_save_naming_its_fields_writes_the_version():
    from apps.transactions.models import OrderLine
    _order, line = _order_with_line()
    before = OrderLine.objects.values_list('version', flat=True).get(pk=line.pk)
    line.status = 'held'
    line.save(update_fields=['status'])
    stored = OrderLine.objects.values_list('version', flat=True).get(pk=line.pk)
    assert stored == line.version == before + 1


def test_the_snapshot_is_plain_values_an_in_place_edit_cannot_reach():
    from apps.transactions.models import OrderLine
    _order, line = _order_with_line(5)
    loaded = OrderLine.objects.get(pk=line.pk)
    assert loaded._loaded['active'] == 5 and loaded._loaded['item_id'] == line.item_fk_id
    loaded.quantity['active'] = 8                         # the way update_quantity edits
    assert loaded._loaded['active'] == 5                  # the snapshot still says 5
    loaded.save()
    assert loaded._loaded['active'] == 8                  # re-taken after the save
    OrderLine.objects.filter(pk=line.pk).update(quantity={'active': 3})
    loaded.refresh_from_db()
    assert loaded._loaded['active'] == 3                  # and after a refresh


def test_a_partial_load_still_snapshots_what_is_stored():
    """BaseModel.__init__ reads every field (_capture_original_state), so a .only() load
    fills the deferred ones. The snapshot is then complete and true, not partial."""
    from apps.transactions.models import OrderLine
    _order, line = _order_with_line(5)
    assert OrderLine.objects.only('id', 'status').get(pk=line.pk)._loaded['active'] == 5
