"""in_step must be able to see the axis the drift is on.

For as long as the AP sign bug lived, `compute_vendor_summary` reported `in_step: true`
while `net` was wrong by twice every payment — it compared receipt balances to ledger echoes,
both of which were correct throughout, and never looked at the cash.

The check that catches it is an invariant, not a recomputation: `available` must lie between
zero and `amount`. A checker that recomputed `available` the way the writer computes it would
have agreed with the writer and still said clean.
"""
from decimal import Decimal
from types import SimpleNamespace

from apps.accounts.services.ledger_balance import _cash_outside_its_own_range


def _cash(amount, available, pk=41, ida=None):
    return SimpleNamespace(pk=pk, ida=ida,
                           amount=Decimal(amount), available=Decimal(available))


def test_the_bug_that_hid_behind_in_step():
    """A -60.00 payment reporting -120.00 available: more unspent than it ever held."""
    msg = _cash_outside_its_own_range(_cash('-60.00', '-120.00'))
    assert msg and 'more unapplied than the payment ever held' in msg


def test_opus_case_a_hundred_paid_reporting_two_hundred_left():
    assert _cash_outside_its_own_range(_cash('-100.00', '-200.00'))


def test_available_may_not_face_the_other_way():
    """A payment out with money coming back is not a smaller number, it is a wrong one."""
    assert _cash_outside_its_own_range(_cash('-20.00', '10.00'))
    assert _cash_outside_its_own_range(_cash('100.00', '-10.00'))


def test_an_overapplied_payment_is_caught():
    assert _cash_outside_its_own_range(_cash('100.00', '150.00'))


# ── what is fine ─────────────────────────────────────────────────────────────────

def test_fully_applied_is_fine():
    assert _cash_outside_its_own_range(_cash('-60.00', '0.00')) is None
    assert _cash_outside_its_own_range(_cash('100.00', '0.00')) is None


def test_partly_applied_is_fine():
    assert _cash_outside_its_own_range(_cash('-500.00', '-379.00')) is None
    assert _cash_outside_its_own_range(_cash('500.00', '379.00')) is None


def test_untouched_is_fine():
    assert _cash_outside_its_own_range(_cash('-60.00', '-60.00')) is None


def test_a_zero_payment_says_nothing():
    assert _cash_outside_its_own_range(_cash('0.00', '0.00')) is None
