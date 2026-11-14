"""Negative quantities, journalized (Bill, 2026-11-13: "they will have reasons to run negative
quantities. We will have to journal these and check the outcomes"). Each case ends with the books
check: GL inventory = what the layers hold."""
import pytest

from tests.test_receipt_journal import COST, _run, _vendor
from tests.test_stock_layers_follow_sales import _stocked

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]


def _rows(model, pk):
    from apps.accounts.models import GlJournal
    out = {}
    for r in GlJournal.objects.filter(source_model=model, source_id=pk):
        out[r.account] = round(out.get(r.account, 0) + float(r.debit or 0) - float(r.credit or 0), 2)
    return {k: v for k, v in out.items() if v}


def _books():
    from apps.core.services.balance_checker import check_gl_inventory
    return check_gl_inventory()


def _layers(item):
    from apps.products.models import InventoryLayer
    return sorted((float(l.quantity.get('received', 0)), float(l.quantity.get('issued', 0) or 0),
                   float(l.cost.get('landed', l.cost.get('unit_po', 0)) or 0))
                  for l in InventoryLayer.objects.filter(item_id=item.pk))


def test_a_credit_invoice_line_journalized():
    from apps.accounts.services.journalize import journalize_invoice
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Order, OrderLine
    from apps.transactions.services.convert.convert import convert_order_to_invoice
    item, _ = _stocked(layers=((5, '2.00'),))
    buyer = OrgBase.objects.create(company='Buyer', org_type='customer', is_active=True)
    order = Order.objects.create(status='confirmed', customer_id=buyer.pk, finance={'sales_tax_rate': 0})
    OrderLine.objects.create(order=order, item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
                             quantity={'active': -3}, price={'unit': 10, 'precision': 2}, cost={'unit': 0})
    invoice_id = convert_order_to_invoice(order.pk)['invoice_id']
    item.refresh_from_db()
    assert item.quantity['on_hand'] == 8, 'the credit puts 3 back on the shelf'
    out = journalize_invoice(invoice_id)
    assert out.get('created'), out
    rows = _rows('invoice', invoice_id)
    print('\nCREDIT rows', rows, 'layers', _layers(item))
    assert rows['1200-inventory'] == 6.0, 'inventory comes back at the cost its new layer carries'
    assert rows['5000-cost_of_goods_sold'] == -6.0
    assert rows['1100-accounts_receivable'] == -30.0, 'the customer is owed'
    assert round(sum(rows.values()), 2) == 0
    findings, _checked = _books()
    assert not findings, findings


def test_a_negative_receipt_line_is_refused():
    from apps.products.models import Warehouse
    from apps.transactions.models import Purchase, PurchaseLine
    item, _ = _stocked(layers=((5, '2.00'),))
    Warehouse.objects.get_or_create(code='MAIN', defaults={'name': 'Main', 'is_active': True})
    po = Purchase.objects.create(vendor_id=_vendor().pk, terms='N30')
    pol = PurchaseLine.objects.create(purchase=po, item={'item_id': item.pk, 'description': 'Widget'},
                                      quantity={'active': -3, 'staged': -3}, cost=dict(COST))
    # Not built (Bill, 2026-11-13: "leave them for now"): a receipt cannot take stock off the shelf.
    # The refusal is the layer's, raw; nothing moves.
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match='would create a layer holding -3'):
        _run('convert', 'purchase', po.pk, {'to': 'receipt'})
    item.refresh_from_db()
    assert item.quantity['on_hand'] == 5
