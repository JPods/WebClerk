"""Conversions save the target with its lines (Bill, 2026-11-08: "save with lines").

The person reviews and edits a saved planned document; nothing lives only in the browser, so
leaving the record loses nothing. Replaces the 2026-09-27 review-before-save for conversions,
after an unsaved review left purchase 1028-po with no lines and re-seeded stale lines onto the
saved invoice 1056-inv during Bill's flight-simulator walk.
"""
import pytest

from apps.orgs.models import OrgBase
from apps.transactions.models import (Quote, QuoteLine, Order, OrderLine, Invoice, InvoiceLine,
                                      Purchase, PurchaseLine)
from apps.transactions.services import validate_status
from apps.transactions.services.convert.convert import (
    convert_quote_to_order, convert_quote_to_invoice, convert_order_to_invoice,
    convert_order_to_purchase)
from tests.utils import save_document


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


@pytest.fixture
def customer():
    return OrgBase.objects.create(company="zz Save With Lines Co", org_type="customer")


@pytest.fixture
def vendor():
    return OrgBase.objects.create(company="zz Save With Lines Vendor", org_type="vendor")


def _quote(customer, quantities=(4, 6)):
    quote = Quote.objects.create(status='active', customer_id=customer.id)
    lines = [QuoteLine.objects.create(quote=quote, item={'description': f'Item {i}'},
                                      price={'unit': 10.0, 'precision': 2}, cost={'unit': 6.0},
                                      quantity={'active': q, 'precision': 2})
             for i, q in enumerate(quantities, 1)]
    return quote, lines


def _order(customer, quantities=(4, 6)):
    order = Order.objects.create(status='active', customer_id=customer.id)
    lines = [OrderLine.objects.create(order=order, item={'description': f'Item {i}'},
                                      price={'unit': 10.0, 'precision': 2}, cost={'unit': 6.0},
                                      quantity={'active': q, 'precision': 2})
             for i, q in enumerate(quantities, 1)]
    return order, lines


PAIRS = {
    ('quote', 'order'): (_quote, convert_quote_to_order, Order, OrderLine, 'order'),
    ('quote', 'invoice'): (_quote, convert_quote_to_invoice, Invoice, InvoiceLine, 'invoice'),
    ('order', 'invoice'): (_order, convert_order_to_invoice, Invoice, InvoiceLine, 'invoice'),
    ('order', 'purchase'): (_order, convert_order_to_purchase, Purchase, PurchaseLine, 'purchase'),
}
#: The pairs whose child line consumes the source line (line_parent.PARENT_OF): a quote line by
#: order lines and, over the counter, by invoice lines; an order line by invoice lines. A purchase
#: does not consume the order it buys for.
CONSUMING = [('quote', 'order'), ('quote', 'invoice'), ('order', 'invoice')]


@pytest.mark.django_db
@pytest.mark.parametrize('pair', list(PAIRS), ids=lambda p: f'{p[0]}_to_{p[1]}')
def test_the_target_is_saved_with_its_lines_at_the_convert(pair, customer):
    make, convert, Target, TargetLine, fk = PAIRS[pair]
    source, src_lines = make(customer)
    result = convert(source.pk)
    target = Target.objects.get(pk=result[f'{pair[1]}_id'])
    saved = list(TargetLine.objects.filter(**{fk: target}).order_by('pk'))
    assert result['lines_saved'] == 2 and len(saved) == 2
    assert target.status == 'planned' and target.parent_id == source.pk
    by_source = {child.refs['source'][f'{pair[0]}_line_id']: child for child in saved}
    assert set(by_source) == {src.pk for src in src_lines}
    for src in src_lines:
        child = by_source[src.pk]
        assert child.quantity['active'] == src.quantity['active']
        if pair in CONSUMING:
            assert child.parent_line_id == src.pk
    assert 'lines' not in result and 'lines_for_review' not in result


@pytest.mark.django_db
@pytest.mark.parametrize('pair', CONSUMING, ids=lambda p: f'{p[0]}_to_{p[1]}')
def test_the_source_remaining_is_reduced_once(pair, customer):
    make, convert, Target, TargetLine, fk = PAIRS[pair]
    source, src_lines = make(customer, quantities=(5,))
    result = convert(source.pk)
    src_lines[0].refresh_from_db()
    assert src_lines[0].quantity['remaining'] == 0
    # Saving the saved target again (the person's review) consumes nothing more ...
    save_document(model_key=pair[1], header_data={'id': result[f'{pair[1]}_id'], 'priority': 'high'},
                  lines_data=[])
    src_lines[0].refresh_from_db()
    assert src_lines[0].quantity['remaining'] == 0
    # ... and trimming the child's quantity gives the difference back: remaining is recomputed
    # from the children, never decremented (line_parent.py).
    child = TargetLine.objects.get(**{fk + '_id': result[f'{pair[1]}_id']})
    save_document(model_key=pair[1], header_data={'id': result[f'{pair[1]}_id']},
                  lines_data=[{'id': child.pk, 'quantity': {**child.quantity, 'active': 2, 'staged': 2},
                               '_dirty': True}])
    src_lines[0].refresh_from_db()
    assert src_lines[0].quantity['remaining'] == 3


