"""Convert saves the parent only; its lines are proposed and saved by the first save (Bill,
2026-11-13: "save the record to get the ida, but keep the lines as an array without ida while
users adjust quantities … the inventory changes will not save until the user saves the parent
transaction for the first time").
"""
import pytest

from apps.core.models import Pending
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.core.services.verbs import run_command
from apps.products.models import Item
from apps.transactions.models import Invoice, InvoiceLine, Order, OrderLine
from apps.transactions.services.convert.convert import convert_record, proposed_lines
from tests.test_stock_layers_follow_sales import _stocked

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]

SYSTEM = Actor.system(source='test')


def _order(*lines):
    from apps.orgs.models import OrgBase
    buyer = OrgBase.objects.create(company='Buyer', org_type='customer', is_active=True)
    order = Order.objects.create(status='confirmed', customer_id=buyer.pk, finance={'sales_tax_rate': 0})
    made = [OrderLine.objects.create(
        order=order, item={'item_id': item.pk, 'id_num': item.pk, 'description': item.name},
        quantity={'active': qty}, price={'unit': 10, 'precision': 2}, cost={'unit': 0})
        for item, qty in lines]
    return order, made


def _on_hand(item):
    return Item.objects.get(pk=item.pk).quantity['on_hand']


def test_convert_saves_the_parent_and_moves_nothing():
    item, _ = _stocked()                                   # 15 on hand
    order, (line,) = _order((item, 6))
    pendings = Pending.objects.count()
    result = convert_record(SYSTEM, 'order', order.pk, 'invoice')
    invoice = Invoice.objects.get(pk=result['invoice_id'])
    assert invoice.ida and invoice.config.get('is_new') is True
    assert invoice.refs['source'] == {'converted_from': 'order', 'order_id': order.pk}
    assert not InvoiceLine.objects.filter(invoice=invoice).exists()
    assert _on_hand(item) == 15 and Pending.objects.count() == pendings
    line.refresh_from_db()
    assert line.quantity['remaining'] == 6                 # nothing is claimed yet


def test_propose_returns_the_lines_unsaved_and_again_on_a_second_ask():
    item, _ = _stocked(layers=((4, '1.00'),))              # 4 on hand
    order, (line,) = _order((item, 10))
    invoice_id = convert_record(SYSTEM, 'order', order.pk, 'invoice')['invoice_id']
    first = run_command(SYSTEM, 'propose', 'invoice', invoice_id, {})
    again = run_command(SYSTEM, 'propose', 'invoice', invoice_id, {})
    assert first == again
    (proposed,) = first['lines']
    assert proposed['_from'] == line.pk and proposed['_new'] is True and 'id' not in proposed
    assert (proposed['quantity']['active'], proposed['quantity']['staged']) == (4, 10)
    assert any('4 of 10 invoiced' in m for m in first['messages'])
    assert not InvoiceLine.objects.filter(invoice_id=invoice_id).exists()


def test_the_first_save_posts_once_at_the_quantity_the_person_set():
    item, _ = _stocked()                                   # 15 on hand
    order, (line,) = _order((item, 6))
    invoice_id = convert_record(SYSTEM, 'order', order.pk, 'invoice')['invoice_id']
    moves = Pending.objects.count()
    save_record(SYSTEM, {'lines': [{'_from': line.pk, 'quantity': {'active': 2}}]},
                model_key='invoice', record_id=invoice_id)
    (saved,) = InvoiceLine.objects.filter(invoice_id=invoice_id)
    assert (saved.quantity['active'], saved.quantity['staged']) == (2, 6)
    assert saved.price['unit'] == 10                       # built from the order line, not sent
    assert _on_hand(item) == 13
    line.refresh_from_db()
    assert line.quantity['remaining'] == 4
    stock_moves = [p for p in Pending.objects.order_by('pk')[moves:]
                   if 'on_hand' in str(p.changes)]
    assert len(stock_moves) == 1                           # one movement, not +6 then −4
    assert 'is_new' not in Invoice.objects.get(pk=invoice_id).config
    assert proposed_lines(Invoice.objects.get(pk=invoice_id), 'invoice') == ([], [])


def test_a_line_sent_without_a_quantity_takes_what_is_in_stock_at_the_save():
    item, layers = _stocked(layers=((10, '1.00'),))
    order, (line,) = _order((item, 10))
    invoice_id = convert_record(SYSTEM, 'order', order.pk, 'invoice')['invoice_id']
    other, (other_line,) = _order((item, 7))               # someone else ships 7 meanwhile
    other_id = convert_record(SYSTEM, 'order', other.pk, 'invoice')['invoice_id']
    save_record(SYSTEM, {'lines': [{'_from': other_line.pk}]}, model_key='invoice', record_id=other_id)
    result = save_record(SYSTEM, {'lines': [{'_from': line.pk}]}, model_key='invoice',
                         record_id=invoice_id)
    (saved,) = InvoiceLine.objects.filter(invoice_id=invoice_id)
    assert (saved.quantity['active'], saved.quantity['staged']) == (3, 10)
    assert any('3 of 10 invoiced, 7 stays on the order' in m for m in result.messages)


def test_a_source_line_is_not_put_on_the_document_twice():
    item, _ = _stocked()
    order, (line,) = _order((item, 6))
    invoice_id = convert_record(SYSTEM, 'order', order.pk, 'invoice')['invoice_id']
    save_record(SYSTEM, {'lines': [{'_from': line.pk, 'quantity': {'active': 2}}]},
                model_key='invoice', record_id=invoice_id)
    with pytest.raises(Refused) as refused:
        save_record(SYSTEM, {'lines': [{'_from': line.pk}]}, model_key='invoice', record_id=invoice_id)
    assert refused.value.code == 'line_already_on_document'


def test_a_line_of_another_document_is_refused():
    item, _ = _stocked()
    order, _lines = _order((item, 6))
    _other, (stranger,) = _order((item, 1))
    invoice_id = convert_record(SYSTEM, 'order', order.pk, 'invoice')['invoice_id']
    with pytest.raises(Refused) as refused:
        save_record(SYSTEM, {'lines': [{'_from': stranger.pk}]}, model_key='invoice', record_id=invoice_id)
    assert refused.value.code == 'no_lines'


def test_from_on_a_document_that_was_not_converted_is_refused():
    invoice = Invoice.objects.create(status='planned')
    with pytest.raises(Refused) as refused:
        save_record(SYSTEM, {'lines': [{'_from': 1}]}, model_key='invoice', record_id=invoice.pk)
    assert refused.value.code == 'not_converted'


def test_convert_no_longer_takes_lines():
    item, _ = _stocked()
    order, (line,) = _order((item, 6))
    with pytest.raises(Refused) as refused:
        run_command(SYSTEM, 'convert', 'order', order.pk,
                    {'to': 'invoice', 'lines': [{'line_id': line.pk, 'qty': 1}]})
    assert refused.value.code == 'lines_go_in_the_save'
