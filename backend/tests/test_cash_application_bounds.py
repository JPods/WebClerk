"""Balance, not buckets.

Bill, 2026-09-20: *"We care that things balance, not that they are in the perfect bucket."*
And: *"We should use +- but also eliminate the mandate for >0. Users might have reasons for
violating that."*

The user decides how to apply their money. The only arithmetic limit is that they cannot
apply money that does not exist, so the bound is on the running total, never on the sign of
any one application.

**The convention, which the AP path has always had.** An application carries its
*document's* sign:

    receipt total  = +100.00   what we owe the vendor
    cash amount    =  -60.00   money leaving
    application    = +60.00    how much of that payment went to this bill

``paid`` and ``balance`` are derived from the applications, so an application stored with
the cash's sign would make a payable report a negative amount paid. The document therefore
carries the sign check; the cash bounds magnitude only, because on AP it points the other
way and requiring its sign would forbid every AP application there is.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.transactions.services.cash.cash_pending import _check_application


def _cash(pk=1, amount='100.00', customer_id=None, vendor_id=None):
    return SimpleNamespace(pk=pk, amount=Decimal(amount),
                           customer_id=customer_id, vendor_id=vendor_id)


def _doc(pk=9, total='100.00', kind='invoice', customer_id=None, vendor_id=None):
    return SimpleNamespace(pk=pk, totals={'total': total},
                           customer_id=customer_id, vendor_id=vendor_id,
                           _meta=SimpleNamespace(model_name=kind))


def _payable(pk=9, total='100.00', vendor_id=None):
    """A payable: stored positive, settled by a negative payment out."""
    return _doc(pk=pk, total=total, kind='receipt', vendor_id=vendor_id)


_AP = dict(party_attr='vendor_id', party_label='vendor')


def _check(cash, doc, amount, target_applied='0', cash_applied='0', **kw):
    return _check_application(cash, doc, Decimal(amount),
                              target_applied=Decimal(target_applied),
                              cash_applied=Decimal(cash_applied), **kw)


# ── what is allowed ──────────────────────────────────────────────────────────────

def test_a_negative_payment_pays_a_positive_payable():
    """The shape production has: the sides point opposite ways and the application takes
    the document's."""
    _check(_cash(amount='-100.00'), _payable(total='100.00'), '40.00', **_AP)


def test_a_negative_application_may_unwind_an_earlier_one():
    """The case `amount must be positive` made impossible to record: 40 of a 100 payment
    is applied, and the user takes 20 of it back."""
    _check(_cash(amount='-100.00'), _payable(total='100.00'), '-20.00',
           target_applied='40.00', cash_applied='40.00', **_AP)


def test_applying_the_whole_remainder_is_allowed():
    _check(_cash(amount='100.00'), _doc(total='100.00'), '60.00',
           target_applied='40.00', cash_applied='40.00')


def test_a_refund_settles_a_credit_memo():
    """AR, both sides negative: we owe the customer, and the cash goes out."""
    _check(_cash(amount='-40.00'), _doc(total='-40.00'), '-40.00')


def test_a_sister_division_shift_is_two_applications_that_balance():
    """Bill, 2026-09-20: payments were applied across sister divisions listed as separate
    customers. The honest record is a negative application on one and a positive on the
    other — each legal on its own, and together they balance."""
    # take 30 back off division A's invoice
    _check(_cash(pk=1, amount='100.00', customer_id=7),
           _doc(pk=9, total='100.00', customer_id=7),
           '-30.00', target_applied='100.00', cash_applied='100.00')
    # and put 30 onto division B's, from B's own cash
    _check(_cash(pk=2, amount='30.00', customer_id=8),
           _doc(pk=10, total='30.00', customer_id=8), '30.00')


# ── what is still refused ────────────────────────────────────────────────────────

def test_zero_has_nothing_to_record():
    with pytest.raises(ValueError, match="nothing to record"):
        _check(_cash(), _doc(), '0')


def test_the_total_may_not_exceed_the_document():
    with pytest.raises(ValueError, match="still open"):
        _check(_cash(amount='500.00'), _doc(total='100.00'), '80.00',
               target_applied='40.00', cash_applied='40.00')


def test_a_positive_cash_cannot_settle_a_credit_memo():
    """AR's document carries the sign, so this stays refused. Dropping the document sign
    check — an earlier attempt at the AP fix — let it through."""
    with pytest.raises(ValueError, match="still open"):
        _check(_cash(amount='40.00'), _doc(total='-40.00'), '40.00')


def test_the_payment_may_not_give_more_than_it_holds():
    """Fable, recheck 3: a -20 cash was allowed to pay 30. AR refused it; AP had no check
    at all beyond `amount must be positive`."""
    with pytest.raises(ValueError, match="still unapplied"):
        _check(_cash(amount='-20.00'), _payable(total='500.00'), '30.00', **_AP)


def test_the_payable_may_not_take_more_than_it_owes():
    with pytest.raises(ValueError, match="still open"):
        _check(_cash(amount='-500.00'), _payable(total='30.00'), '40.00', **_AP)


def test_an_application_may_not_point_against_its_document():
    with pytest.raises(ValueError, match="still open"):
        _check(_cash(amount='-100.00'), _payable(total='100.00'), '-30.00', **_AP)


def test_one_customers_money_does_not_pay_anothers_invoice():
    """Not a balance rule — it balances fine — but the relationship it publishes."""
    with pytest.raises(ValueError, match="customers differ"):
        _check(_cash(amount='100.00', customer_id=7),
               _doc(total='100.00', customer_id=8), '100.00')


def test_the_refusal_tells_the_user_what_to_do_instead():
    """Coach, don't drop: the message names the path that works."""
    with pytest.raises(ValueError, match="negative application on one and a positive"):
        _check(_cash(amount='100.00', customer_id=7),
               _doc(total='100.00', customer_id=8), '100.00')


def test_one_vendors_money_does_not_pay_anothers_bill():
    """AP had no party check at all."""
    with pytest.raises(ValueError, match="vendors differ"):
        _check(_cash(amount='-100.00', vendor_id=3),
               _payable(total='100.00', vendor_id=4), '100.00', **_AP)
