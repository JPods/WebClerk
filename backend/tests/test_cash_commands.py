"""The cash commands: pay, refund, receive (Bill, 2026-09-24; plan §11.6, §13).

The money rule (§5): money moves only in a base, through the cash door, once — one Pending
per effect, however many times the gateway answers. A completed charge applies itself to
its invoice; a refund reverses through the cash door; a Cash is saved empty for its id and
a command claims it.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.core.models.pending import Pending
from apps.core.services import verbs
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.transactions.models import Cash, Invoice
from apps.transactions.services.cash import cash_commands, cash_door

pytestmark = pytest.mark.django_db


class FakeGateway:
    """Spreedly as the tests need it: a charge token per purchase, and what it says later."""

    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.purchases, self.refunds = [], []
        self.states = {}

    def purchase(self, token, amount_cents, order_id=''):
        txn_token = f'txn-{len(self.purchases) + 1}'
        self.purchases.append((token, amount_cents, order_id))
        self.states[txn_token] = 'succeeded' if self.succeeds else 'failed'
        return {'transaction': {'token': txn_token, 'succeeded': self.succeeds,
                                'gateway_transaction_id': f'gw-{txn_token}',
                                'message': 'ok' if self.succeeds else 'declined',
                                'payment_method': {'last_four_digits': '4242'}}}

    def refund(self, txn_token, amount_cents=None, *, full=True):
        self.refunds.append((txn_token, amount_cents, full))
        return {'transaction': {'token': f'refund-{len(self.refunds)}', 'succeeded': True}}

    def show_transaction(self, txn_token):
        return {'transaction': {'token': txn_token, 'state': self.states.get(txn_token, ''),
                                'succeeded': self.states.get(txn_token) == 'succeeded'}}


@pytest.fixture
def gateway(monkeypatch):
    fake = FakeGateway()
    monkeypatch.setattr(cash_commands, '_gateway', lambda: fake)
    return fake


@pytest.fixture
def invoice(db):
    from apps.orgs.models import OrgBase
    buyer = OrgBase.objects.create(company='Card Buyer', org_type='customer', is_active=True)
    return Invoice.objects.create(customer_id=buyer.pk, status='open',
                                  totals={'total': 100.0, 'received': 0.0, 'balance': 100.0})


def _empty_cash(invoice, amount='100.00'):
    return save_record(Actor.system(), {'model_name': 'cash', 'invoice_id': invoice.pk,
                                        'amount': amount, 'method': 'card',
                                        'purpose': 'empty'}).obj


def _pay(cash, capture, token='pm-1'):
    with capture(execute=True):
        return verbs.run(Actor.system(), 'pay', 'cash',
                         {'id': cash.pk, 'payment_method_token': token})


def _applications(cash):
    return Pending.objects.filter(purpose__in=cash_door.CASH_PURPOSES,
                                  changes__cash_id=cash.pk)


def _balance(invoice):
    invoice.refresh_from_db()
    return Decimal(str(invoice.totals['balance']))


# ── pay ───────────────────────────────────────────────────────────────

def test_a_completed_charge_applies_itself_to_its_invoice_once(
        invoice, gateway, django_capture_on_commit_callbacks):
    cash = _empty_cash(invoice)
    _pay(cash, django_capture_on_commit_callbacks)

    cash.refresh_from_db()
    assert cash.status == 'completed' and cash.purpose == cash_commands.PAYMENT
    assert gateway.purchases == [('pm-1', 10000, f'wc3-{cash.pk}')]
    applied = _applications(cash).get()
    assert applied.changes['gateway_event_id'] == 'txn-1'
    assert _balance(invoice) == Decimal('0')

    # The gateway's own answer and its webhook both arrive; the second changes nothing.
    cash_commands.record_outcome(cash.pk, state='succeeded',
                                 txn={'token': 'txn-1', 'succeeded': True})
    verbs.run_command(Actor.anonymous(), 'receive', 'cash', None,
                      {'_provider': 'spreedly', '_body': {'transaction': {'token': 'txn-1'}}})
    assert _applications(cash).count() == 1, 'one Pending per effect'
    assert _balance(invoice) == Decimal('0')


def test_a_cash_already_claimed_cannot_be_charged_again(
        invoice, gateway, django_capture_on_commit_callbacks):
    cash = _empty_cash(invoice)
    _pay(cash, django_capture_on_commit_callbacks)
    with pytest.raises(Refused) as refused:
        _pay(cash, django_capture_on_commit_callbacks)
    assert refused.value.code == 'cash_not_empty'
    assert len(gateway.purchases) == 1, 'a double-click cannot charge twice'


def test_a_declined_charge_moves_nothing(invoice, monkeypatch,
                                         django_capture_on_commit_callbacks):
    declined = FakeGateway(succeeds=False)
    monkeypatch.setattr(cash_commands, '_gateway', lambda: declined)
    cash = _empty_cash(invoice)
    _pay(cash, django_capture_on_commit_callbacks)
    cash.refresh_from_db()
    assert cash.status == 'failed'
    assert not _applications(cash).exists()
    assert _balance(invoice) == Decimal('100')


def test_a_refused_pay_never_reaches_the_gateway(invoice, gateway,
                                                 django_capture_on_commit_callbacks):
    cash = _empty_cash(invoice)
    with django_capture_on_commit_callbacks(execute=True), pytest.raises(Refused):
        verbs.run(Actor.system(), 'pay', 'cash', {'id': cash.pk})     # no card token
    assert gateway.purchases == []


def test_an_empty_cash_cannot_be_saved_as_paid(invoice):
    with pytest.raises(Refused) as refused:
        save_record(Actor.system(), {'model_name': 'cash', 'invoice_id': invoice.pk,
                                     'amount': '100.00', 'purpose': 'empty',
                                     'status': 'completed'})
    assert refused.value.code == 'empty_cash'


# ── refund ────────────────────────────────────────────────────────────

def test_a_full_refund_reverses_the_application_through_the_cash_door(
        invoice, gateway, django_capture_on_commit_callbacks):
    cash = _empty_cash(invoice)
    _pay(cash, django_capture_on_commit_callbacks)
    with django_capture_on_commit_callbacks(execute=True):
        verbs.run(Actor.system(), 'refund', 'cash', {'id': cash.pk})

    cash.refresh_from_db()
    assert cash.status == 'refunded'
    assert gateway.refunds == [('txn-1', 10000, True)]
    reversal = Pending.objects.get(changes__reverses__isnull=False, changes__cash_id=cash.pk)
    assert Decimal(str(reversal.changes['amount'])) == Decimal('-100.00')
    assert _balance(invoice) == Decimal('100')

    # The same refund recorded again changes nothing.
    assert cash_commands.record_refund(cash.pk, 10000, event_id='refund-1') is None
    assert Pending.objects.filter(changes__reverses__isnull=False,
                                  changes__cash_id=cash.pk).count() == 1


def test_a_partial_refund_is_a_credit_not_a_void(
        invoice, gateway, django_capture_on_commit_callbacks):
    cash = _empty_cash(invoice)
    _pay(cash, django_capture_on_commit_callbacks)
    with django_capture_on_commit_callbacks(execute=True):
        verbs.run(Actor.system(), 'refund', 'cash', {'id': cash.pk, 'amount_cents': 2500})
    cash.refresh_from_db()
    assert cash.status == 'partially_refunded'
    assert gateway.refunds == [('txn-1', 2500, False)], 'a void would cancel the whole charge'
    assert _balance(invoice) == Decimal('25')

    with pytest.raises(Refused) as refused:
        verbs.run(Actor.system(), 'refund', 'cash', {'id': cash.pk, 'amount_cents': 9000})
    assert refused.value.code == 'refund_amount', 'no more than is left'


def test_an_uncharged_cash_cannot_be_refunded(invoice, gateway):
    cash = _empty_cash(invoice)
    with pytest.raises(Refused) as refused:
        verbs.run(Actor.system(), 'refund', 'cash', {'id': cash.pk})
    assert refused.value.code == 'cash_not_refundable'


# ── receive and who may ───────────────────────────────────────────────

def test_the_public_reaches_receive_and_nothing_else(invoice, gateway):
    cash = _empty_cash(invoice)
    with pytest.raises(Refused) as refused:
        verbs.run_command(Actor.anonymous(), 'pay', 'cash', cash.pk,
                          {'payment_method_token': 'pm-x'})
    assert refused.value.status == 401
    with pytest.raises(Refused) as unknown:
        verbs.run_command(Actor.anonymous(), 'receive', 'cash', None,
                          {'_provider': 'stripe', '_body': {}})
    assert unknown.value.code == 'unknown_provider'


def test_the_routes(client, django_user_model, invoice, gateway,
                    django_capture_on_commit_callbacks):
    admin = django_user_model.objects.create_user(email='pay-admin@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    saved = client.post('/wcapi/cash/', {'model_name': 'cash', 'invoice_id': invoice.pk,
                                         'amount': '100.00', 'method': 'card',
                                         'purpose': 'empty'}, content_type='application/json')
    assert saved.status_code in (200, 201), saved.content
    cash_id = saved.json()['data']['id']
    with django_capture_on_commit_callbacks(execute=True):
        paid = client.post(f'/wcapi/cash/{cash_id}/pay/', {'payment_method_token': 'pm-1'},
                           content_type='application/json')
    assert paid.status_code == 200, paid.content
    assert paid.json()['data']['result']['status'] == 'processing'
    # In a request the charge runs as the command commits, before the response; under the
    # test's outer transaction it runs as the capture closes, so the record is read here.
    assert Cash.objects.get(pk=cash_id).status == 'completed'
    unknown = client.post(f'/wcapi/cash/{cash_id}/frobnicate/', {},
                          content_type='application/json')
    assert unknown.status_code == 404

    client.logout()
    hook = client.post('/wcapi/cash/_receive/spreedly/',
                       data='{"transaction": {"token": "txn-1"}}',
                       content_type='application/json')
    assert hook.status_code == 200, hook.content
    assert _applications(Cash.objects.get(pk=cash_id)).count() == 1


def test_a_gateway_event_moves_money_once_even_around_the_code(invoice):
    """The database holds it: two Pendings for one gateway event cannot both exist."""
    Pending.objects.create(model_name='cash', record_id='1', purpose='audit_note',
                           dt_processed=1, changes={'gateway_event_id': 'evt-9'})
    with pytest.raises(IntegrityError), transaction.atomic():
        Pending.objects.create(model_name='cash', record_id='2', purpose='audit_note',
                               dt_processed=1, changes={'gateway_event_id': 'evt-9'})


# ── the invoice's ledger (Bill, 2026-09-24) ───────────────────────────

def test_a_change_of_terms_rebuilds_the_ledger(invoice, monkeypatch):
    from apps.accounts.services import ledger_balance
    rebuilt = []
    monkeypatch.setattr(ledger_balance, 'on_invoice_save',
                        lambda inv, replace_ledgers=True: rebuilt.append(inv.pk))
    save_record(Actor.system(), {'model_name': 'invoice', 'id': invoice.pk, 'terms': 'NET15'})
    assert rebuilt == [invoice.pk], 'once, though the total did not change'
    rebuilt.clear()
    save_record(Actor.system(), {'model_name': 'invoice', 'id': invoice.pk, 'status': 'open'})
    assert rebuilt == [], 'a save that touches nothing the ledger reads rebuilds nothing'
