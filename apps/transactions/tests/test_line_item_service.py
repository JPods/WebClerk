import pytest
from apps.transactions.services.line_item_service import LineItemService

import pytest
from apps.transactions.services.line_item_service import LineItemService
from apps.products.models import Item
from apps.transactions.models import SalesOrder


@pytest.mark.django_db
def test_add_item_creates_pending_for_sales_order():
    # Create sample item
    item = Item.objects.create(
        name="Test Item",
        ida="TEST-ITEM",
        price={"base": 10},
        cost={"standard": 5},
        record={"quantity": {"placed": 3}},
    )

    # Create a sales order
    order = SalesOrder.objects.create(status="confirmed")

    service = LineItemService()

    # Add item
    line = service.add_item_to_transaction(order, item_id=item.id, quantity=3)

    # Validate pending record created
    from apps.core.models import Pending
    pending_records = Pending.objects.filter(data__doc_pk=order.pk)

    assert pending_records.count() == 1
    assert pending_records.first().data.get("on_so") == 3

