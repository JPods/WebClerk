import pytest

from apps.products.models import Item
from apps.transactions.models import Invoice, InvoiceLine, Order, OrderLine
from apps.transactions.services.transaction_save import (
    InsufficientInventoryError,
    TransferQuantityError,
    save_transaction_with_lines,
)


def _make_item(*, name: str, sku: str, on_hand: float, available: float):
    return Item.objects.create(
        name=name,
        sku=sku,
        quantity={
            "on_hand": on_hand,
            "available": available,
            "allocated": 0,
        },
    )


def _make_order_with_line(*, item: Item, placed: float, actioned: float, remaining: float):
    order = Order.objects.create(status="confirmed")
    line = OrderLine.objects.create(
        order=order,
        item_fk=item,
        item={"id": item.id, "item_id": item.id, "sku": item.sku},
        quantity={
            "placed": placed,
            "actioned": actioned,
            "remaining": remaining,
            "precision": 2,
        },
        price={"unit": 10, "extended": 10 * placed},
        cost={"unit": 5, "extended": 5 * placed},
    )
    return order, line


@pytest.mark.django_db
def test_transfer_partial_quantity_updates_only_requested_amount(monkeypatch):
    monkeypatch.setattr(
        "apps.products.dispatch_pending.dispatch_pending_processing",
        lambda *args, **kwargs: None,
    )

    item = _make_item(name="Widget A", sku="W-A", on_hand=20, available=20)
    order, source_line = _make_order_with_line(
        item=item,
        placed=10,
        actioned=2,
        remaining=8,
    )

    result = save_transaction_with_lines(
        model_key="invoice",
        header_data={
            "status": "pending",
            "parent_model": "order",
            "parent_id": order.id,
            "totals": {},
            "finance": {},
        },
        lines_data=[
            {
                "quantity": {"placed": 3, "actioned": 3, "remaining": 0},
                "item": {"id": item.id, "item_id": item.id, "sku": item.sku},
                "price": {"unit": 10, "extended": 30},
                "cost": {"unit": 5, "extended": 15},
                "refs": {
                    "source": {
                        "order_line_id": source_line.id,
                        "order_id": order.id,
                        "converted_from": "order",
                    }
                },
                "_dirty": True,
            }
        ],
        request=None,
        verify_calculations=False,
        save_only_dirty=True,
    )

    assert result["action"] == "created"
    source_line.refresh_from_db()
    assert source_line.quantity["actioned"] == 5
    assert source_line.quantity["remaining"] == 5

    inv = Invoice.objects.get(pk=result["header"]["id"])
    assert inv.parent_model == "order"
    assert inv.parent_id == order.id
    assert InvoiceLine.objects.filter(invoice=inv).count() == 1


@pytest.mark.django_db
def test_transfer_blocks_when_requested_exceeds_source_remaining(monkeypatch):
    monkeypatch.setattr(
        "apps.products.dispatch_pending.dispatch_pending_processing",
        lambda *args, **kwargs: None,
    )

    item = _make_item(name="Widget B", sku="W-B", on_hand=20, available=20)
    order, source_line = _make_order_with_line(
        item=item,
        placed=10,
        actioned=8,
        remaining=2,
    )

    with pytest.raises(TransferQuantityError):
        save_transaction_with_lines(
            model_key="invoice",
            header_data={
                "status": "pending",
                "parent_model": "order",
                "parent_id": order.id,
                "totals": {},
                "finance": {},
            },
            lines_data=[
                {
                    "quantity": {"placed": 3, "actioned": 3, "remaining": 0},
                    "item": {"id": item.id, "item_id": item.id, "sku": item.sku},
                    "price": {"unit": 10, "extended": 30},
                    "cost": {"unit": 5, "extended": 15},
                    "refs": {
                        "source": {
                            "order_line_id": source_line.id,
                            "order_id": order.id,
                            "converted_from": "order",
                        }
                    },
                    "_dirty": True,
                }
            ],
            request=None,
            verify_calculations=False,
            save_only_dirty=True,
        )


@pytest.mark.django_db
def test_transfer_blocks_when_inventory_insufficient(monkeypatch):
    monkeypatch.setattr(
        "apps.products.dispatch_pending.dispatch_pending_processing",
        lambda *args, **kwargs: None,
    )

    item = _make_item(name="Widget C", sku="W-C", on_hand=2, available=2)
    order, source_line = _make_order_with_line(
        item=item,
        placed=5,
        actioned=0,
        remaining=5,
    )

    with pytest.raises(InsufficientInventoryError):
        save_transaction_with_lines(
            model_key="invoice",
            header_data={
                "status": "pending",
                "parent_model": "order",
                "parent_id": order.id,
                "totals": {},
                "finance": {},
            },
            lines_data=[
                {
                    "quantity": {"placed": 3, "actioned": 3, "remaining": 0},
                    "item": {"id": item.id, "item_id": item.id, "sku": item.sku},
                    "price": {"unit": 10, "extended": 30},
                    "cost": {"unit": 5, "extended": 15},
                    "refs": {
                        "source": {
                            "order_line_id": source_line.id,
                            "order_id": order.id,
                            "converted_from": "order",
                        }
                    },
                    "_dirty": True,
                }
            ],
            request=None,
            verify_calculations=False,
            save_only_dirty=True,
        )
