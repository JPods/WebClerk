"""Regression tests for the Bite 2 payments/GL findings (assessment 2026-09-19).

~/Allie/readmes/assessments/2026-09-19/bite-2-payments-gl/comparison.md lists them.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from apps.transactions.models import Cash, Invoice, InvoiceLine


def _invoice(total_unit=20.00, customer_id=None, rate=0.05):
    inv = Invoice.objects.create(finance={"sales_tax_rate": rate}, customer_id=customer_id)
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": total_unit, "precision": 2}, cost={"unit": 0})
    inv.refresh_from_db()
    return inv


@pytest.mark.django_db
def test_cash_takes_its_type_from_the_sign():
    """#10: a receipt saved without a type is cash_in."""
    c = Cash.objects.create(amount=Decimal("10.00"))
    assert c.type == 'cash_in'
    d = Cash.objects.create(amount=Decimal("-5.00"))
    assert d.type == 'cash_out'


@pytest.mark.django_db
def test_a_cash_discount_reduces_the_invoice_and_posts_to_sales_discounts(chart_of_accounts):
    """#1 and #1b."""
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    from apps.accounts.services.journalize import journalize_invoice
    from apps.accounts.services.chart import role_account
    inv = _invoice(20.00)                                   # 20.00 + 1.00 tax = 21.00
    cash = Cash.objects.create(amount=Decimal("10.00"))
    apply_cash_to_invoice(cash.pk, inv.pk, 10, discount_amt=2, acted_by=1)
    inv.refresh_from_db()
    assert inv.totals["total"] == pytest.approx(19.00)      # 21 − 2, never 23
    result = journalize_invoice(inv.pk)
    assert result.get("created"), result
    disc = [p for p in result["postings"] if p["account"] == role_account('discount_given')]
    assert disc and disc[0]["debit"] == pytest.approx(2.00)


@pytest.mark.django_db
def test_cash_from_one_customer_does_not_pay_anothers_invoice():
    """#3."""
    from apps.orgs.models import Customer
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    a = Customer.objects.create(company='A')
    b = Customer.objects.create(company='B')
    inv = _invoice(20.00, customer_id=b.pk)
    cash = Cash.objects.create(amount=Decimal("10.00"), customer_id=a.pk)
    with pytest.raises(ValueError, match="customers differ"):
        apply_cash_to_invoice(cash.pk, inv.pk, 10)


@pytest.mark.django_db
def test_a_small_balance_dismissal_is_adjusted_not_received_and_posts_to_writeoff(chart_of_accounts):
    """#2 and #7."""
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    from apps.accounts.services.journalize import journalize_cash
    from apps.accounts.services.chart import role_account
    inv = _invoice(20.00)                                   # 21.00
    cash = Cash.objects.create(amount=Decimal("20.50"))
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal("20.50"), dismiss_balance=True, acted_by=1)
    inv.refresh_from_db()
    assert inv.totals["received"] == pytest.approx(20.50)   # money only
    assert inv.totals["adjusted"] == pytest.approx(0.50)
    assert inv.totals["balance"] == pytest.approx(0.00)
    adj = Cash.objects.filter(invoice=inv, method='small_balance').get()
    posted = journalize_cash(adj.pk)
    accounts = {p["account"]: p for p in posted["postings"]}
    assert role_account('small_balance_writeoff') in accounts
    assert role_account('undeposited_funds') not in accounts          # never to the bank


@pytest.mark.django_db
def test_a_reversed_cash_can_be_posted_again(chart_of_accounts):
    """#4."""
    from apps.accounts.services.journalize import journalize_cash
    from apps.accounts.services.ledger_balance import reverse_gl_entries
    cash = Cash.objects.create(amount=Decimal("10.00"))
    assert journalize_cash(cash.pk)["created"] == 2
    assert reverse_gl_entries(cash) == 2
    assert journalize_cash(cash.pk)["created"] == 2
    assert reverse_gl_entries(cash) == 2                    # the second posting reverses too


@pytest.mark.django_db
def test_the_ar_ledger_follows_the_invoice_total(chart_of_accounts):
    """#5: a line edit changes the total; the ledger follows."""
    from django.apps import apps
    Ledger = apps.get_model('accounts', 'Ledger')
    inv = _invoice(20.00, rate=0)
    from apps.accounts.services.ledger_balance import on_invoice_save
    on_invoice_save(inv)
    line = inv.lines.first()
    line.quantity = {"active": 3}
    line.save()
    inv.refresh_from_db()
    ledgers = Ledger.objects.filter(invoice_id=inv.pk, model_name='invoice')
    assert sum(Decimal(str(l.value_original)) for l in ledgers) == Decimal("60.00")


