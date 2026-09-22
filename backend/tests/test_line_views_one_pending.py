"""G6 (readmes/97 §8): the REST line views wrote each inventory Pending a second time.

The line signals (signals.register_line_inventory_signals) are the one path for a line's
Pending. The views are not routed today, so their perform_* hooks are driven directly with
a stand-in serializer: one create, one update, one delete → one Pending each.
"""
import pytest

from apps.core.models import Pending
from apps.transactions.models import OrderLine
from apps.transactions.views.line_views import OrderLineListCreate, OrderLineRetrieveUpdate
from tests.conftest import ItemFactory, OrderFactory


class _Serializer:
    """What perform_create/perform_update see: save() writes the line, as DRF's would."""

    def __init__(self, save):
        self._save = save
        self.validated_data = {}

    def save(self):
        return self._save()


def _pendings(item):
    return Pending.objects.filter(model_name='item', record_id=str(item.pk)).count()


@pytest.mark.django_db
def test_order_line_views_write_one_pending_per_change():
    item = ItemFactory(ida='G6-1', description='G6 widget')
    order = OrderFactory()
    ref = {'item_id': item.pk, 'id': item.pk, 'ida': item.ida}

    line = OrderLineListCreate().perform_create(_Serializer(
        lambda: OrderLine.objects.create(order=order, item=ref, quantity={'active': 4})))
    line = OrderLine.objects.get(order=order)
    assert _pendings(item) == 1

    def update():
        line.quantity = {'active': 6}
        line.save()
        return line
    view = OrderLineRetrieveUpdate()
    view.get_object = lambda: OrderLine.objects.get(pk=line.pk)
    view.perform_update(_Serializer(update))
    assert _pendings(item) == 2

    view.perform_destroy(OrderLine.objects.get(pk=line.pk))
    assert _pendings(item) == 3
