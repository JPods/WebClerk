"""An invoice's Financials may show its order's value and what is left unfilled on it, labelled as
the order's; every total on the invoice is the invoice's own (Bill, 2026-11-08). The summary is
served on the GET, never stored."""
import pytest

from apps.orgs.models import OrgBase
from apps.transactions.models import Order, OrderLine
from apps.transactions.services.convert.convert import convert_order_to_invoice
from apps.transactions.services.parent_summary import parent_summary
from tests.utils import save_document


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


@pytest.fixture
def admin_client(client, django_user_model):
    admin = django_user_model.objects.create_user(email='parent-summary@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    return client


def _order_and_invoice():
    buyer = OrgBase.objects.create(company='zz Parent Summary Co', org_type='customer', is_active=True)
    order = Order.objects.create(status='active', customer_id=buyer.pk, finance={"sales_tax_rate": 0})
    line = OrderLine.objects.create(order=order, item={'description': 'Widget'},
                                    price={'unit': 10.0, 'precision': 2}, cost={'unit': 6.0},
                                    quantity={'active': 11, 'precision': 2})
    result = convert_order_to_invoice(order.pk)
    inv_id = result['invoice_id']
    from apps.transactions.models import InvoiceLine
    child = InvoiceLine.objects.get(invoice_id=inv_id)
    # The invoice bills 8 of the 11: 3 stay unfilled on the order.
    save_document(model_key='invoice', header_data={'id': inv_id},
                  lines_data=[{'id': child.pk, 'quantity': {**child.quantity, 'active': 8, 'staged': 8}, '_dirty': True}])
    order.refresh_from_db(); line.refresh_from_db()
    return order, line, inv_id


@pytest.mark.django_db
def test_the_invoice_carries_its_orders_value_and_unfilled_value(admin_client):
    order, line, inv_id = _order_and_invoice()
    assert line.quantity['remaining'] == 3
    r = admin_client.get(f'/wcapi/invoice/{inv_id}/')
    assert r.status_code == 200, r.content
    record = r.json()['data']['record']
    summary = record['parent_summary']
    assert summary['model'] == 'order' and summary['id'] == order.pk and summary['ida'] == order.ida
    assert summary['total'] == order.totals['total'] and summary['amount'] == order.totals['amount']
    assert summary['unfilled'] == pytest.approx(3 * 10.0)
    # The invoice's own totals are the invoice's: 8 × 10, not the order's 11 × 10.
    assert record['totals']['amount'] == pytest.approx(80.0)


@pytest.mark.django_db
def test_a_document_without_a_parent_carries_none(admin_client):
    order, _line, _inv = _order_and_invoice()
    r = admin_client.get(f'/wcapi/order/{order.pk}/')
    assert r.json()['data']['record']['parent_summary'] is None
    assert parent_summary(order) is None