@pytest.mark.django_db
def test_journalize_invoice_and_cash_posts_nothing_when_the_invoice_fails(chart_of_accounts, monkeypatch):
    """#6: no cash posting against an invoice that did not post."""
    from apps.accounts.services import journalize as j
    inv = _invoice(20.00)
    Cash.objects.create(amount=Decimal("10.00"), invoice=inv)
    monkeypatch.setattr(j, 'journalize_invoice', lambda *a, **k: {'created': 0, 'status': 'exception',
                                                                   'error': 'Out of balance: residual=4.000'})
    result = j.journalize_invoice_and_cash_entries(inv.pk)
    assert result["status"] == "exception" and result["cash_entries"] == []


@pytest.mark.django_db
def test_no_adjustment_without_a_user():
    """Bill: writing off anything is a positive action by a user, never automatic."""
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    inv = _invoice(20.00)
    cash = Cash.objects.create(amount=Decimal("20.50"))
    with pytest.raises(ValueError, match="user's decision"):
        apply_cash_to_invoice(cash.pk, inv.pk, Decimal("20.50"), dismiss_balance=True)


@pytest.mark.django_db
def test_the_write_off_records_who_decided(chart_of_accounts):
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    inv = _invoice(20.00)
    cash = Cash.objects.create(amount=Decimal("20.50"))
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal("20.50"), dismiss_balance=True, acted_by=7)
    adj = Cash.objects.get(invoice=inv, method='small_balance')
    assert adj.metadata["decision"]["decided_by_user_id"] == 7
    assert adj.metadata["decision"]["dt_decided"].endswith("Z")


@pytest.mark.django_db
def test_company_policy_limits_a_write_off(chart_of_accounts):
    from apps.core.models import Setting
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    company = Setting.objects.get(purpose='wc:company_profile')
    company.config = {**company.config, 'cash_policy': {'write_off_limit': 0.25}}
    company._setting_create_authorized = True
    company.save()
    inv = _invoice(20.00)                                   # 21.00
    cash = Cash.objects.create(amount=Decimal("20.50"))
    with pytest.raises(ValueError, match="Company policy"):
        apply_cash_to_invoice(cash.pk, inv.pk, Decimal("20.50"), dismiss_balance=True, acted_by=1)


@pytest.mark.django_db
def test_financial_summary_matches_sources_and_echoes(chart_of_accounts):
    """Bill: unapplied cash and its ledger records should match; the summary shows both."""
    from apps.orgs.models import Customer
    from apps.accounts.services.ledger_balance import on_invoice_save, update_org_balances
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    c = Customer.objects.create(company='C')
    inv = _invoice(20.00, customer_id=c.pk)                 # 21.00
    on_invoice_save(inv)
    cash = Cash.objects.create(amount=Decimal("30.00"), customer_id=c.pk)
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal("10.00"))
    c.refresh_from_db()
    update_org_balances(c)
    s = c.financial["summary"]
    assert s["receivable"] == pytest.approx(11.00)
    assert s["receivable_ledger"] == pytest.approx(11.00)
    assert s["unapplied_cash"] == pytest.approx(20.00)
    assert s["net"] == pytest.approx(-9.00)
    assert c.financial["customer"]["balances"]["due"] == pytest.approx(11.00)   # invoices only


@pytest.mark.django_db
def test_customer_sales_by_period_come_from_invoices(chart_of_accounts):
    """Bill: sales month-to-date, year-to-date, last year, lifetime — computed from invoices."""
    import time
    from datetime import datetime, timezone
    from apps.orgs.models import Customer
    from apps.accounts.services.ledger_balance import update_org_balances
    c = Customer.objects.create(company='S')
    now = datetime.now(timezone.utc)
    this_year = _invoice(100.00, customer_id=c.pk, rate=0)
    last_year = _invoice(40.00, customer_id=c.pk, rate=0)
    Invoice.objects.filter(pk=last_year.pk).update(
        dt_approved=int(datetime(now.year - 1, 6, 1, tzinfo=timezone.utc).timestamp() * 1000))
    update_org_balances(c)
    c.refresh_from_db()
    sales = c.financial["customer"]["sales"]
    assert sales["ytd"] == pytest.approx(100.00)
    assert sales["mtd"] == pytest.approx(100.00)
    assert sales["last_year"] == pytest.approx(40.00)
    assert sales["lifetime"] == pytest.approx(140.00)


