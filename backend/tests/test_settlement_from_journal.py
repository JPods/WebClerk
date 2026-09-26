"""Fix #2: a document's received / paid / balance come from its applications.

Fable L2 H-1: ``compute_totals`` carried received forward from the stored totals, so a stored
number that went wrong stayed wrong (wc_demo invoices 75, 96–101: 734.00 applied, received 0.00),
and no check compared it with the journal. Bill, 2026-09-25/26: cash.available is the driving
value; received is Σ applications, no exceptions.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.core.models.pending import Pending
from apps.core.services.balance_checker import (
    check_document_settlement, check_orphan_applications)
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Invoice, InvoiceLine
from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
from apps.transactions.services.pricing.totals_compute import compute_totals, recalculate_totals

pytestmark = pytest.mark.django_db


def _customer(name='Journal Buyer'):
    return OrgBase.objects.create(company=name, org_type='customer', is_active=True)


def _invoice(customer, unit=100.00):
    inv = Invoice.objects.create(customer_id=customer.pk, finance={"sales_tax_rate": 0})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": unit, "precision": 2}, cost={"unit": 0})
    recalculate_totals(inv.pk, 'invoice')
    inv.refresh_from_db()
    return inv


def _pay(inv, customer, amount):
    cash = Cash.objects.create(amount=Decimal(amount), customer_id=customer.pk)
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal(amount), acted_by=1)
    inv.refresh_from_db()
    return cash


def _checks(inv):
    return {f['check'] for f in check_document_settlement() if f['record_id'] == inv.pk}


def test_a_recalculation_reads_received_from_the_applications_not_the_stored_totals():
    buyer = _customer()
    inv = _invoice(buyer, 100.00)
    _pay(inv, buyer, '40.00')
    assert inv.totals['received'] == 40.0

    # The drift wc_demo carries: the stored number rewritten to 0 with the application intact.
    Invoice.objects.filter(pk=inv.pk).update(totals={**inv.totals, 'received': 0.0, 'balance': 100.0})
    inv.refresh_from_db()
    assert 'invoice.received' in _checks(inv), 'the check sees the stored number disagree'

    recalculate_totals(inv.pk, 'invoice')
    inv.refresh_from_db()
    assert inv.totals['received'] == 40.0
    assert inv.totals['balance'] == 60.0
    assert inv.totals['cash_state'] == 'partial'
    assert not _checks(inv), 'journal and stored agree again'


def test_the_repair_re_spreads_the_ledger_echo():
    """Fable: recalculate_totals rebuilt the ledger only when total changed, so repairing
    received left ledger.value_available at the old spread and the org check went red."""
    from apps.accounts.models import Ledger
    buyer = _customer('Echo Buyer')
    inv = _invoice(buyer, 100.00)
    _pay(inv, buyer, '25.00')
    Invoice.objects.filter(pk=inv.pk).update(totals={**inv.totals, 'received': 0.0, 'balance': 100.0})
    Ledger.objects.filter(invoice_id=inv.pk, model_name='invoice').update(value_available=100.0)

    recalculate_totals(inv.pk, 'invoice')
    echo = sum(Decimal(str(v)) for v in Ledger.objects.filter(
        invoice_id=inv.pk, model_name='invoice').values_list('value_available', flat=True))
    assert Ledger.objects.filter(invoice_id=inv.pk, model_name='invoice').exists()
    assert echo == Decimal('75.00'), 'Σ ledger rows = the invoice balance'


def test_a_new_header_has_nothing_settled_and_asks_no_journal(django_assert_num_queries):
    header = SimpleNamespace(totals={'received': 999}, finance={}, customer_id=None)
    with django_assert_num_queries(0):
        received_adjusted = __import__(
            'apps.transactions.services.pricing.totals_compute',
            fromlist=['_settlement'])._settlement(header, 'invoice')
    assert received_adjusted == (Decimal(0), Decimal(0), Decimal(0))


def test_an_adjustment_lands_in_adjusted_not_received():
    buyer = _customer('Adjusted Buyer')
    inv = _invoice(buyer, 100.00)
    cash = Cash.objects.create(amount=Decimal('90.00'), customer_id=buyer.pk)
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal('90.00'), discount_amt=10, acted_by=1)
    recalculate_totals(inv.pk, 'invoice')
    inv.refresh_from_db()
    assert inv.totals['received'] == 90.0
    assert inv.totals['adjusted'] == 10.0
    assert inv.totals['balance'] == 0.0


def test_an_application_pointing_at_a_deleted_invoice_is_an_orphan():
    buyer = _customer('Orphan Buyer')
    inv = _invoice(buyer, 50.00)
    _pay(inv, buyer, '50.00')
    pending = Pending.objects.get(purpose='cash_application', changes__invoice_id=inv.pk)
    # The door refuses to delete an invoice with money applied (as it should); the wc_demo
    # orphans came from a raw purge. Point the application at an invoice that does not exist.
    gone = Invoice.objects.order_by('-pk').values_list('pk', flat=True).first() + 1000
    Pending.objects.filter(pk=pending.pk).update(changes={**pending.changes, 'invoice_id': gone})
    orphans = [f for f in check_orphan_applications() if f['record_id'] == pending.pk]
    assert orphans and 'invoice' in orphans[0]['message']


def test_compute_totals_accepts_a_header_without_a_pk():
    """Unit callers pass SimpleNamespace headers (Fable)."""
    header = SimpleNamespace(totals={}, finance={"sales_tax_rate": 0}, customer_id=None,
                             allocations=None)
    compute_totals(header, [], 'invoice')


def test_month_end_reports_real_sales_purchases_and_cash():
    """period_close summed a removed Invoice.total (and a Cash.total that never was) under
    except: every close reported 0 with 0 counts."""
    from datetime import datetime, timezone
    from apps.accounts.services.period_close import _generate_period_summary
    buyer = _customer('Month Buyer')
    a, b = _invoice(buyer, 30.00), _invoice(buyer, 70.00)
    Cash.objects.create(amount=Decimal('12.50'), customer_id=buyer.pk)
    now = datetime.now(timezone.utc)
    summary = _generate_period_summary(now.year, now.month)
    assert summary['invoice_count'] >= 2
    assert Decimal(str(summary['total_sales'])) >= Decimal('100.00')
    assert summary['cash_count'] >= 1 and Decimal(str(summary['total_cash_entries'])) >= Decimal('12.50')


def test_a_customer_statement_lists_its_open_invoices():
    """render_report filtered .exclude(balance=0) on a removed column and keyed a customer's
    statement on contact_id."""
    from apps.core.services.render_report import _load_statement_data
    buyer = _customer('Statement Buyer')
    open_inv = _invoice(buyer, 40.00)
    paid_inv = _invoice(buyer, 10.00)
    _pay(paid_inv, buyer, '10.00')
    data = _load_statement_data('orgbase', buyer.pk)
    ids = {i.pk for i in data['invoices']}
    assert open_inv.pk in ids and paid_inv.pk not in ids


def test_a_jpods_trip_is_paid_from_the_riders_prepaid_balance():
    """Bill, 2026-09-26: the trip is paid from prepaid Cash; received is the application."""
    from apps.core.models import Contact
    from apps.jpods.services.invoice_service import create_trip_invoice
    buyer = _customer('Rider Org')
    rider = Contact.objects.create(email='rider@jpods.test', customer_id=buyer.pk)
    Cash.objects.create(amount=Decimal('5.00'), customer_id=buyer.pk)
    result = create_trip_invoice({'contact_id': rider.pk, 'origin_station_id': 'S001',
                                  'destination_station_id': 'S003', 'price': '3.25', 'currency': 'USD'})
    assert 'error' not in result, result
    inv = Invoice.objects.get(pk=result['invoice_id'])
    assert inv.totals['received'] == 3.25 and inv.totals['balance'] == 0.0
    assert Pending.objects.filter(purpose='cash_application', changes__invoice_id=inv.pk,
                                  changes__state='applied').count() == 1
    assert not _checks(inv)


def test_a_short_prepaid_balance_refuses_the_trip_and_writes_nothing():
    from apps.core.models import Contact
    from apps.jpods.services.invoice_service import create_trip_invoice
    buyer = _customer('Short Rider Org')
    rider = Contact.objects.create(email='short@jpods.test', customer_id=buyer.pk)
    Cash.objects.create(amount=Decimal('1.00'), customer_id=buyer.pk)
    before = Invoice.objects.count()
    result = create_trip_invoice({'contact_id': rider.pk, 'origin_station_id': 'S001',
                                  'destination_station_id': 'S003', 'price': '3.25', 'currency': 'USD'})
    assert result.get('code') == 'insufficient_balance'
    assert 'add 2.25 USD to ride' in result['error']
    assert Invoice.objects.count() == before


def test_ledger_rows_match_the_terms_instalments_open_or_paid():
    """Bill, 2026-09-26: rows per document = instalments of its terms; Σ rows = balance."""
    from apps.accounts.models import Ledger, Term
    from apps.core.services.balance_checker import check_ledger_rows
    Term.objects.create(ida='3Pay30Days', name='3 payments', period_count=3, days_in_period=30,
                        days_due=0, is_active=True)
    buyer = _customer('Instalment Buyer')
    inv = Invoice.objects.create(customer_id=buyer.pk, finance={"sales_tax_rate": 0}, terms='3Pay30Days')
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": 90.00, "precision": 2}, cost={"unit": 0})
    recalculate_totals(inv.pk, 'invoice')
    rows = Ledger.objects.filter(invoice_id=inv.pk, model_name='invoice')
    assert rows.count() == 3, 'one row per instalment'
    _pay(inv, buyer, '30.00')                 # the first instalment paid: its row stays, at 0
    mine = lambda: {f['check'] for f in check_ledger_rows(buyer.pk) if f['record_id'] == inv.pk}
    assert rows.count() == 3 and not mine()

    rows.order_by('-pk').first().delete()      # a lost row
    assert 'ledger.rows' in mine()
