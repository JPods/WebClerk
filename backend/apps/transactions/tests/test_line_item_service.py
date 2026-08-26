import pytest
from apps.transactions.services.line_item_service import LineItemService
from apps.products.models import Item
from apps.transactions.models import Order, OrderLine


@pytest.mark.django_db
def test_add_item_creates_pending_for_order():
    """Adding an OrderLine with an item_fk creates a pending inventory record."""
    item = Item.objects.create(
        name="Test Item",
        ida="TEST-ITEM",
        price={"base": 10},
        cost={"standard": 5},
    )

    order = Order.objects.create(status="confirmed")
    # Create an order line referencing the item — the post_save signal
    # in signals.py should create a Pending record for inventory tracking
    OrderLine.objects.create(
        order=order,
        item_fk=item,
        quantity={"staged": 3, "active": 3},
        price={"unit": 10},
        cost={"unit": 5},
    )

    from apps.core.models import Pending
    # Pending records are created by the signal with purpose='inventory_line_add'
    pending_records = Pending.objects.filter(purpose='inventory_line_add', record_id=str(item.pk))
    assert pending_records.count() >= 1