@pytest.mark.django_db
def test_demo_rates_4_percent_shipping_and_8_percent_tax_reach_the_journal(chart_of_accounts):
    """Bill: ship_via test_4% and tax test_8% drive shipping and tax into totals and journal entries."""
    from django.core.management import call_command
    from apps.accounts.services.journalize import journalize_invoice
    from apps.accounts.services.chart import role_account
    from apps.accounts.models.tax_jurisdiction import TaxJurisdiction
    call_command('seed_shipping_service', verbosity=0)
    call_command('seed_tax_jurisdictions', verbosity=0)
    tj = TaxJurisdiction.objects.get(tax_jurisdiction='test_8%')
    inv = Invoice.objects.create(ship_via='test_4%',
                                 finance={"sales_tax_rate": tj.tax_rate_sales, "sales_tax_name": tj.tax_name})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 5},
                               price={"unit": 20.00, "precision": 2}, cost={"unit": 0})
    inv.refresh_from_db()
    assert inv.totals["amount"] == pytest.approx(100.00)
    assert inv.totals["shipping"] == pytest.approx(4.00)          # 4% of goods
    assert inv.totals["tax"] == pytest.approx(8.00)               # 8% = 2 × shipping
    assert inv.totals["total"] == pytest.approx(112.00)
    line = inv.lines.first()
    assert line.totals["shipping"] == pytest.approx(4.00) and line.totals["tax"] == pytest.approx(8.00)
    result = journalize_invoice(inv.pk)
    by_account = {p["account"]: p for p in result["postings"]}
    assert by_account[role_account('shipping_revenue')]["credit"] == pytest.approx(4.00)
    assert by_account[role_account('sales_tax_payable')]["credit"] == pytest.approx(8.00)
    assert by_account[role_account('accounts_receivable')]["debit"] == pytest.approx(112.00)


@pytest.mark.django_db
def test_org_metrics_from_source_records(chart_of_accounts):
    """Bill: count and size by period, the size vector, rhythm/quiet, channel × fulfillment, visits."""
    from datetime import datetime, timezone, timedelta
    from django.core.management import call_command
    from apps.orgs.models import Customer
    from apps.orgs.services.org_metrics import compute_org_metrics
    from apps.communications.models import Touch
    call_command('seed_shipping_service', verbosity=0)
    c = Customer.objects.create(company='M')
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    def sale(amount, days_ago, source='', ship_via=''):
        inv = _invoice(amount, customer_id=c.pk, rate=0)
        Invoice.objects.filter(pk=inv.pk).update(
            dt_approved=int((now - timedelta(days=days_ago)).timestamp() * 1000),
            source_name=source, ship_via=ship_via)
    sale(40, 130, 'direct', 'UPS')
    sale(300, 100, 'web', 'Will Call')
    sale(60, 70, 'web', 'pickup')
    sale(1200, 40)
    Touch.objects.create(org_id=c.pk, channel='visit', direction='in',
                         dt_created=int((now - timedelta(days=5)).timestamp() * 1000))
    m = compute_org_metrics(c, now=now)
    assert m["periods"]["ytd"]["count"] == 4 and m["periods"]["ytd"]["amount"] == 1600.0
    assert m["periods"]["ytd"]["average"] == 400.0
    y = m["years"][-1]
    assert y["size_bands"]["0-50"]["count"] == 1 and y["size_bands"]["1000-5000"]["count"] == 1
    assert y["fulfillment"] == {"shipped": 1, "pickup": 2, "unknown": 1}   # from the registry; nothing guessed
    assert y["online_pickup"] == 2 and y["online_pickup_share"] == 50.0
    assert y["visits_in"] == 1
    assert m["rhythm"]["usual_interval_days"] == 30 and m["rhythm"]["days_since_last"] == 40
    assert m["rhythm"]["quiet"] is False                    # 40 < 1.5 × 30 = 45


