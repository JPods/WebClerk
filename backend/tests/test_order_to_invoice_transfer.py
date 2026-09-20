import pytest
from apps.orgs.models import OrgBase
from apps.transactions.models import Order, OrderLine, Invoice, InvoiceLine
from apps.transactions.services.convert.convert_order_to_invoice import (
    transfer_order_to_invoice,
    OrderToInvoiceTransferError,
)
from apps.transactions.services.transaction_save import save_transaction_with_lines


@pytest.fixture
def customer_a():
    return OrgBase.objects.create(company="Customer A", org_type="customer")


@pytest.fixture
def customer_b():
    return OrgBase.objects.create(company="Customer B", org_type="customer")


@pytest.fixture
def customer_c():
    return OrgBase.objects.create(company="Customer C", org_type="customer")


def _save_reviewed_invoice(monkeypatch, result):
    """Save the lines a conversion returned for review — the step that creates lines."""
    monkeypatch.setattr(
        "apps.products.dispatch_pending.dispatch_pending_processing",
        lambda *args, **kwargs: None,
    )
    return save_transaction_with_lines(
        model_key="invoice",
        header_data={"id": result["invoice_id"]},
        lines_data=result["lines"],
        request=None,
        verify_calculations=False,
    )


@pytest.mark.django_db
def test_transfer_all_lines_success(customer_a, monkeypatch):
    order = Order.objects.create(status='confirmed', customer_id=customer_a.id)
    l1 = OrderLine.objects.create(order=order, item={'description': 'Item 1'}, price={'amount': 100.0, 'unit': 100.0}, quantity={'active': 1})
    l2 = OrderLine.objects.create(order=order, item={'description': 'Item 2'}, price={'amount': 200.0, 'unit': 100.0}, quantity={'active': 2})

    result = transfer_order_to_invoice(order=order, transfer_all=True, invoice_status='pending', preserve_order=True)
    assert result['success'] is True
    inv = Invoice.objects.get(id=result['invoice_id'])
    assert inv.customer_id == customer_a.id
    assert inv.parent_model == 'order'
    assert inv.parent_id == order.id
    assert inv.refs['source']['converted_from'] == 'order'

    # Conversion creates the header only; lines come back for review.
    assert result['lines_for_review'] == 2
    assert InvoiceLine.objects.filter(invoice=inv).count() == 0
    l1.refresh_from_db()
    assert l1.quantity['remaining'] == 1

    _save_reviewed_invoice(monkeypatch, result)
    children = InvoiceLine.objects.filter(invoice=inv)
    assert sorted(c.parent_line_id for c in children) == sorted([l1.id, l2.id])
    for ol in (l1, l2):
        ol.refresh_from_db()
        assert ol.quantity['remaining'] == 0
        assert ol.status == 'transferred'


@pytest.mark.django_db
def test_transfer_selected_lines_only(customer_b, monkeypatch):
    order = Order.objects.create(status='confirmed', customer_id=customer_b.id)
    l1 = OrderLine.objects.create(order=order, item={'description': 'Item 1'}, price={'amount': 100.0}, quantity={'active': 1})
    l2 = OrderLine.objects.create(order=order, item={'description': 'Item 2'}, price={'amount': 200.0}, quantity={'active': 2})
    res = transfer_order_to_invoice(order=order, line_ids=[l1.id], transfer_all=False)
    assert res['lines_for_review'] == 1
    assert res['lines'][0]['refs']['source']['order_line_id'] == l1.id

    _save_reviewed_invoice(monkeypatch, res)
    l1.refresh_from_db(); l2.refresh_from_db()
    assert l1.quantity['remaining'] == 0
    assert l2.quantity['remaining'] == 2
    assert InvoiceLine.objects.filter(invoice_id=res['invoice_id'], parent_line_id=l1.id).count() == 1
    assert InvoiceLine.objects.filter(parent_line_id=l2.id).count() == 0

@pytest.mark.django_db
def test_validation_errors(customer_c):
    order = Order.objects.create(status='confirmed', customer_id=customer_c.id)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, line_ids=None, transfer_all=False)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, line_ids=[999], transfer_all=False)
    with pytest.raises(OrderToInvoiceTransferError):
        transfer_order_to_invoice(order=order, transfer_all=True)
