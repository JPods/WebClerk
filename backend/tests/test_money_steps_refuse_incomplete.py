"""The money steps refuse an incomplete document, with coaching (the team, 2026-11-06; Bill:
save stays permissive — a template order without a customer saves). Release, invoice (convert)
and journalize refuse a document that has no party, no terms or no lines; receiving (convert to
receipt) needs the vendor and lines, not terms (the lead, 2026-11-06); quote→order and
order→purchase are planning steps and free. The hard requirement lives on the state change,
not on save, and goes through the existing state-change code.
There is no ship step in WC3: an invoice's release is where goods leave."""
import pytest

from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.core.services.verbs import run_command
from apps.orgs.models import Customer, Vendor
from apps.transactions.models import (Invoice, InvoiceLine, Order, OrderLine, Purchase, PurchaseLine,
                                      Quote, QuoteLine, Receipt, ReceiptLine, Requisition, RequisitionLine,
                                      WorkOrder, WorkOrderLine)

pytestmark = pytest.mark.django_db

SELL_LINE = {'quantity': {'staged': 1, 'active': 1}, 'price': {'unit': 10, 'amount': 10}}
BUY_LINE = {'quantity': {'staged': 1, 'active': 1}, 'cost': {'unit': 10, 'amount': 10}}
SELL = {'quote': (Quote, QuoteLine), 'order': (Order, OrderLine), 'invoice': (Invoice, InvoiceLine)}
BUY = {'purchase': (Purchase, PurchaseLine), 'receipt': (Receipt, ReceiptLine)}
#: Lines only: a workorder builds, a requisition wants — neither names a party or terms.
LINES_ONLY = {'workorder': (WorkOrder, WorkOrderLine), 'requisition': (Requisition, RequisitionLine)}


@pytest.fixture
def admin(django_user_model):
    user = django_user_model.objects.create_superuser(
        email='steps@example.com', password=None, name_first='St', name_last='Eps', username='')
    return Actor(user=user, kind='user', source='wcapi')


@pytest.fixture
def terms():
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    return 'N30'


def _document(model_key, *, party=True, terms_ida='N30', lines=1, status='planned'):
    """A document with what the caller says it has; what it lacks is the test."""
    if model_key in SELL:
        Model, Line = SELL[model_key]
        org = Customer.objects.create(company='Steps Buyer') if party else None
        header = Model.objects.create(status=status, customer_id=org.pk if org else None, terms=terms_ida,
                                      finance={'sales_tax_rate': 0}, totals={'total': 10 * lines})
    elif model_key in BUY:
        Model, Line = BUY[model_key]
        org = Vendor.objects.create(company='Steps Seller') if party else None
        header = Model.objects.create(status=status, vendor_id=org.pk if org else None, terms=terms_ida,
                                      totals={'total': 10 * lines})
    else:
        Model, Line = LINES_ONLY[model_key]
        header = Model.objects.create(status=status)
    for _ in range(lines):
        spec = SELL_LINE if model_key in SELL else BUY_LINE
        if model_key == 'receipt':   # a receipt line's active quantity is the receive command's
            spec = {**spec, 'quantity': {'staged': 1}}
        Line.objects.create(**{model_key: header}, **spec)
    return header


def _refused(fn):
    with pytest.raises(Refused) as refused:
        fn()
    return refused.value


# ── release: status → released through the save door ──

@pytest.mark.parametrize('model_key,lack', [
    ('quote', 'party'), ('quote', 'terms'), ('quote', 'lines'),
    ('order', 'party'), ('order', 'terms'), ('order', 'lines'),
    ('invoice', 'party'), ('invoice', 'terms'), ('invoice', 'lines'),
    ('purchase', 'party'), ('purchase', 'terms'), ('purchase', 'lines'),
    ('requisition', 'lines'), ('workorder', 'lines'),
])
def test_release_refuses_an_incomplete_document_with_coaching(admin, terms, model_key, lack):
    doc = _document(model_key, party=lack != 'party', terms_ida='' if lack == 'terms' else terms,
                    lines=0 if lack == 'lines' else 1)
    refused = _refused(lambda: save_record(admin, {'id': doc.pk, 'version': doc.version, 'status': 'released'},
                                           model_key=model_key))
    assert refused.status == 409 and refused.code == 'incomplete_document'
    word = {'party': 'customer' if model_key in SELL else 'vendor', 'terms': 'terms', 'lines': 'line'}[lack]
    assert word in refused.message and 'release' in refused.message
    doc.refresh_from_db()
    assert doc.status == 'planned'


@pytest.mark.parametrize('model_key', ['quote', 'order', 'invoice', 'purchase', 'requisition', 'workorder'])
def test_a_complete_document_releases(admin, terms, model_key):
    doc = _document(model_key)
    save_record(admin, {'id': doc.pk, 'version': doc.version, 'status': 'released'}, model_key=model_key)
    doc.refresh_from_db()
    assert doc.status == 'released'


