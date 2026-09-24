"""The cash commands — pay, refund, receive (Bill, 2026-09-24; plan §11.6, §13).

    POST /wcapi/cash/                        save an empty Cash (purpose "empty") for its id
    POST /wcapi/cash/<id>/pay/               charge it: {payment_method_token}
    POST /wcapi/cash/<id>/refund/            refund it: {amount_cents?}
    POST /wcapi/cash/_receive/<provider>/    the gateway tells us how a charge ended

Each runs through ``verbs.run_command``: code before → user before → this base → code
after → user after, on the Cash locked. The money rule (§5): only these bases move money,
and only through the cash door, once.

- **Pay** claims the empty Cash (purpose "payment", status processing) and commits; the
  gateway is called after the commit, so a refused pay never charges a card, and a card is
  never charged against a Cash that does not exist. A Cash already claimed is refused, so
  a double-click cannot charge twice (Bill: create the record for its id).
- **The outcome** — the gateway's answer to the charge, or its webhook — goes through one
  function, ``record_outcome``. A charge that succeeded completes the Cash and applies it
  to its invoice through the cash door, once: the status moves from processing to
  completed under the row lock, and the application's Pending carries the gateway event
  id, which Pending holds unique (Bill: a completed charge applies itself).
- **Refund** calls the gateway after the commit, then reverses the Cash's applications
  through the cash door by the amount refunded, newest first (Bill: a refund reverses).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.services.door import Refused

logger = logging.getLogger(__name__)

EMPTY = 'empty'            # a Cash saved for its id; nothing moved (plan §13.5)
PAYMENT = 'payment'        # a Cash a pay has claimed
PROVIDERS = ('spreedly',)  # known gateways; Stripe and PayPal checks are to be written


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _cents(amount) -> int:
    return int((_d(amount) * 100).to_integral_value())


def _gateway():
    from apps.transactions.services.cash.spreedly_gateway import SpreedlyService
    return SpreedlyService.from_settings()


def _seen(event_id: Optional[str]) -> bool:
    from apps.core.models.pending import Pending
    return bool(event_id) and Pending.objects.filter(
        changes__gateway_event_id=event_id).exists()


# ── pay ───────────────────────────────────────────────────────────────

def pay(ctx) -> Dict[str, Any]:
    cash = ctx.obj
    token = ctx.data.get('payment_method_token')
    if not token:
        raise Refused(400, 'payment_method_token_required',
                      'A card payment needs the payment_method_token from the card form.')
    if cash.purpose != EMPTY or cash.status not in (None, '', 'pending') or cash.gateway_transaction_id:
        raise Refused(409, 'cash_not_empty',
                      f'Cash {cash.pk} is already {cash.status or cash.purpose}; a new payment '
                      f'starts with a new empty Cash (POST /wcapi/cash/).',
                      {'id': cash.pk, 'status': cash.status, 'purpose': cash.purpose})
    if not cash.invoice_id:
        raise Refused(400, 'invoice_required',
                      f'Cash {cash.pk} names no invoice; a payment pays an invoice.')

    from apps.transactions.models import Invoice
    from apps.transactions.services.pricing.dual_pricing import compute_cash_amount
    invoice = Invoice.objects.select_for_update().get(pk=cash.invoice_id)
    amount = _d(ctx.data.get('amount') or cash.amount)
    if amount <= 0:
        raise Refused(400, 'amount_required', 'A payment needs an amount above zero.')

    pricing = compute_cash_amount(invoice.totals or {}, cash.method or '')
    fee = _d(pricing['surcharge'])
    charge = _d(pricing['amount']) if fee > 0 else amount

    meta = cash.metadata if isinstance(cash.metadata, dict) else {}
    if fee > 0:
        meta.setdefault('processing_fees', []).append({
            'type': 'dual_pricing_surcharge', 'rate': pricing['card_rate'],
            'amount': float(fee), 'base_total': float(charge - fee)})
    cash.metadata = meta
    cash.amount = charge
    cash.fee_amount = fee
    cash.purpose = PAYMENT
    cash.status = 'processing'
    cash.gateway = 'spreedly'
    cash.contact_id = cash.contact_id or ctx.user_id
    cash.add_audit_entry('pay_requested', {'amount_cents': _cents(charge), 'fee': float(fee),
                                           'by': ctx.user_id})
    cash.save()

    cash_id = cash.pk
    transaction.on_commit(lambda: charge_card(cash_id, token))
    return {'id': cash_id, 'status': 'processing', 'amount': float(charge),
            'surcharge': float(fee), 'is_cash_price': pricing['is_cash_price']}


def charge_card(cash_id: int, token: str) -> None:
    """After the commit: ask the gateway to charge, and record what it answered."""
    from apps.transactions.services.cash.spreedly_gateway import SpreedlyError
    from apps.transactions.models import Cash
    cash = Cash.objects.get(pk=cash_id)
    try:
        result = _gateway().purchase(token, _cents(cash.amount), order_id=f'wc3-{cash_id}')
    except SpreedlyError as e:
        logger.error('Cash %s: the gateway refused the charge: %s', cash_id, e)
        record_outcome(cash_id, state='failed', txn={'message': str(e)})
        return
    txn = result.get('transaction', {})
    record_outcome(cash_id, state='succeeded' if txn.get('succeeded') else 'failed', txn=txn)


# ── the outcome of a charge ───────────────────────────────────────────

@transaction.atomic
def record_outcome(cash_id: int, *, state: str, txn: Dict[str, Any]) -> Optional[str]:
    """How a charge ended, from its own answer or from the gateway's webhook — the one
    place a card payment moves money. Returns what happened, or None if it was already
    recorded."""
    from apps.transactions.models import Cash
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice

    cash = Cash.objects.select_for_update().get(pk=cash_id)
    event_id = txn.get('token') or ''
    if cash.status == 'completed' or _seen(event_id):
        return None                                  # already settled: a retry changes nothing

    if event_id:
        cash.gateway_transaction_id = event_id
    if txn.get('gateway_transaction_id'):
        cash.gateway_payment_intent_id = txn['gateway_transaction_id']
    pm = txn.get('payment_method') or {}
    if pm:
        refs = cash.refs if isinstance(cash.refs, dict) else {}
        refs['card'] = {'pm_token': pm.get('token', ''), 'last4': pm.get('last_four_digits', ''),
                        'brand': pm.get('card_type', ''), 'exp_month': pm.get('month', ''),
                        'exp_year': pm.get('year', ''), 'fingerprint': pm.get('fingerprint', '')}
        cash.refs = refs

    if state != 'succeeded':
        if cash.status == 'failed':
            return None
        cash.status = 'failed'
        cash.gateway_response = {'succeeded': False, 'state': state,
                                 'message': txn.get('message', '')}
        cash.add_audit_entry('gateway_failed', {'token': event_id, 'state': state})
        cash.save()
        return 'failed'

    cash.status = 'completed'
    cash.dt_processed = timezone.now()
    cash.gateway_response = {'succeeded': True, 'spreedly_token': event_id,
                             'gateway_transaction_id': txn.get('gateway_transaction_id', ''),
                             'message': txn.get('message', '')}
    cash.add_audit_entry('gateway_completed', {'token': event_id,
                                               'amount_cents': _cents(cash.amount)})
    cash.save()

    applied = _d(cash.amount) - _d(cash.fee_amount)   # the surcharge is not the invoice's
    if cash.invoice_id and applied > 0:
        try:
            with transaction.atomic():
                apply_cash_to_invoice(cash.pk, cash.invoice_id, applied,
                                      reason='card payment', contact_id=cash.contact_id,
                                      gateway_event_id=event_id or f'cash-{cash.pk}')
        except IntegrityError:
            return None                              # the same event applied in another thread
    return 'completed'


# ── refund ────────────────────────────────────────────────────────────

def refund(ctx) -> Dict[str, Any]:
    cash = ctx.obj
    if cash.status not in ('completed', 'partially_refunded') or not cash.gateway_transaction_id:
        raise Refused(409, 'cash_not_refundable',
                      f'Cash {cash.pk} is {cash.status or "not charged"}; only a completed card '
                      f'payment can be refunded.', {'id': cash.pk, 'status': cash.status})
    meta = cash.metadata if isinstance(cash.metadata, dict) else {}
    refunded = sum(int(r.get('amount_cents') or 0) for r in meta.get('refunds', []))
    left = _cents(cash.amount) - refunded
    asked = ctx.data.get('amount_cents')
    cents = left if asked in (None, '') else int(asked)
    if cents <= 0 or cents > left:
        raise Refused(400, 'refund_amount',
                      f'Cash {cash.pk} has {left / 100:.2f} left to refund; {cents / 100:.2f} '
                      f'was asked.', {'left_cents': left, 'asked_cents': cents})

    cash.add_audit_entry('refund_requested', {'amount_cents': cents, 'by': ctx.user_id})
    cash.save(update_fields=['metadata', 'version', 'dt_modified'])
    cash_id = cash.pk
    transaction.on_commit(lambda: refund_card(cash_id, cents, ctx.user_id))
    return {'id': cash_id, 'refund_cents': cents}


def refund_card(cash_id: int, cents: int, acted_by: Optional[int]) -> None:
    from apps.transactions.models import Cash
    from apps.transactions.services.cash.spreedly_gateway import SpreedlyError
    cash = Cash.objects.get(pk=cash_id)
    meta = cash.metadata if isinstance(cash.metadata, dict) else {}
    full = not meta.get('refunds') and cents == _cents(cash.amount)
    try:
        result = _gateway().refund(cash.gateway_transaction_id, cents, full=full)
    except SpreedlyError as e:
        logger.error('Cash %s: the gateway refused the refund: %s', cash_id, e)
        _record_refund_failed(cash_id, cents, str(e))
        return
    txn = result.get('transaction', {})
    if not txn.get('succeeded'):
        _record_refund_failed(cash_id, cents, txn.get('message', ''))
        return
    record_refund(cash_id, cents, event_id=txn.get('token') or f'refund-{cash_id}-{cents}',
                  acted_by=acted_by)


@transaction.atomic
def _record_refund_failed(cash_id: int, cents: int, message: str) -> None:
    from apps.transactions.models import Cash
    cash = Cash.objects.select_for_update().get(pk=cash_id)
    cash.add_audit_entry('refund_failed', {'amount_cents': cents, 'message': message})
    cash.save(update_fields=['metadata', 'version', 'dt_modified'])


@transaction.atomic
def record_refund(cash_id: int, cents: int, *, event_id: str,
                  acted_by: Optional[int] = None) -> Optional[str]:
    """A refund the gateway made: reverse the Cash's applications by that much, newest
    first, each reversal carrying the event id; then mark the Cash."""
    from apps.transactions.models import Cash
    from apps.transactions.services.cash import cash_door

    cash = Cash.objects.select_for_update().get(pk=cash_id)
    meta = cash.metadata if isinstance(cash.metadata, dict) else {}
    refunds = meta.setdefault('refunds', [])
    if any(r.get('event_id') == event_id for r in refunds):
        return None                                  # this refund is already recorded

    left = _d(cents) / 100
    for n, application in enumerate(reversed(cash_door._applications(cash_id=cash.pk))):
        if left <= 0:
            break
        live = cash_door.live(application)
        if live <= 0:
            continue
        take = min(live, left)
        cash_door.reverse_application(application, 'card refund', acted_by=acted_by,
                                      amount=-take, gateway_event_id=f'{event_id}:{n}')
        left -= take

    refunds.append({'event_id': event_id, 'amount_cents': cents,
                    'dt': timezone.now().isoformat(), 'by': acted_by})
    total = sum(int(r['amount_cents']) for r in refunds)
    cash.refresh_from_db()
    cash.metadata = {**(cash.metadata or {}), 'refunds': refunds}
    cash.status = 'refunded' if total >= _cents(cash.amount) else 'partially_refunded'
    cash.add_audit_entry('gateway_refund', {'token': event_id, 'amount_cents': cents})
    cash.save()
    return cash.status


# ── receive: the gateway's webhook ────────────────────────────────────

def receive(ctx) -> Dict[str, Any]:
    """The one command the public actor reaches (plan §11.7d). The body is not trusted: a
    known provider's event is confirmed by asking the provider (Spreedly's show_transaction)
    before anything is recorded."""
    provider = ctx.data.get('_provider') or ''
    if provider not in PROVIDERS:
        raise Refused(400, 'unknown_provider',
                      f'No payment provider {provider!r} is configured here.',
                      {'providers': list(PROVIDERS)})
    body = ctx.data.get('_body') or {}
    token = ((body.get('transaction') or {}).get('token') or '') if isinstance(body, dict) else ''
    if not token:
        raise Refused(400, 'no_transaction_token', 'The event names no transaction.')

    from apps.transactions.models import Cash
    cash_id = Cash.objects.filter(gateway_transaction_id=token).values_list('pk', flat=True).first()
    if cash_id is None:
        logger.warning('Gateway event for unknown transaction %s — ignored', token)
        return {'status': 'ignored'}
    try:
        verified = _gateway().show_transaction(token).get('transaction', {})
    except Exception as e:  # noqa: BLE001 — the provider will retry; nothing was recorded
        raise Refused(502, 'verification_failed', f'Could not confirm {token}: {e}')
    state = verified.get('state', '')
    if state == 'succeeded':
        outcome = record_outcome(cash_id, state='succeeded', txn=verified)
    elif state in ('failed', 'gateway_processing_failed'):
        outcome = record_outcome(cash_id, state=state, txn=verified)
    else:
        outcome = None
    return {'status': 'ok', 'outcome': outcome}


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('cash', 'pay', pay)
    register_command('cash', 'refund', refund)
    register_command('cash', 'receive', receive, needs_record=False, public=True)
