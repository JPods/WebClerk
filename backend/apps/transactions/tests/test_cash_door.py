"""The cash door: a change to an application is a new signed Pending, never an edit.

Plan: readmes/assessments/2026-09-22-cash-door-plan.md. Bill, 2026-09-22: deleting a
transaction issues the Pendings that account for its cash, and then it is gone.
"""
from decimal import Decimal

import pytest
from django.db import transaction

from apps.core.models.pending import Pending
from apps.transactions.models import Cash, Invoice, Receipt
from apps.transactions.services.cash import cash_door
from apps.transactions.services.cash.cash_pending import (
    CASH_PURPOSE, apply_cash_to_invoice, refresh_cash_available, unapply_cash_application)
from apps.transactions.services.cash.cash_pending_receipt import (
    RECEIPT_CASH_PURPOSE, apply_cash_to_receipt)

pytestmark = pytest.mark.django_db


# ── fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def buyer(db):
    """The customer whose invoices these are. A cash record's party must be a real org."""
    from apps.orgs.models import OrgBase
    return OrgBase.objects.create(company='Cash Door Customer', org_type='customer',
                                  is_active=True)


@pytest.fixture
def seller(db):
    """The vendor whose payables these are."""
    from apps.orgs.models import OrgBase
    return OrgBase.objects.create(company='Cash Door Vendor', org_type='vendor',
                                  is_active=True)


def _invoice(customer_id, total='100.00'):
    return Invoice.objects.create(
        customer_id=customer_id, status='open',
        totals={'total': float(Decimal(total)), 'received': 0.0,
                'balance': float(Decimal(total))})


def _receipt(vendor_id, total='80.00'):
    return Receipt.objects.create(
        vendor_id=vendor_id, status='open',
        totals={'total': float(Decimal(total)), 'paid': 0.0,
                'balance': float(Decimal(total))})


def _cash(amount='100.00', customer_id=None, vendor_id=None):
    return Cash.objects.create(
        amount=Decimal(amount), available=Decimal(amount), status='completed',
        method='check', customer_id=customer_id, vendor_id=vendor_id)


def _applications(**match):
    return Pending.objects.filter(purpose__in=cash_door.CASH_PURPOSES, **match)


# ── reversal, not an edit ─────────────────────────────────────────────

def test_unapply_writes_a_reversal_and_leaves_the_original_alone(buyer, seller):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    result = apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('60.00'))
    application = Pending.objects.get(pk=result['pending_id'])
    assert application.changes['state'] == 'applied'

    unapply_cash_application(application.pk, reason='customer disputed')

    application.refresh_from_db()
    assert application.changes['state'] == 'applied', "the original application is never edited"
    reversal = _applications(changes__reverses=application.pk).get()
    assert Decimal(str(reversal.changes['amount'])) == Decimal('-60.00')
    assert reversal.changes['state'] == 'applied'
    assert reversal.changes['reason'] == 'customer disputed'

    invoice.refresh_from_db()
    cash.refresh_from_db()
    assert Decimal(str(invoice.totals['received'])) == Decimal('0.00')
    assert cash.available == Decimal('100.00'), "the money is available again"
    assert cash_door.live(application) == Decimal('0.00')


def test_a_second_unapply_is_refused(buyer, seller):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    application = Pending.objects.get(
        pk=apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('25.00'))['pending_id'])
    unapply_cash_application(application.pk, reason='first')
    with pytest.raises(Exception, match='(?i)reversed|nothing'):
        unapply_cash_application(application.pk, reason='second')


def test_reapply_after_unapply(buyer, seller):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    first = apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('100.00'))
    unapply_cash_application(first['pending_id'], reason='wrong invoice')
    apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('40.00'))
    invoice.refresh_from_db(); cash.refresh_from_db()
    assert Decimal(str(invoice.totals['received'])) == Decimal('40.00')
    assert cash.available == Decimal('60.00')


def test_ap_unapply_goes_through_the_same_door(buyer, seller):
    receipt = _receipt(seller.pk)
    cash = _cash(amount='-80.00', vendor_id=seller.pk)
    application = Pending.objects.get(
        pk=apply_cash_to_receipt(cash.pk, receipt.pk, Decimal('80.00'))['pending_id'])
    receipt.refresh_from_db()
    assert receipt.status == 'paid'

    unapply_cash_application(application.pk, reason='paid the wrong bill')

    reversal = _applications(changes__reverses=application.pk).get()
    assert reversal.purpose == RECEIPT_CASH_PURPOSE
    receipt.refresh_from_db()
    assert Decimal(str(receipt.totals['paid'])) == Decimal('0.00')
    assert receipt.status == 'open', "a payable that is no longer paid is open again"


# ── a delete accounts for its cash ────────────────────────────────────

def test_deleting_a_cash_reverses_every_application_it_made(buyer, seller):
    first, second, receipt = _invoice(buyer.pk, total='50.00'), _invoice(buyer.pk, total='30.00'), _receipt(seller.pk, total='20.00')
    cash = _cash(amount='100.00', customer_id=buyer.pk)
    cash.vendor_id = seller.pk
    cash.save(update_fields=['vendor_id'])
    apply_cash_to_invoice(cash.pk, first.pk, Decimal('50.00'))
    apply_cash_to_invoice(cash.pk, second.pk, Decimal('30.00'))
    apply_cash_to_receipt(cash.pk, receipt.pk, Decimal('20.00'))

    cash.delete()

    assert _applications(changes__reverses__isnull=False).count() == 3
    for document, field in ((first, 'received'), (second, 'received'), (receipt, 'paid')):
        document.refresh_from_db()
        assert Decimal(str(document.totals[field])) == Decimal('0.00'), document
    assert not Cash.objects.filter(pk=cash.pk).exists()


