"""A removed line arrives marked, and the backend does the delete (Bill, 2026-09-22).

"Deleting a line on the front end requires the array element be identified as deleted, not
just missed in the send. So the front end removing a line should not remove it from the
collection of lines but identify it as deleted so the backend does the delete."

The line stays in the payload carrying `_delete: true`; the save deletes the row inside the
same transaction as the header, and the line's own door writes the Pending that releases
what it held. A line the user never saved has no id and simply never arrives.
~/Allie/readmes/assessments/2026-09-22-one-door-line-pendings.md §12
"""
import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def request_obj(rf, django_user_model):
    request = rf.post('/wcapi/save/')
    request.user = django_user_model.objects.create_user(username='door', password='x')
    return request


def _item(ida='DEL-1'):
    from apps.products.models import Item
    return Item.objects.create(ida=ida, name=ida)


def _order_with_two_lines(item):
    from apps.transactions.models import Order, OrderLine
    order = Order.objects.create(status='open')
    a = OrderLine.objects.create(order=order, item_fk=item, item={'id': item.pk, 'item_id': item.pk},
                                 quantity={'active': 5}, status='open')
    b = OrderLine.objects.create(order=order, item_fk=item, item={'id': item.pk, 'item_id': item.pk},
                                 quantity={'active': 3}, status='open')
    return order, a, b


def _on_so(item):
    item.refresh_from_db()
    return float((item.quantity or {}).get('on_so') or 0)


def test_a_marked_line_is_deleted_by_the_save_and_releases_what_it_held(request_obj):
    from apps.transactions.models import OrderLine
    from apps.transactions.services.transaction_save import save_transaction_with_lines

    item = _item()
    order, keep, remove = _order_with_two_lines(item)
    assert _on_so(item) == 8

    result = save_transaction_with_lines(
        'order',
        {'id': order.pk, 'status': 'open'},
        [
            {'id': keep.pk, '_dirty': False, 'item': {'item_id': item.pk}, 'quantity': {'active': 5}},
            {'id': remove.pk, '_delete': True, 'item': {'item_id': item.pk}, 'quantity': {'active': 3}},
        ],
        request=request_obj,
        verify_calculations=False,
    )

    assert not OrderLine.objects.filter(pk=remove.pk).exists()      # the backend did the delete
    assert OrderLine.objects.filter(pk=keep.pk).exists()
    assert {'id': remove.pk, 'action': 'deleted'} in result['lines']
    assert _on_so(item) == 5                                        # its commitment came back


def test_the_marker_never_reaches_the_row(request_obj):
    """_delete is a transport directive, not a field: a line that stays must not carry it."""
    from apps.transactions.models import OrderLine
    from apps.transactions.services.transaction_save import save_transaction_with_lines

    item = _item('DEL-2')
    order, keep, _remove = _order_with_two_lines(item)
    save_transaction_with_lines(
        'order', {'id': order.pk, 'status': 'open'},
        [{'id': keep.pk, '_dirty': True, '_delete': False,
          'item': {'item_id': item.pk}, 'quantity': {'active': 6}}],
        request=request_obj, verify_calculations=False,
    )
    keep.refresh_from_db()
    assert float(keep.quantity['active']) == 6
    assert not hasattr(keep, '_delete')
    assert '_delete' not in (keep.item or {}) and '_delete' not in (keep.quantity or {})


def test_a_marked_line_that_is_not_on_the_document_fails_hard(request_obj):
    """A delete for a line this document does not have means the client is out of step.
    Reporting it as skipped would hide that (Bill, 2026-09-22: fail hard)."""
    from apps.transactions.services.transaction_save import save_transaction_with_lines

    item = _item('DEL-3')
    order, _keep, remove = _order_with_two_lines(item)
    pk = remove.pk
    remove.delete()
    with pytest.raises(LookupError, match=str(pk)):
        save_transaction_with_lines(
            'order', {'id': order.pk, 'status': 'open'},
            [{'id': pk, '_delete': True, 'item': {'item_id': item.pk}, 'quantity': {'active': 3}}],
            request=request_obj, verify_calculations=False,
        )
    assert _on_so(item) == 5                                        # released once, not twice