@pytest.mark.django_db
@pytest.mark.parametrize('pair', list(PAIRS), ids=lambda p: f'{p[0]}_to_{p[1]}')
def test_leaving_without_saving_loses_nothing(pair, customer):
    """What the browser shows after the convert is the database: no unsaved review copy."""
    make, convert, Target, TargetLine, fk = PAIRS[pair]
    source, _ = make(customer)
    result = convert(source.pk)
    # A fresh read, as another window or a reload would make it, has the lines.
    fresh = Target.objects.get(pk=result[f'{pair[1]}_id'])
    assert fresh.lines.count() == 2
    assert fresh.lines.filter(quantity__active__gt=0).count() == 2


@pytest.mark.django_db
def test_a_purchase_without_a_vendor_is_saved_and_coached(customer):
    order, _ = _order(customer)
    result = convert_order_to_purchase(order.pk)              # no vendor on the order or named
    po = Purchase.objects.get(pk=result['purchase_id'])
    assert po.vendor_id is None and po.lines.count() == 2, 'never a silent empty purchase'
    assert any('vendor' in m.lower() for m in result['messages']), result['messages']
    # The release gate keeps refusing until a vendor is named.
    assert 'vendor' in validate_status.incomplete(po, 'purchase')


@pytest.mark.django_db
def test_a_purchase_with_a_vendor_is_not_coached(customer, vendor):
    order, _ = _order(customer)
    result = convert_order_to_purchase(order.pk, vendor_id=vendor.pk)
    assert not any('vendor' in m.lower() for m in result['messages']), result['messages']
    assert Purchase.objects.get(pk=result['purchase_id']).vendor_id == vendor.pk


@pytest.mark.django_db
def test_a_second_save_of_the_converted_document_does_not_duplicate_its_lines(customer):
    """The lines exist from the convert, with ids; a later save edits them by id. Nothing in
    the browser holds an id-less copy any more (the review handoff is gone), so no save can
    add the converted lines a second time (invoice 1056-inv's risk, 2026-11-08)."""
    quote, _ = _quote(customer)
    result = convert_quote_to_order(quote.pk)
    order = Order.objects.get(pk=result['order_id'])
    lines = list(order.lines.order_by('pk'))
    assert len(lines) == 2
    save_document(model_key='order', header_data={'id': order.pk},
                  lines_data=[{'id': l.pk, 'quantity': l.quantity, 'price': l.price, '_dirty': True} for l in lines])
    save_document(model_key='order', header_data={'id': order.pk, 'priority': 'high'}, lines_data=[])
    assert list(order.lines.order_by('pk').values_list('pk', flat=True)) == [l.pk for l in lines]


@pytest.mark.django_db
def test_a_quote_line_is_consumed_by_its_order_lines_and_its_invoice_lines_together(customer):
    """quote 10 → order 6 and, over the counter, invoice 3: the quote line has 1 left."""
    quote, (ql,) = _quote(customer, quantities=(10,))
    from apps.transactions.services.convert.convert import _take_named
    convert_quote_to_order(quote.pk, line_ids=[ql.pk])          # takes all 10 ...
    order_line = OrderLine.objects.get(parent_line_id=ql.pk)
    save_document(model_key='order', header_data={'id': order_line.order_id},
                  lines_data=[{'id': order_line.pk, 'quantity': {**order_line.quantity, 'active': 6, 'staged': 6},
                               '_dirty': True}])                    # ... trimmed to 6
    ql.refresh_from_db(); assert ql.quantity['remaining'] == 4
    from apps.transactions.services.convert.convert import convert_record, _system
    convert_record(_system(), 'quote', quote.pk, 'invoice', line_ids=[ql.pk],
                   take=_take_named([{'line_id': ql.pk, 'qty': 3}], 'quote'))
    ql.refresh_from_db(); assert ql.quantity['remaining'] == 1
    inv_line = InvoiceLine.objects.get(parent_line_id=ql.pk, refs__source__quote_line_id=ql.pk)
    assert inv_line.quantity['active'] == 3


@pytest.mark.django_db
def test_an_invoice_line_from_an_order_does_not_count_against_a_quote_line_with_the_same_id(customer):
    """parent_line_id alone is ambiguous for an invoice line (order line or quote line); the
    refs.source key says which, and the aggregate reads it."""
    order, (ol,) = _order(customer, quantities=(5,))
    quote, (ql,) = _quote(customer, quantities=(7,))
    convert_order_to_invoice(order.pk)                         # invoice line → order line
    inv_line = InvoiceLine.objects.get(parent_line_id=ol.pk)
    # Force the id collision the aggregate must see through.
    InvoiceLine.objects.filter(pk=inv_line.pk).update(parent_line_id=ql.pk)
    from apps.transactions.services.line_parent import _aggregate_children
    assert _aggregate_children('quoteline', ql.pk) == (0.0, 0)
    ol.refresh_from_db(); assert ol.quantity['remaining'] == 0


@pytest.mark.django_db
def test_a_named_quantity_above_the_source_remaining_is_refused(customer):
    """The caller only names line ids and a qty; the transfer check in the same unit caps the
    qty at the source line's remaining, so nobody converts 50 of a remaining 3."""
    from apps.core.services.door import Refused
    from apps.transactions.services.convert.convert import convert_record, _system, _take_named
    quote, (ql,) = _quote(customer, quantities=(3,))
    with pytest.raises(Refused) as exc:
        convert_record(_system(), 'quote', quote.pk, 'order', line_ids=[ql.pk],
                       take=_take_named([{'line_id': ql.pk, 'qty': 50}], 'quote'))
    assert exc.value.code == 'transfer_exceeds_remaining'
    assert Order.objects.filter(parent_id=quote.pk).count() == 0
    ql.refresh_from_db(); assert ql.quantity['remaining'] == 3
