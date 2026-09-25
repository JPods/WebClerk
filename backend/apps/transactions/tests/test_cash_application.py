"""
Cash applied to invoices — the numbers must balance; the user chooses how.

  invoice received = Σ applied cash_application amounts
  invoice balance  = total − received          (cash_state derived)
  cash available   = amount − Σ applied from that cash
  Σ org ledgers    = Σ invoice balances − Σ unapplied cash

Run:
    python -m pytest apps/transactions/tests/test_cash_application.py --no-cov -q
"""
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def customer():
    from apps.orgs.models import OrgBase
    return OrgBase.objects.create(company="Cash Test Customer", org_type="customer")


@pytest.fixture
def term_net30():
    from apps.accounts.models import Term
    return Term.objects.get(ida="N30")


def _invoice(customer, total, term=None):
    from apps.transactions.models import Invoice
    from apps.accounts.services.terms_ledger import apply_terms_for_invoice
    inv = Invoice.objects.create(
        status='released', customer=customer,
        totals={'amount': total, 'total': total, 'received': 0, 'balance': total},
    )
    apply_terms_for_invoice(inv, term=term, replace=True)
    return inv


def _cash(customer, amount, method='check'):
    from apps.transactions.models import Cash
    return Cash.objects.create(
        amount=Decimal(str(amount)), available=Decimal(str(amount)),
        status='completed', method=method, customer_id=customer.id,
    )


def _refresh(*records):
    for r in records:
        r.refresh_from_db()


def _ledger_sum(customer):
    from apps.accounts.models import Ledger
    return sum(Decimal(str(v or 0)) for v in
               Ledger.objects.filter(org_id=customer.id).values_list('value_available', flat=True))


def _apply(cash, invoice, amount):
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
    return apply_cash_to_invoice(cash.pk, invoice.pk, amount)


class TestCashState:
    def test_states(self):
        from apps.transactions.services.cash.cash_pending import cash_state
        assert cash_state(100, 0) == 'open'
        assert cash_state(100, 40) == 'partial'
        assert cash_state(100, 100) == 'paid'
        assert cash_state(-30, 0) == 'credit'
        assert cash_state(-30, -10) == 'partial'
        assert cash_state(-30, -30) == 'paid'
        assert cash_state(100, 130) == 'over'


class TestApply:
    def test_partial_then_paid(self, customer, term_net30):
        inv = _invoice(customer, 100, term_net30)
        cash = _cash(customer, 100)

        _apply(cash, inv, 40)
        _refresh(inv, cash)
        assert inv.totals['received'] == 40.0
        assert inv.totals['balance'] == 60.0
        assert inv.totals['cash_state'] == 'partial'
        assert inv.status == 'released'  # workflow untouched
        assert cash.available == Decimal('60.00')

        _apply(cash, inv, 60)
        _refresh(inv, cash)
        assert inv.totals['cash_state'] == 'paid'
        assert cash.available == Decimal('0.00')
        assert _ledger_sum(customer) == Decimal('0')

    def test_cannot_apply_past_balance(self, customer, term_net30):
        """The bound is on the running total now, and the message says what is left
        rather than naming a state (2026-09-20). The refusal is unchanged."""
        inv = _invoice(customer, 100, term_net30)
        cash = _cash(customer, 500)
        with pytest.raises(ValueError, match='still open'):
            _apply(cash, inv, 120)

    def test_cannot_apply_more_than_available(self, customer, term_net30):
        inv = _invoice(customer, 100, term_net30)
        cash = _cash(customer, 30)
        with pytest.raises(ValueError, match='available to apply'):
            _apply(cash, inv, 50)

    def test_overpayment_stays_as_customer_credit(self, customer, term_net30):
        inv = _invoice(customer, 100, term_net30)
        cash = _cash(customer, 150)
        _apply(cash, inv, 100)
        _refresh(inv, cash)
        assert inv.totals['cash_state'] == 'paid'
        assert cash.available == Decimal('50.00')
        assert _ledger_sum(customer) == Decimal('-50')

    def test_deposit_is_credit_until_applied(self, customer, term_net30):
        _cash(customer, 75)
        assert _ledger_sum(customer) == Decimal('-75')
        inv = _invoice(customer, 200, term_net30)
        assert _ledger_sum(customer) == Decimal('125')

    def test_unapply_restores_balances(self, customer, term_net30):
        from apps.transactions.services.cash.cash_pending import unapply_cash_application
        inv = _invoice(customer, 100, term_net30)
        cash = _cash(customer, 100)
        result = _apply(cash, inv, 100)
        unapply_cash_application(result['pending_id'], reason='applied to wrong invoice')
        _refresh(inv, cash)
        assert inv.totals['received'] == 0.0
        assert inv.totals['cash_state'] == 'open'
        assert cash.available == Decimal('100.00')
        assert _ledger_sum(customer) == Decimal('0')


class TestCreditMemo:
    def test_credit_memo_is_customer_credit(self, customer):
        memo = _invoice(customer, -40)
        assert memo.totals['total'] == -40
        assert _ledger_sum(customer) == Decimal('-40')

    def test_refund_settles_credit_memo(self, customer):
        memo = _invoice(customer, -40)
        refund = _cash(customer, -40)
        _apply(refund, memo, -40)
        _refresh(memo, refund)
        assert memo.totals['cash_state'] == 'paid'
        assert refund.available == Decimal('0.00')
        assert _ledger_sum(customer) == Decimal('0')

    def test_positive_cash_cannot_settle_credit_memo(self, customer):
        memo = _invoice(customer, -40)
        cash = _cash(customer, 40)
        with pytest.raises(ValueError):
            _apply(cash, memo, 40)

    def test_transfer_credit_to_invoice(self, customer, term_net30):
        from apps.transactions.models import Cash
        from apps.transactions.services.cash.cash_pending import transfer_credit
        memo = _invoice(customer, -40)
        inv = _invoice(customer, 100, term_net30)

        result = transfer_credit(memo.pk, inv.pk, 40, reason='return credit')
        _refresh(memo, inv)
        transfer = Cash.objects.get(pk=result['cash_id'])
        assert memo.totals['cash_state'] == 'paid'
        assert inv.totals['balance'] == 60.0
        assert inv.totals['cash_state'] == 'partial'
        assert transfer.method == 'credit_transfer'
        assert transfer.available == Decimal('0.00')
        assert _ledger_sum(customer) == Decimal('60')

    def test_credit_left_open_is_users_choice(self, customer, term_net30):
        memo = _invoice(customer, -40)
        _invoice(customer, 100, term_net30)
        memo.refresh_from_db()
        assert memo.totals['balance'] == -40
        assert _ledger_sum(customer) == Decimal('60')
