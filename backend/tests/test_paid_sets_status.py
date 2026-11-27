"""Paid sets the status; the person may override it (Bill, 2026-11-27).

"If we have paid an invoice, we should set its status to 'paid', but in company data, they should be
able to set the status to whatever makes sense to them." One rule for invoice and receipt
(totals_compute.settle_paid_status): it moves only when the figure crosses paid, and only a status
the system set. The partial state is a figure (totals.cash_state); the system never writes
partially_paid or open. No prompt, no message.
"""
from decimal import Decimal

import pytest
from django.utils.crypto import get_random_string

from apps.transactions.models import Cash, Invoice
from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice, unapply_cash_application

pytestmark = pytest.mark.django_db


@pytest.fixture
def buyer(db):
    from apps.orgs.models import OrgBase
    return OrgBase.objects.create(company='Paid Status Customer', org_type='customer', is_active=True)


def _invoice(customer_id, status='released', total='100.00'):
    return Invoice.objects.create(customer_id=customer_id, status=status,
                                  totals={'total': float(Decimal(total)), 'received': 0.0,
                                          'balance': float(Decimal(total))})


def _cash(customer_id, amount='100.00'):
    return Cash.objects.create(amount=Decimal(amount), available=Decimal(amount), status='complete',
                               method='check', customer_id=customer_id)


def _status(doc):
    doc.refresh_from_db()
    return doc.status, doc.totals.get('cash_state')


def test_paid_in_full_sets_paid_and_a_reversal_returns_it_to_released(buyer):
    invoice = _invoice(buyer.pk)
    part = apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('40.00'))
    assert _status(invoice) == ('released', 'partial')          # partial is a figure, never a status
    rest = apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('60.00'))
    assert _status(invoice) == ('paid', 'paid')
    unapply_cash_application(rest['pending_id'], reason='bounced')
    assert _status(invoice) == ('released', 'partial')
    unapply_cash_application(part['pending_id'], reason='bounced')
    assert _status(invoice) == ('released', 'open')


@pytest.mark.parametrize('start', ['', 'open'])
def test_a_status_the_system_set_becomes_paid(buyer, start):
    invoice = _invoice(buyer.pk, status=start)
    apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('100.00'))
    assert _status(invoice) == ('paid', 'paid')


@pytest.mark.parametrize('theirs', ['planned', 'approved', 'on_hold', 'complete', 'partially_paid', 'sent'])
def test_a_status_the_person_set_stays_when_paid_and_when_reversed(buyer, theirs):
    invoice = _invoice(buyer.pk, status=theirs)
    paid = apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('100.00'))
    assert _status(invoice) == (theirs, 'paid')
    unapply_cash_application(paid['pending_id'], reason='bounced')
    assert _status(invoice) == (theirs, 'open')


def test_a_paid_the_person_set_on_a_partial_invoice_stays_as_more_cash_comes(buyer):
    invoice = _invoice(buyer.pk)
    apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('20.00'))
    Invoice.objects.filter(pk=invoice.pk).update(status='paid')    # the person's word
    apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('20.00'))
    assert _status(invoice) == ('paid', 'partial')


def test_a_journalized_invoice_is_set_paid_and_the_person_may_still_set_its_status(buyer, django_user_model):
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    invoice = _invoice(buyer.pk)
    Invoice.objects.filter(pk=invoice.pk).update(dt_journaled=1795000000000)
    apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('100.00'))
    assert _status(invoice) == ('paid', 'paid')
    person = django_user_model.objects.create_superuser(
        email='paid-status@example.com', password=get_random_string(20), name_first='P', name_last='S')
    save_record(Actor(user=person), {'id': invoice.pk, 'version': invoice.version, 'status': 'complete'},
                model_key='invoice')
    assert _status(invoice) == ('complete', 'paid')


# ── the one-off: wc_demo's statuses from their facts (settle_document_statuses) ──

