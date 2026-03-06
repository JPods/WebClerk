import pytest
from apps.transactions.services.line_item_service import LineItemService

import pytest
from apps.transactions.services.line_item_service import LineItemService
from apps.products.models import Item
from apps.transactions.models import Order


@pytest.mark.django_db
def test_add_item_creates_pending_for_order():
    # Create sample item
    item = Item.objects.create(
        name="Test Item",
        ida="TEST-ITEM",
        price={"base": 10},
        cost={"standard": 5},
        record={"quantity": {"staged": 3}},
    )

    # Create an order
    order = Order.objects.create(status="confirmed")
    # Validate pending record created
    from apps.core.models import Pending
    pending_records = Pending.objects.filter(data__doc_pk=order.pk)

    assert pending_records.count() == 1
    assert pending_records.first().data.get("on_so") == 3

