import pytest

from apps.products.models import Item
from apps.transactions.models import Invoice, InvoiceLine, Order, OrderLine
from apps.core.services.door import Refused
from tests.utils import save_document


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


def _make_order_with_line(*, item: Item, active: float, already_invoiced: float = 0):
    """Order line with `active` ordered; `already_invoiced` becomes a prior invoice
    child line, so the order line's remaining = active - already_invoiced (computed)."""
    order = Order.objects.create(status="confirmed")
    line = OrderLine.objects.create(
        order=order,
        item_fk=item,
        item={"id": item.id, "item_id": item.id, "sku": item.sku},
        quantity={"active": active, "precision": 2},
        price={"unit": 10, "amount": 10 * active},
        cost={"unit": 5, "extended": 5 * active},
    )
    if already_invoiced:
        prior = Invoice.objects.create(status="pending", parent_model="order", parent_id=order.id)
        InvoiceLine.objects.create(
            invoice=prior,
            item={"id": item.id, "item_id": item.id, "sku": item.sku},
            quantity={"active": already_invoiced},
            refs={"source": {"order_line_id": line.id, "order_id": order.id}},
        )
    line.refresh_from_db()
    assert line.quantity["remaining"] == active - already_invoiced
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
        active=10,
        already_invoiced=2,
    )

    result = save_document(
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
                "quantity": {"active": 3},
                "item": {"id": item.id, "item_id": item.id, "sku": item.sku},
                "price": {"unit": 10, "amount": 30},
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
    )

    assert result["action"] == "created"
    source_line.refresh_from_db()
    # remaining = active 10 - children (2 prior + 3 new)
    assert source_line.quantity["remaining"] == 5
    assert source_line.status != "transferred"

    inv = Invoice.objects.get(pk=result["header"]["id"])
    assert inv.parent_model == "order"
    assert inv.parent_id == order.id
    new_lines = InvoiceLine.objects.filter(invoice=inv)
    assert new_lines.count() == 1
    assert new_lines.first().parent_line_id == source_line.id


@pytest.mark.django_db
def test_transfer_blocks_when_requested_exceeds_source_remaining(monkeypatch):
    monkeypatch.setattr(
        "apps.products.dispatch_pending.dispatch_pending_processing",
        lambda *args, **kwargs: None,
    )

    item = _make_item(name="Widget B", sku="W-B", on_hand=20, available=20)
    order, source_line = _make_order_with_line(
        item=item,
        active=10,
        already_invoiced=8,
    )

    with pytest.raises(Refused, match='has 2 left') as refused:
        save_document(
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
                    "quantity": {"active": 3},
                    "item": {"id": item.id, "item_id": item.id, "sku": item.sku},
                    "price": {"unit": 10, "amount": 30},
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
        active=5,
    )

    with pytest.raises(Refused, match='available') as refused:
        save_document(
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
                    "quantity": {"active": 3},
                    "item": {"id": item.id, "item_id": item.id, "sku": item.sku},
                    "price": {"unit": 10, "amount": 30},
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
        )


@pytest.mark.django_db
def test_order_from_quote_may_backorder(monkeypatch):
    """Stock is checked on invoices only: an order saved from a quote backorders."""
    monkeypatch.setattr(
        "apps.products.dispatch_pending.dispatch_pending_processing",
        lambda *args, **kwargs: None,
    )
    from apps.transactions.models import Quote, QuoteLine

    item = _make_item(name="Widget S", sku="W-S", on_hand=1, available=1)
    quote = Quote.objects.create(status="planned")
    source = QuoteLine.objects.create(
        quote=quote,
        item_fk=item,
        item={"id": item.id, "item_id": item.id, "sku": item.sku},
        quantity={"staged": 5, "active": 5, "precision": 2},
        price={"unit": 10, "amount": 50},
        cost={"unit": 5, "extended": 25},
    )

    result = save_document(
        model_key="order",
        header_data={"status": "confirmed", "parent_model": "quote", "parent_id": quote.id,
                     "totals": {}, "finance": {}},
        lines_data=[{
            "quantity": {"staged": 5, "active": 5},
            "item": {"id": item.id, "item_id": item.id, "sku": item.sku},
            "price": {"unit": 10, "amount": 50},
            "cost": {"unit": 5, "extended": 25},
            "refs": {"source": {"quote_line_id": source.id, "quote_id": quote.id}},
            "_dirty": True,
        }],
    )

    order_line = OrderLine.objects.get(order_id=result["header"]["id"])
    assert order_line.parent_line_id == source.id
    source.refresh_from_db()
    assert source.quantity["remaining"] == 0