def test_the_one_off_sets_statuses_from_facts_and_only_when_applied(buyer):
    from io import StringIO
    from django.core.management import call_command
    from apps.transactions.models import InvoiceLine
    paid = _invoice(buyer.pk, status='planned')
    says_paid = _invoice(buyer.pk, status='paid')
    empty = _invoice(buyer.pk, status='pending', total='0.00')
    canceled = _invoice(buyer.pk, status='canceled')
    no_terms = _invoice(buyer.pk, status='planned')
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    Invoice.objects.filter(pk__in=[paid.pk, says_paid.pk, canceled.pk]).update(terms='N30')
    for doc in (paid, says_paid, canceled, no_terms):       # a line re-runs the totals: the figures go after
        InvoiceLine.objects.create(invoice=doc, item={'description': 'x'}, price={'unit': 100.0},
                                   quantity={'active': 1})
    for doc, received in ((paid, 100.0), (says_paid, 40.0)):
        Invoice.objects.filter(pk=doc.pk).update(totals={'total': 100.0, 'received': received,
                                                         'balance': 100.0 - received})
    out = StringIO()
    call_command('settle_document_statuses', stdout=out)
    listed = out.getvalue()
    assert f"(#{paid.pk}): 'planned' -> 'paid'" in listed
    assert f"(#{says_paid.pk}): 'paid' -> 'released'" in listed
    assert f'#{empty.pk})' not in listed and f'#{canceled.pk})' not in listed
    assert f"(#{no_terms.pk}): left 'planned', cannot release: lacks terms" in listed
    assert Invoice.objects.get(pk=paid.pk).status == 'planned'          # a dry run changes nothing

    call_command('settle_document_statuses', '--apply', stdout=StringIO())
    assert [Invoice.objects.get(pk=d.pk).status for d in (paid, says_paid, empty, canceled, no_terms)] == \
        ['paid', 'released', 'pending', 'canceled', 'planned']


# ── one rule wherever the figure is recomputed; the system's moves are quiet (2026-11-27) ──

def _lined_invoice(buyer, status='released', unit=100.0):
    from apps.transactions.models import InvoiceLine
    invoice = _invoice(buyer.pk, status=status)
    line = InvoiceLine.objects.create(invoice=invoice, item={'description': 'x'}, price={'unit': unit},
                                      quantity={'active': 1, 'staged': 1})
    invoice.refresh_from_db()
    return invoice, line


def test_a_line_edit_that_leaves_a_paid_invoice_owing_returns_it_to_released(buyer):
    invoice, line = _lined_invoice(buyer)
    total = Decimal(str(invoice.totals['total']))
    apply_cash_to_invoice(_cash(buyer.pk, str(total)).pk, invoice.pk, total)
    assert _status(invoice) == ('paid', 'paid')
    line.quantity = {**line.quantity, 'active': 2}
    line.save()
    assert _status(invoice) == ('released', 'partial')


def test_a_line_edit_that_settles_a_released_invoice_sets_it_paid(buyer):
    invoice, line = _lined_invoice(buyer)
    line.quantity = {**line.quantity, 'active': 2}
    line.save()
    invoice.refresh_from_db()
    half = Decimal(str(invoice.totals['total'])) / 2
    apply_cash_to_invoice(_cash(buyer.pk, str(half)).pk, invoice.pk, half)
    assert _status(invoice)[0] == 'released'
    line.quantity = {**line.quantity, 'active': 1}
    line.save()
    assert _status(invoice) == ('paid', 'paid')


def test_the_systems_status_moves_send_no_invoice_sent_email(buyer, monkeypatch, django_capture_on_commit_callbacks):
    from apps.transactions.services.notify_email import TransactionEmailService
    sent = []
    monkeypatch.setattr(TransactionEmailService, 'send_invoice_sent_notification',
                        classmethod(lambda cls, invoice: sent.append(invoice.pk) or True))
    invoice = _invoice(buyer.pk)
    with django_capture_on_commit_callbacks(execute=True):
        paid = apply_cash_to_invoice(_cash(buyer.pk).pk, invoice.pk, Decimal('100.00'))
        unapply_cash_application(paid['pending_id'], reason='bounced')     # paid -> released
    assert _status(invoice)[0] == 'released' and sent == []


def test_a_receipt_keeps_its_paid_figure_through_a_recompute():
    from apps.orgs.models import Vendor
    from apps.transactions.models import Receipt, ReceiptLine
    from apps.transactions.services.pricing.totals_compute import recalculate_totals
    receipt = Receipt.objects.create(status='released', vendor_id=Vendor.objects.create(company='V').pk)
    ReceiptLine.objects.create(receipt=receipt, item={'description': 'x'}, quantity={'active': 0, 'staged': 1},
                               cost={'unit': 10.0})
    recalculate_totals(receipt.pk, 'receipt')
    receipt.refresh_from_db()
    assert receipt.totals['cash_state'] in ('open', 'paid')       # never '' after a recompute
