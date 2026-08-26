import pytest
from apps.orgs.models import OrgBase
from apps.transactions.models import Order, OrderLine, Invoice
from apps.transactions.services.order_to_invoice import (
    transfer_order_to_invoice,
    OrderToInvoiceTransferError,
)


@pytest.fixture
def customer_a():
    return OrgBase.objects.create(display_name="Customer A", org_type="customer")


@pytest.fixture
def customer_b():
    return OrgBase.objects.create(display_name="Customer B", org_type="customer")


@pytest.fixture
def customer_c():
    return OrgBase.objects.create(display_name="Customer C", org_type="customer")


@pytest.mark.django_db
def test_transfer_all_lines_success(customer_a):
    order = Order.objects.create(status='confirmed', customer_id=customer_a.id)
    OrderLine.objects.create(order=order, item={'description': 'Item 1'}, price={'extended': 100.0, 'unit': 100.0}, quantity={'invoiced': 0, 'remaining': 1})
    OrderLine.objects.create(order=order, item={'description': 'Item 2'}, price={'extended': 200.0, 'unit': 100.0}, quantity={'invoiced': 0, 'remaining': 2})

    result = transfer_order_to_invoice(order=order, transfer_all=True, invoice_status='pending', preserve_order=True)
    assert result['success'] is True
    inv = Invoice.objects.get(id=result['invoice_id'])
    assert inv.customer_id == customer_a.id
    assert inv.refs['source']['order_id'] == order.id

@pytest.mark.django_db
def test_transfer_selected_lines_only(customer_b):
    order = Order.objects.create(status='confirmed', customer_id=customer_b.id)
    l1 = OrderLine.objects.create(order=order, item={'description': 'Item 1'}, price={'extended': 100.0}, quantity={'invoiced': 0, 'remaining': 1})
    l2 = OrderLine.objects.create(order=order, item={'description': 'Item 2'}, price={'extended': 200.0}, quantity={'invoiced': 0, 'remaining': 2})
    res = transfer_order_to_invoice(order=order, line_ids=[l1.id], transfer_all=False)
    assert res['lines_transferred'] == 1
    l1.refresh_from_db(); l2.refresh_from_db()
    assert l1.quantity['remaining'] == 0
    assert l2.quantity['remaining'] == 2

@pytest.mark.django_db
def test_validation_errors(customer_c):
    order = Order.objects.create(status='confirmed', customer_id=customer_c.id)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, line_ids=None, transfer_all=False)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, line_ids=[999], transfer_all=False)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, transfer_all=True)
