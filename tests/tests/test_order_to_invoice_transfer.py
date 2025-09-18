import pytest
from apps.transactions.models import SalesOrder, SalesOrderLine, Invoice
from apps.transactions.services.order_to_invoice import (
    transfer_order_to_invoice,
    OrderToInvoiceTransferError,
)

@pytest.mark.django_db
def test_transfer_all_lines_success():
    order = SalesOrder.objects.create(status='confirmed', party_id=123)
    SalesOrderLine.objects.create(parent=order, price={'extended': 100.0, 'unit': 100.0}, quantity={'invoiced': 0, 'remaining': 1})
    SalesOrderLine.objects.create(parent=order, price={'extended': 200.0, 'unit': 100.0}, quantity={'invoiced': 0, 'remaining': 2})

    result = transfer_order_to_invoice(order=order, transfer_all=True, invoice_status='pending', preserve_order=True)
    assert result['success'] is True
    inv = Invoice.objects.get(id=result['invoice_id'])
    assert inv.party_id == 123
    assert inv.refs['source']['sales_order_id'] == order.id

@pytest.mark.django_db
def test_transfer_selected_lines_only():
    order = SalesOrder.objects.create(status='confirmed', party_id=456)
    l1 = SalesOrderLine.objects.create(parent=order, price={'extended': 100.0}, quantity={'invoiced': 0, 'remaining': 1})
    l2 = SalesOrderLine.objects.create(parent=order, price={'extended': 200.0}, quantity={'invoiced': 0, 'remaining': 2})
    res = transfer_order_to_invoice(order=order, line_ids=[l1.id], transfer_all=False)
    assert res['lines_transferred'] == 1
    l1.refresh_from_db(); l2.refresh_from_db()
    assert l1.quantity['remaining'] == 0
    assert l2.quantity['remaining'] == 2

@pytest.mark.django_db
def test_validation_errors():
    order = SalesOrder.objects.create(status='confirmed', party_id=300)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, line_ids=None, transfer_all=False)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, line_ids=[999], transfer_all=False)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, transfer_all=True)