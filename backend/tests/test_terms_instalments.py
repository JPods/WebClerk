"""Complex terms broken into parts — what ledgers are for.

Bill, 2026-09-20: "What is important about ledgers is they support complex terms by
breaking due dates into parts", and "AP and AR need ledgers". Until today no document in
wc_demo used a multi-part term, so this path had never run on either side.
"""
from decimal import Decimal

import pytest

from tests.utils import received_receipt_line
from django.apps import apps as dj_apps

pytestmark = pytest.mark.django_db


def _term(ida='3Pay30Days', period_count=3, days_in_period=30, days_due=90):
    Term = dj_apps.get_model('accounts', 'Term')
    return Term.objects.create(ida=ida, name=ida, period_count=period_count,
                               days_in_period=days_in_period, days_due=days_due,
                               discount_rate=0, days_discount=0, is_active=True)


def _invoice(total, terms_ida=None):
    from apps.orgs.models import Customer
    from apps.transactions.models import Invoice, InvoiceLine
    customer = Customer.objects.create(company='C')
    invoice = Invoice.objects.create(customer_id=customer.pk, terms=terms_ida or '')
    InvoiceLine.objects.create(invoice=invoice, item={'item_id': 1},
                               quantity={'active': 1},
                               price={'unit': total, 'precision': 2})
    invoice.refresh_from_db()
    return invoice


def test_a_three_part_term_makes_three_instalments_with_their_own_due_dates():
    from apps.accounts.services.terms_ledger import apply_terms_for_invoice
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    _term()
    invoice = _invoice(Decimal('300.00'), terms_ida='3Pay30Days')

    apply_terms_for_invoice(invoice, replace=True)

    rows = list(Ledger.objects.filter(parent_id=invoice.pk, model_name='invoice').order_by('dt_due'))
    assert len(rows) == 3
    # The shares are quantized (0.3333 / 0.3333 / 0.3334), so the parts are uneven by a
    # couple of cents and the last carries the remainder. Bill: "the rounding variance of
    # a few cents is understandable by most people." What must hold is that they add up.
    assert [float(r.value_original) for r in rows] == [99.99, 99.99, 100.02]
    assert sum(Decimal(str(r.value_original)) for r in rows) == Decimal('300.00')
    # each part carries its own date — the reason a balance on the document cannot do this
    assert (rows[1].dt_due - rows[0].dt_due).days == 30
    assert (rows[2].dt_due - rows[1].dt_due).days == 30


def test_instalments_add_up_to_the_document_exactly():
    """118.20 across three parts used to make 39.40 + 39.40 + 39.41 = 118.21."""
    from apps.accounts.services.terms_ledger import apply_terms_for_invoice
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    _term()
    invoice = _invoice(Decimal('118.20'), terms_ida='3Pay30Days')

    apply_terms_for_invoice(invoice, replace=True)

    rows = Ledger.objects.filter(parent_id=invoice.pk, model_name='invoice')
    parts = sum(Decimal(str(r.value_original)) for r in rows)
    assert parts == Decimal('118.20')


def test_ap_and_ar_resolve_the_same_term_the_same_way():
    """AP read terms_fk and AR read the terms ida, so one document aged two ways. There
    is no FK now (Bill, 2026-10-22): both read the ida, whatever its case."""
    from apps.orgs.models import Vendor
    from apps.transactions.models import Receipt
    from apps.accounts.services.terms_ledger import resolve_term
    term = _term()
    invoice = _invoice(Decimal('90.00'), terms_ida='3Pay30Days')
    receipt = Receipt.objects.create(vendor_id=Vendor.objects.create(company='V').pk, terms='3pay30days')

    assert resolve_term(invoice).pk == term.pk
    assert resolve_term(receipt).pk == term.pk


def test_a_payable_splits_into_parts_like_a_receivable():
    from apps.orgs.models import Vendor
    from apps.transactions.models import Receipt, ReceiptLine
    from apps.accounts.services.terms_ledger import apply_terms_for_payable
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    _term()
    vendor = Vendor.objects.create(company='V')
    receipt = Receipt.objects.create(vendor_id=vendor.pk, terms='3Pay30Days')
    received_receipt_line(receipt=receipt, quantity={'active': 1},
                               cost={'unit': 300.00, 'precision': 2})
    receipt.refresh_from_db()

    apply_terms_for_payable(receipt, replace=True)

    rows = list(Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt').order_by('dt_due'))
    assert len(rows) == 3
    assert sum(Decimal(str(r.value_original)) for r in rows) == Decimal('300.00')
    assert all(r.source == 'AP' and r.org_id == vendor.pk for r in rows)


# ── terms are text (Bill, 2026-10-22) ────────────────────────────────

def test_the_terms_dropdown_offers_idas():
    """It offered the description as the value, so a pick never resolved to a Term."""
    from apps.core.services.field_behaviors import _get_terms_options
    _term()
    assert {'value': '3Pay30Days', 'label': '3Pay30Days'} in _get_terms_options()


def test_the_save_door_stores_the_terms_own_spelling_and_refuses_an_unknown_one():
    from apps.core.services.door import Actor, Refused
    from apps.core.services.save import save_record
    from apps.orgs.models import Customer
    _term()
    customer = Customer.objects.create(company='C')

    save_record(Actor.system(), {'model_name': 'customer', 'id': customer.pk, 'terms': '3pay30days'})
    customer.refresh_from_db()
    assert customer.terms == '3Pay30Days'

    with pytest.raises(Refused) as refused:
        save_record(Actor.system(), {'model_name': 'customer', 'id': customer.pk, 'terms': 'Net 30'})
    assert refused.value.code == 'invalid_terms'
    assert '3Pay30Days' in refused.value.message          # the coaching names the valid idas

    save_record(Actor.system(), {'model_name': 'customer', 'id': customer.pk, 'terms': ''})
    customer.refresh_from_db()
    assert customer.terms == ''                           # empty: the company default applies