@pytest.mark.parametrize('model_key', ['quote', 'order', 'invoice', 'purchase', 'requisition', 'workorder'])
def test_an_incomplete_document_still_saves(admin, model_key):
    """Save is permissive (Bill: hollow records are a small price for saving partial work)."""
    doc = _document(model_key, party=False, terms_ida='', lines=0)
    save_record(admin, {'id': doc.pk, 'version': doc.version, 'comments': {'public': 'template'}}, model_key=model_key)
    doc.refresh_from_db()
    assert doc.comments.get('public') == 'template'


# ── convert: invoicing needs the customer, terms and lines; receiving needs the vendor and lines ──

@pytest.mark.parametrize('source,target,lack', [
    ('quote', 'invoice', 'party'), ('order', 'invoice', 'party'), ('order', 'invoice', 'terms'),
    ('order', 'invoice', 'lines'), ('purchase', 'receipt', 'party'), ('purchase', 'receipt', 'lines'),
])
def test_convert_refuses_an_incomplete_source(admin, terms, source, target, lack):
    doc = _document(source, party=lack != 'party', terms_ida='' if lack == 'terms' else terms,
                    lines=0 if lack == 'lines' else 1)
    refused = _refused(lambda: run_command(admin, 'convert', source, doc.pk, {'to': target}))
    assert refused.status == 409 and refused.code == 'incomplete_document'
    assert refused.details['missing'] == [{'party': 'customer' if source != 'purchase' else 'vendor',
                                           'terms': 'terms', 'lines': 'line'}[lack]]


def test_receiving_does_not_need_terms(admin):
    """Receiving is goods arriving; the terms bind at the vendor's bill (the lead, 2026-11-06)."""
    from apps.products.models import Warehouse
    Warehouse.objects.get_or_create(code='MAIN', defaults={'name': 'Main', 'is_active': True})
    po = _document('purchase', terms_ida='')
    run_command(admin, 'convert', 'purchase', po.pk, {'to': 'receipt'})
    assert Receipt.objects.filter(parent_id=po.pk, parent_model="purchase").exists()


def test_planning_converts_are_free(admin):
    """quote→order moves no money: a template quote without a customer becomes a template order
    (Bill: template orders without a customer are a person's own business)."""
    quote = _document('quote', party=False, terms_ida='')
    run_command(admin, 'convert', 'quote', quote.pk, {'to': 'order'})
    assert Order.objects.get(parent_id=quote.pk, parent_model="quote").customer_id is None


# ── journalize ──

@pytest.mark.parametrize('model_key,lack', [
    ('invoice', 'party'), ('invoice', 'terms'), ('invoice', 'lines'),
    ('receipt', 'party'), ('receipt', 'terms'), ('receipt', 'lines'),
    ('workorder', 'lines'),
])
def test_journalize_refuses_an_incomplete_document(admin, terms, chart_of_accounts, model_key, lack):
    doc = _document(model_key, party=lack != 'party', terms_ida='' if lack == 'terms' else terms,
                    lines=0 if lack == 'lines' else 1, status='released')
    refused = _refused(lambda: run_command(admin, 'journalize', model_key, doc.pk, {}))
    assert refused.status == 409 and refused.code == 'incomplete_document'
    doc.refresh_from_db()
    assert not doc.dt_journaled


# ── journalize: an invoice posts only once released (validate_status.JOURNALIZE_FROM) ──

@pytest.mark.parametrize('status', ['planned', 'signoff_request', 'on_hold'])
def test_journalize_refuses_an_invoice_that_is_not_released(admin, terms, chart_of_accounts, status):
    """Once posted no status moves (validate_transition), so a planned invoice posted would be
    planned forever — wc_demo held eleven such rows on 2026-11-07."""
    doc = _document('invoice', status=status)
    refused = _refused(lambda: run_command(admin, 'journalize', 'invoice', doc.pk, {}))
    assert refused.status == 409 and refused.code == 'not_released'
    assert status in refused.message and 'Release it first' in refused.message
    doc.refresh_from_db()
    assert not doc.dt_journaled and doc.status == status


def test_a_released_invoice_posts(admin, terms, chart_of_accounts):
    doc = _document('invoice', status='released')
    run_command(admin, 'journalize', 'invoice', doc.pk, {})
    doc.refresh_from_db()
    assert doc.dt_journaled and doc.status == 'released'


def test_the_invoice_report_shows_a_planned_invoice_waiting_and_a_released_one_ready(terms, chart_of_accounts):
    """The batch that took every unposted invoice is gone (Bill, 2026-11-07: never automatic); the
    report shows what may post and why the rest waits."""
    from apps.accounts.services.journalize_report import unposted
    planned, released = _document('invoice', status='planned'), _document('invoice', status='released')
    rows = {r['id']: r for r in unposted('invoice')['rows']}
    assert 'Release it first' in rows[planned.pk]['waiting'] and rows[planned.pk]['preview'] is None
    assert rows[released.pk]['waiting'] == '' and rows[released.pk]['preview']['entries']
