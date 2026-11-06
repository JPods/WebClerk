"""An adversarial read of applying and un-applying cash for wrong totals (plan 102, the lead's
item 4b, 2026-11-06). Each test states an invariant the books must keep: what a cash has
available is its amount less what applied and refunded; an invoice's received is what applied
to it, its adjusted what its adjustment Cash settled; apply then unapply leaves both exactly
where they were, journalized or not; nothing applies past the document or the cash."""
from decimal import Decimal

import pytest

from apps.core.models.pending import Pending
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Invoice
from apps.transactions.services.cash.cash_pending import (apply_cash_to_invoice, refresh_cash_available,
                                                          unapply_cash_application)

pytestmark = pytest.mark.django_db
JOURNALED = 1793800000000


def _buyer():
    return OrgBase.objects.create(company='Invariant Buyer', org_type='customer', is_active=True)


def _invoice(buyer, total):
    return Invoice.objects.create(customer_id=buyer.pk, status='open',
                                  totals={'total': float(total), 'received': 0.0, 'balance': float(total)})


def _cash(buyer, amount, method='check', **kw):
    return Cash.objects.create(amount=Decimal(str(amount)), available=Decimal(str(amount)), status='complete',
                               method=method, customer_id=buyer.pk, **kw)


def _received(invoice):
    invoice.refresh_from_db()
    t = invoice.totals or {}
    return Decimal(str(t.get('received') or 0)), Decimal(str(t.get('adjusted') or 0)), t.get('cash_state')


def test_one_cash_over_two_invoices_then_one_unapplied(django_user_model):
    buyer = _buyer()
    a, b = _invoice(buyer, 60), _invoice(buyer, 100)
    cash = _cash(buyer, 100)
    first = apply_cash_to_invoice(cash.pk, a.pk, Decimal('60'))
    apply_cash_to_invoice(cash.pk, b.pk, Decimal('40'))
    assert refresh_cash_available(cash) == Decimal('0.00')
    assert _received(a) == (Decimal('60.00'), Decimal('0.00'), 'paid')
    assert _received(b) == (Decimal('40.00'), Decimal('0.00'), 'partial')
    unapply_cash_application(first['pending_id'], reason='wrong invoice')
    assert refresh_cash_available(cash) == Decimal('60.00')
    assert _received(a) == (Decimal('0.00'), Decimal('0.00'), 'open')
    assert _received(b) == (Decimal('40.00'), Decimal('0.00'), 'partial')


def test_nothing_applies_past_the_document_or_the_cash():
    buyer = _buyer()
    inv = _invoice(buyer, 100)
    cash = _cash(buyer, 80)
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal('60'))
    with pytest.raises(ValueError):
        apply_cash_to_invoice(cash.pk, inv.pk, Decimal('30'))      # the cash has 20 left
    other = _cash(buyer, 100)
    with pytest.raises(ValueError):
        apply_cash_to_invoice(other.pk, inv.pk, Decimal('50'))     # the invoice has 40 open
    assert refresh_cash_available(cash) == Decimal('20.00') and refresh_cash_available(other) == Decimal('100.00')
    assert _received(inv) == (Decimal('60.00'), Decimal('0.00'), 'partial')


def test_a_discount_settles_the_invoice_as_adjusted_not_received(django_user_model):
    """The 2% is its own Cash (method discount), applied like money but counted as adjusted
    (Bill, 2026-11-02): received stays what the bank saw."""
    who = django_user_model.objects.create_superuser(email='disc@example.com', password=None,
                                                     name_first='Di', name_last='Sc', username='')
    buyer = _buyer()
    inv = _invoice(buyer, 100)
    money, discount = _cash(buyer, 98), _cash(buyer, 2, method='discount')
    apply_cash_to_invoice(money.pk, inv.pk, Decimal('98'))
    apply_cash_to_invoice(discount.pk, inv.pk, Decimal('2'), acted_by=who.pk)
    assert _received(inv) == (Decimal('98.00'), Decimal('2.00'), 'paid')
    with pytest.raises(ValueError):
        unapply_cash_application(Pending.objects.get(changes__cash_id=discount.pk).pk)   # undone by deleting the discount cash
    paid = Pending.objects.get(changes__cash_id=money.pk)
    unapply_cash_application(paid.pk, reason='bounced')
    assert _received(inv) == (Decimal('0.00'), Decimal('2.00'), 'partial')
    assert refresh_cash_available(money) == Decimal('98.00')


def test_apply_and_unapply_under_the_journalized_lock_leave_the_journal_alone():
    buyer = _buyer()
    inv = _invoice(buyer, 100)
    cash = _cash(buyer, 100, dt_journaled=JOURNALED)
    Invoice.objects.filter(pk=inv.pk).update(dt_journaled=JOURNALED)
    first = apply_cash_to_invoice(cash.pk, inv.pk, Decimal('70'))
    assert refresh_cash_available(cash) == Decimal('30.00') and _received(inv)[0] == Decimal('70.00')
    unapply_cash_application(first['pending_id'], reason='re-apply')
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal('100'))
    cash.refresh_from_db(); inv.refresh_from_db()
    assert cash.dt_journaled == JOURNALED and inv.dt_journaled == JOURNALED
    assert cash.amount == Decimal('100.00') and (inv.totals or {}).get('total') == 100.0
    assert refresh_cash_available(cash) == Decimal('0.00') and _received(inv) == (Decimal('100.00'), Decimal('0.00'), 'paid')


def test_available_is_recomputed_from_the_applications_when_the_row_drifted():
    buyer = _buyer()
    inv = _invoice(buyer, 100)
    cash = _cash(buyer, 100)
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal('40'))
    Cash.objects.filter(pk=cash.pk).update(available=Decimal('99'))    # drift
    assert refresh_cash_available(cash) == Decimal('60.00')
    with pytest.raises(ValueError):
        apply_cash_to_invoice(cash.pk, inv.pk, Decimal('61'))         # the row's 99 never counted