def test_deleting_an_invoice_returns_the_money_to_the_cash(buyer, seller):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('75.00'))
    cash.refresh_from_db()
    assert cash.available == Decimal('25.00')

    invoice.delete()

    cash.refresh_from_db()
    assert cash.available == Decimal('100.00'), "a deleted invoice gives the money back"
    assert _applications(changes__reverses__isnull=False).count() == 1


def test_deleting_an_invoice_does_not_delete_the_cash_that_paid_it(buyer, seller):
    """The FK was CASCADE: deleting an invoice deleted the customer's money (Fable)."""
    invoice = _invoice(buyer.pk)
    cash = _cash(customer_id=buyer.pk)
    cash.invoice = invoice
    cash.save(update_fields=['invoice'])
    apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('100.00'))

    invoice.delete()

    cash.refresh_from_db()
    assert cash.pk and cash.invoice_id is None
    assert cash.available == Decimal('100.00')


def test_queued_application_is_closed_not_reversed_when_its_invoice_goes(buyer, seller):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    queued = Pending.objects.create(
        model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
        name='queued', dt_processed=0,
        changes={'cash_id': cash.pk, 'invoice_id': invoice.pk, 'amount': 10.0,
                 'state': 'pending', 'dt_applied': None})
    Pending.objects.filter(pk=queued.pk).update(dt_processed=0, changes={
        'cash_id': cash.pk, 'invoice_id': invoice.pk, 'amount': 10.0, 'state': 'pending'})

    invoice.delete()

    queued.refresh_from_db()
    assert queued.changes['state'] == 'canceled'
    assert queued.dt_processed > 0
    assert not _applications(changes__reverses=queued.pk).exists(), "nothing applied, nothing to reverse"


# ── a cash Pending is permanent and frozen ────────────────────────────

def test_a_cash_application_cannot_be_deleted(buyer, seller):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    application = Pending.objects.get(
        pk=apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('10.00'))['pending_id'])
    # The refusal is raised inside the delete's own transaction, so that transaction is
    # aborted: nothing is deleted, which is the point.
    with pytest.raises(cash_door.CashDoorError, match='(?i)permanent'):
        with transaction.atomic():
            application.delete()
    assert Pending.objects.filter(pk=application.pk).exists()


def test_an_applied_application_cannot_be_edited(buyer, seller):
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    application = Pending.objects.get(
        pk=apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('10.00'))['pending_id'])
    application.changes = dict(application.changes, amount=999.0)
    with pytest.raises(cash_door.CashDoorError, match='(?i)already applied'):
        application.save(update_fields=['changes'])


def test_the_applier_may_still_process_a_queued_application(buyer, seller):
    """The freeze compares the stored row, so the applier's own write still works.

    A queued application is written straight to the table (as celery finds it) and then
    applied: the applier writes changes and dt_processed in one save, which an
    instance-level freeze would have refused.
    """
    invoice, cash = _invoice(buyer.pk), _cash(customer_id=buyer.pk)
    queued = Pending(model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
                     name='queued', dt_processed=0,
                     changes={'cash_id': cash.pk, 'invoice_id': invoice.pk,
                              'amount': 10.0, 'state': 'pending', 'dt_applied': None})
    Pending.objects.bulk_create([queued])
    queued = Pending.objects.get(name='queued')
    assert not queued.is_processed()

    assert queued.try_apply() is True

    queued.refresh_from_db()
    assert queued.changes['state'] == 'applied'
    invoice.refresh_from_db()
    assert Decimal(str(invoice.totals['received'])) == Decimal('10.00')


# ── ledgers do not outlive their record ───────────────────────────────

def test_deleting_a_cash_takes_its_ledger_rows_with_it(buyer, seller):
    from apps.accounts.models import Ledger
    cash = _cash(customer_id=buyer.pk)
    Ledger.objects.create(model_name='cash', parent_id=cash.pk, org_id=buyer.pk,
                          value_original=Decimal('100.00'), value_available=Decimal('100.00'))
    cash.delete()
    assert not Ledger.objects.filter(model_name='cash', parent_id=cash.pk).exists()


# ── one available, both sides ─────────────────────────────────────────

def test_available_counts_both_sides_of_the_house(buyer, seller):
    """One refresh_cash_available, and both names give the same answer.

    There were two functions with different formulas: the AR one ignored AP applications,
    so a payment that had already paid a vendor still reported the money as available.
    Both reviewers found it independently in the recheck-3 audit.
    """
    from apps.transactions.services.cash.cash_pending_receipt import (
        refresh_cash_available as ap_name)

    receipt = _receipt(seller.pk, total='30.00')
    cash = _cash(amount='-80.00', vendor_id=seller.pk)
    apply_cash_to_receipt(cash.pk, receipt.pk, Decimal('30.00'))
    cash.refresh_from_db()

    # -80.00 paid out, 30.00 of it spent on a payable: 50.00 left to give.
    assert refresh_cash_available(cash) == Decimal('-50.00')
    assert ap_name(cash) == refresh_cash_available(cash), "one function, two names"