@pytest.mark.django_db
def test_tax_on_shipping_and_on_costs_are_off_until_the_company_turns_them_on(chart_of_accounts):
    """Bill: zero tax on shipping and no tax on costs for now; a company switch for each."""
    from django.core.management import call_command
    from apps.core.models import Setting
    from apps.transactions.models import Purchase, PurchaseLine
    call_command('seed_shipping_service', verbosity=0)
    inv = Invoice.objects.create(ship_via='test_4%',
                                 finance={"sales_tax_rate": 0.08, "tax_on_shipping_rate": 0.08})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 5},
                               price={"unit": 20.00, "precision": 2}, cost={"unit": 0})
    inv.refresh_from_db()
    assert inv.totals["tax"] == pytest.approx(8.00)                # shipping not taxed
    po = Purchase.objects.create(finance={"sales_tax_rate": 0.08})
    PurchaseLine.objects.create(purchase=po, quantity={"active": 2}, cost={"unit": 50.00})
    po.refresh_from_db()
    assert po.totals["tax"] == 0                                   # costs not taxed
    company = Setting.objects.get(purpose='wc:company_profile')
    company.config = {**company.config, 'tax_policy': {'tax_on_shipping': True}}
    company.save()
    inv.lines.first().save()
    inv.refresh_from_db()
    assert inv.totals["tax"] == pytest.approx(8.00 + 0.32)         # 8% of the 4.00 shipping


@pytest.mark.django_db
def test_flight_simulator_reads_its_rates_from_the_records(chart_of_accounts):
    """Bill: no hard-coded rates in the flight simulator — apply a tax jurisdiction and a carrier."""
    from django.core.management import call_command
    from apps.products.services.inventory.inventory_flight_sim import (
        get_cash_flight_scenario, get_flight_scenario, sim_header_defaults)
    call_command('seed_shipping_service', verbosity=0)
    call_command('seed_tax_jurisdictions', verbosity=0)
    scenario = get_flight_scenario()
    cfg = scenario["config"]
    assert cfg["tax_jurisdiction"] == 'test_8%' and cfg["tax_rate"] == 0.08
    assert cfg["ship_via"] == 'test_4%' and cfg["shipping_rate"] == 0.04
    invoice_step = next(s for s in scenario["steps"] if s["step"] == 4)
    amounts = {p["purpose"].split()[0]: p["amount"] for p in invoice_step["expected_gl"]}
    assert amounts["Accounts"] == pytest.approx(44.80)        # 40 goods + 1.60 shipping + 3.20 tax
    assert amounts["Shipping"] == pytest.approx(1.60)
    assert amounts["Sales"] == pytest.approx(3.20)            # 8% = 2 × 4%
    assert scenario["invoice_summary"]["invoice_total"] == pytest.approx(44.80)
    settle = scenario["invoice_summary"]["settlement"]
    assert sum(x["amount"] for x in settle) == pytest.approx(44.80)   # cash + discount + write-off
    cash = get_cash_flight_scenario()["steps"][1]["expected_invoice"]
    assert cash["total"] == pytest.approx(67.20)             # 60 + 2.40 + 4.80
    # the defaults the console puts on each record it creates
    d = sim_header_defaults()
    assert d["ship_via"] == 'test_4%' and d["finance"]["sales_tax_rate"] == 0.08


@pytest.mark.django_db
def test_a_payable_creates_a_ledger_with_a_due_date(chart_of_accounts):
    """Bill 2026-09-19: "We should work AP just as we work AR. Each payable creates a
    ledger with a due date." """
    from django.apps import apps
    from apps.orgs.models import Vendor
    from apps.transactions.models import Purchase, Receipt
    from apps.accounts.services.ledger_balance import update_org_balances
    Ledger = apps.get_model('accounts', 'Ledger')

    vendor = Vendor.objects.create(company='V')
    po = Purchase.objects.create(vendor_id=vendor.pk)
    from apps.transactions.models import ReceiptLine
    receipt = Receipt.objects.create(parent_id=po.pk, parent_model='purchase',
                                     vendor_invoice_amount=Decimal('300.00'))
    assert receipt.vendor_id == vendor.pk          # inherited from the purchase it receives against
    assert not Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt').exists()   # no lines: a draft, no payable
    ReceiptLine.objects.create(receipt=receipt, quantity={'active': 3}, cost={'unit': 100.00, 'precision': 2})
    receipt.refresh_from_db()
    assert receipt.totals['total'] == pytest.approx(300.00)              # the money comes from the lines
    assert receipt.metadata['vendor_claim']['in_step'] is True           # and matches the vendor's claim

    rows = Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt')
    assert rows.count() >= 1
    assert sum(Decimal(str(r.value_available)) for r in rows) == Decimal('300.00')
    assert all(r.dt_due is not None for r in rows)          # every payable row has a due date
    assert all(r.source == 'AP' and r.org_id == vendor.pk for r in rows)

    # Paying it moves the water level, exactly as on the AR side
    from apps.transactions.services.pricing.totals_compute import update_paid
    update_paid(receipt, Decimal('120.00'))
    from apps.accounts.services.terms_ledger import allocate_paid
    receipt.refresh_from_db()
    allocate_paid(receipt)
    rows = Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt')
    assert sum(Decimal(str(r.value_available)) for r in rows) == Decimal('180.00')

    update_org_balances(vendor)
    vendor.refresh_from_db()
    s = vendor.financial['summary']
    assert s['payable'] == pytest.approx(180.00)
    assert s['payable_ledger'] == pytest.approx(180.00)
    assert s['in_step'] is True
    assert vendor.financial['vendor']['balances']['due'] == pytest.approx(180.00)


@pytest.mark.django_db
def test_a_cash_application_records_itself_on_the_invoice():
    """The ledger says how deep the water is; the event says how it got there."""
    from apps.orgs.models import Customer
    from apps.transactions.models import Cash, Invoice, InvoiceLine
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice

    customer = Customer.objects.create(company='C')
    invoice = Invoice.objects.create(customer_id=customer.pk)
    InvoiceLine.objects.create(invoice=invoice, item={'item_id': 1}, quantity={'active': 1},
                               price={'unit': 100.00, 'precision': 2})
    invoice.refresh_from_db()
    cash = Cash.objects.create(customer_id=customer.pk, amount=Decimal('40.00'),
                               available=Decimal('40.00'), status='completed')

    out = apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('40.00'), reason='check 1021')

    invoice.refresh_from_db()
    cash.refresh_from_db()
    assert float(invoice.totals['received']) == 40.0
    event = invoice.events[0]
    assert event['kind'] == 'cash_application'
    assert event['amount'] == 40.0
    assert event['cash_id'] == cash.pk
    assert event['reason'] == 'check 1021'
    assert float(cash.available) == 0.0

    # a retry is a quiet no-op: applied once, recorded once, and no exception
    from apps.core.models.pending import Pending
    from apps.transactions.services.cash.cash_pending import apply_cash_pending
    pending = Pending.objects.get(pk=out['pending_id'])
    assert apply_cash_pending(pending) is True
    invoice.refresh_from_db()
    cash.refresh_from_db()
    assert len(invoice.events) == 1
    assert float(invoice.totals['received']) == 40.0
    assert float(cash.available) == 0.0


@pytest.mark.django_db
def test_ap_paid_is_derived_so_a_double_apply_cannot_double_count():
    from apps.orgs.models import Vendor
    from apps.transactions.models import Cash, Receipt, ReceiptLine
    from apps.core.models.pending import Pending
    from apps.transactions.services.cash.cash_pending_receipt import (
        apply_cash_to_receipt, apply_receipt_cash_pending)

    vendor = Vendor.objects.create(company='V')
    receipt = Receipt.objects.create(vendor_id=vendor.pk)
    ReceiptLine.objects.create(receipt=receipt, quantity={'active': 1},
                               cost={'unit': 100.00, 'precision': 2})
    receipt.refresh_from_db()
    cash = Cash.objects.create(vendor_id=vendor.pk, amount=Decimal('-60.00'),
                               available=Decimal('-60.00'), status='completed')

    out = apply_cash_to_receipt(cash.pk, receipt.pk, Decimal('60.00'))

    receipt.refresh_from_db()
    assert float(receipt.totals['paid']) == 60.0
    assert float(receipt.totals['balance']) == 40.0

    pending = Pending.objects.get(pk=out['pending_id'])
    apply_receipt_cash_pending(pending)          # apply it a second time
    receipt.refresh_from_db()
    assert float(receipt.totals['paid']) == 60.0   # derived, so it cannot double-count
    assert len(receipt.events) == 1
