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
- **The outcome** is recorded in two commits, so nothing the gateway did can be lost: its
  answer (the token, the card) is stamped first; then ``record_outcome`` settles — the
  status moves from processing to completed under the row lock and the cash door applies
  the Cash to its invoice, once, the Pending carrying the gateway event id, which Pending
  holds unique (Bill: a completed charge applies itself). If settling fails, the stamped
  Cash waits for the webhook, which settles it the same way; a charge whose answer never
  came is found by its order reference, ``wc3-<cash id>``.
- **Refund** calls the gateway after the commit and records what it refunded in its own
  commit — from then the money is spent (it never becomes available again) — and then
  reverses applications through the cash door for whatever of it was applied, newest
  first (Bill: a refund reverses). A reversal that fails is finished by the next refund.
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
    amount = _d(ctx.data.get('amount') or cash.amount).quantize(Decimal('0.01'))
    balance = _d((invoice.totals or {}).get('balance'))
    if amount <= 0:
        raise Refused(400, 'amount_required', 'A payment needs an amount above zero.')
    if amount > balance:
        raise Refused(400, 'amount_exceeds_balance',
                      f'Invoice {invoice.pk} has {balance} to pay; {amount} was asked. Nothing '
                      f'was charged.', {'balance': float(balance), 'amount': float(amount)})

    # A card surcharge (dual pricing) is the same share of this payment as of the whole
    # invoice; the invoice is paid the amount, the surcharge is the fee.
    pricing = compute_cash_amount(invoice.totals or {}, cash.method or '')
    surcharge = _d(pricing['surcharge'])
    cash_total = _d(pricing['amount']) - surcharge
    fee = ((surcharge * amount / cash_total).quantize(Decimal('0.01'))
           if surcharge > 0 and cash_total > 0 else Decimal('0'))
    charge = amount + fee

    meta = cash.metadata if isinstance(cash.metadata, dict) else {}
    if fee > 0:
        meta.setdefault('processing_fees', []).append({
            'type': 'dual_pricing_surcharge', 'rate': pricing['card_rate'],
            'amount': float(fee), 'base_total': float(amount)})
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
    return {'id': cash_id, 'status': 'processing', 'amount': float(amount),
            'surcharge': float(fee), 'charged': float(charge),
            'is_cash_price': pricing['is_cash_price']}


def charge_card(cash_id: int, token: str) -> None:
    """After the commit: ask the gateway to charge; stamp its answer; then settle."""
    from apps.transactions.models import Cash
    from apps.transactions.services.cash.spreedly_gateway import SpreedlyError
    cash = Cash.objects.get(pk=cash_id)
    try:
        result = _gateway().purchase(token, _cents(cash.amount), order_id=f'wc3-{cash_id}')
    except SpreedlyError as e:
        if 400 <= (e.status_code or 0) < 500:            # the gateway said no
            logger.warning('Cash %s: the gateway declined the charge: %s', cash_id, e)
            record_outcome(cash_id, state='failed', txn={'message': str(e)})
        else:                                            # it may have charged: the webhook says
            _note(cash_id, 'gateway_unanswered', {'message': str(e)})
        return
    except Exception as e:  # noqa: BLE001 — a timeout: the charge may have gone through
        _note(cash_id, 'gateway_unanswered', {'message': f'{type(e).__name__}: {e}'})
        return

    txn = result.get('transaction', {})
    _stamp(cash_id, txn)
    try:
        record_outcome(cash_id, state='succeeded' if txn.get('succeeded') else 'failed', txn=txn)
    except Exception as e:  # noqa: BLE001 — stamped; the webhook settles it
        logger.exception('Cash %s: charged, not yet settled', cash_id)
        _note(cash_id, 'settle_failed', {'message': f'{type(e).__name__}: {e}'})


@transaction.atomic
def _note(cash_id: int, action: str, details: Dict[str, Any]) -> None:
    from apps.transactions.models import Cash
    cash = Cash.objects.select_for_update().get(pk=cash_id)
    cash.add_audit_entry(action, details)
    cash.save(update_fields=['metadata', 'version', 'dt_modified'])


def _stamp_fields(cash, txn: Dict[str, Any]) -> None:
    if txn.get('token'):
        cash.gateway_transaction_id = txn['token']
    if txn.get('gateway_transaction_id'):
        cash.gateway_payment_intent_id = txn['gateway_transaction_id']
    pm = txn.get('payment_method') or {}
    if pm:
        refs = cash.refs if isinstance(cash.refs, dict) else {}
        refs['card'] = {'pm_token': pm.get('token', ''), 'last4': pm.get('last_four_digits', ''),
                        'brand': pm.get('card_type', ''), 'exp_month': pm.get('month', ''),
                        'exp_year': pm.get('year', ''), 'fingerprint': pm.get('fingerprint', '')}
        cash.refs = refs


@transaction.atomic
def _stamp(cash_id: int, txn: Dict[str, Any]) -> None:
    """The gateway's answer, kept before anything else is tried: its token is how the
    webhook finds this Cash if settling fails."""
    from apps.transactions.models import Cash
    cash = Cash.objects.select_for_update().get(pk=cash_id)
    _stamp_fields(cash, txn)
    cash.add_audit_entry('gateway_answered', {'token': txn.get('token', ''),
                                              'succeeded': bool(txn.get('succeeded'))})
    cash.save()


# ── the outcome of a charge ───────────────────────────────────────────

@transaction.atomic
def record_outcome(cash_id: int, *, state: str, txn: Dict[str, Any]) -> Optional[str]:
    """How a charge ended, from its own answer or from the gateway's webhook — the one
    place a card payment moves money. Returns what happened, or None if it was already
    recorded. A failure rolls everything back, to be settled again by the next arrival."""
    from apps.core.models.pending import Pending
    from apps.transactions.models import Cash
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice

    cash = Cash.objects.select_for_update().get(pk=cash_id)
    event_id = txn.get('token') or cash.gateway_transaction_id or f'cash-{cash.pk}'
    if cash.status == 'completed':
        return None                                  # already settled: a retry changes nothing
    seen = Pending.objects.filter(changes__gateway_event_id=event_id).first()
    if seen is not None:
        if str((seen.changes or {}).get('cash_id')) != str(cash.pk):
            raise ValueError(f'gateway event {event_id} already moved money for cash '
                             f'{(seen.changes or {}).get("cash_id")}, not cash {cash.pk}')
        return None

    _stamp_fields(cash, txn)
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
        apply_cash_to_invoice(cash.pk, cash.invoice_id, applied, reason='card payment',
                              contact_id=cash.contact_id, gateway_event_id=event_id)
    return 'completed'


# ── refund ────────────────────────────────────────────────────────────

def _refunds(cash) -> list:
    meta = cash.metadata if isinstance(cash.metadata, dict) else {}
    return list(meta.get('refunds') or [])


def refund(ctx) -> Dict[str, Any]:
    cash = ctx.obj
    for owed in [r for r in _refunds(cash) if not r.get('reversed')]:
        reverse_refund(cash.pk, owed['event_id'], acted_by=ctx.user_id)   # finish what failed
    cash.refresh_from_db()
    if cash.status not in ('completed', 'partially_refunded') or not cash.gateway_transaction_id:
        raise Refused(409, 'cash_not_refundable',
                      f'Cash {cash.pk} is {cash.status or "not charged"}; only a completed card '
                      f'payment can be refunded.', {'id': cash.pk, 'status': cash.status})
    left = _cents(cash.amount) - sum(int(r.get('amount_cents') or 0) for r in _refunds(cash))
    asked = ctx.data.get('amount_cents')
    cents = left if asked in (None, '') else int(asked)
    if cents <= 0 or cents > left:
        raise Refused(400, 'refund_amount',
                      f'Cash {cash.pk} has {left / 100:.2f} left to refund; {cents / 100:.2f} '
                      f'was asked.', {'left_cents': left, 'asked_cents': cents})

    cash.add_audit_entry('refund_requested', {'amount_cents': cents, 'by': ctx.user_id})
    cash.save(update_fields=['metadata', 'version', 'dt_modified'])
    cash_id, user_id = cash.pk, ctx.user_id
    transaction.on_commit(lambda: refund_card(cash_id, cents, user_id))
    return {'id': cash_id, 'refund_cents': cents}


def refund_card(cash_id: int, cents: int, acted_by: Optional[int]) -> None:
    """After the commit: ask the gateway to refund; record what it refunded; reverse."""
    from apps.transactions.models import Cash
    cash = Cash.objects.get(pk=cash_id)
    full = not _refunds(cash) and cents == _cents(cash.amount)
    try:
        result = _gateway().refund(cash.gateway_transaction_id, cents, full=full)
    except Exception as e:  # noqa: BLE001 — nothing refunded that we know of
        _note(cash_id, 'refund_failed', {'amount_cents': cents, 'message': str(e)})
        return
    txn = result.get('transaction', {})
    if not txn.get('succeeded'):
        _note(cash_id, 'refund_failed', {'amount_cents': cents,
                                         'message': txn.get('message', '')})
        return
    event_id = txn.get('token') or f'refund-{cash_id}-{timezone.now().timestamp()}'
    record_refund(cash_id, cents, event_id=event_id, acted_by=acted_by)
    try:
        reverse_refund(cash_id, event_id, acted_by=acted_by)
    except Exception as e:  # noqa: BLE001 — recorded; the next refund finishes it
        logger.exception('Cash %s: refund %s recorded, not yet reversed', cash_id, event_id)
        _note(cash_id, 'refund_reversal_pending', {'event_id': event_id,
                                                   'message': f'{type(e).__name__}: {e}'})


@transaction.atomic
def record_refund(cash_id: int, cents: int, *, event_id: str,
                  acted_by: Optional[int] = None) -> Optional[str]:
    """What the gateway refunded, kept first: from here the money is spent."""
    from apps.transactions.models import Cash
    from apps.transactions.services.cash.cash_pending import refresh_cash_available

    cash = Cash.objects.select_for_update().get(pk=cash_id)
    refunds = _refunds(cash)
    if any(r.get('event_id') == event_id for r in refunds):
        return None                                  # this refund is already recorded
    refunds.append({'event_id': event_id, 'amount_cents': cents, 'reversed': False,
                    'dt': timezone.now().isoformat(), 'by': acted_by})
    total = sum(int(r['amount_cents']) for r in refunds)
    cash.metadata = {**(cash.metadata or {}), 'refunds': refunds}
    cash.status = 'refunded' if total >= _cents(cash.amount) else 'partially_refunded'
    cash.add_audit_entry('gateway_refund', {'token': event_id, 'amount_cents': cents})
    cash.save()
    refresh_cash_available(cash)
    return cash.status


@transaction.atomic
def reverse_refund(cash_id: int, event_id: str, *, acted_by: Optional[int] = None) -> Decimal:
    """Take a recorded refund off the documents it was applied to. Money the Cash still
    held unapplied is refunded first; only the rest was on a document. Returns what was
    reversed."""
    from apps.transactions.models import Cash
    from apps.transactions.services.cash import cash_door
    from apps.transactions.services.cash.cash_pending import (_applied,
                                                              refresh_cash_available)
    from apps.transactions.services.cash.cash_pending_receipt import _applied as _applied_ap

    cash = Cash.objects.select_for_update().get(pk=cash_id)
    refunds = _refunds(cash)
    entry = next((r for r in refunds if r.get('event_id') == event_id), None)
    if entry is None or entry.get('reversed'):
        return Decimal('0')
    other = sum(int(r.get('amount_cents') or 0) for r in refunds
                if r is not entry) / Decimal(100)
    unapplied = (_d(cash.amount) - _applied(cash_id=cash.pk) + _applied_ap(cash_id=cash.pk)
                 - other)
    left = _d(entry['amount_cents']) / 100 - max(unapplied, Decimal('0'))
    reversed_total = Decimal('0')
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
        reversed_total += take
    if left > 0:
        raise cash_door.CashDoorError(
            f'refund {event_id} of cash {cash.pk}: {left} is neither unapplied nor on a '
            f'document — the cash was over-refunded')

    cash.refresh_from_db()
    refunds = _refunds(cash)
    for r in refunds:
        if r.get('event_id') == event_id:
            r['reversed'] = True
    cash.metadata = {**(cash.metadata or {}), 'refunds': refunds}
    cash.save(update_fields=['metadata', 'version', 'dt_modified'])
    refresh_cash_available(cash)
    return reversed_total


# ── receive: the gateway's webhook ────────────────────────────────────

def receive(ctx) -> Dict[str, Any]:
    """The one command the public actor reaches (plan §11.7d). The body is not trusted: the
    event is confirmed by asking the provider (Spreedly's show_transaction) before anything
    is looked up or recorded, so an unconfirmed token learns nothing."""
    provider = ctx.data.get('_provider') or ''
    if provider not in PROVIDERS:
        raise Refused(400, 'unknown_provider',
                      f'No payment provider {provider!r} is configured here.',
                      {'providers': list(PROVIDERS)})
    body = ctx.data.get('_body') or {}
    token = ((body.get('transaction') or {}).get('token') or '') if isinstance(body, dict) else ''
    if not token:
        raise Refused(400, 'no_transaction_token', 'The event names no transaction.')
    try:
        verified = _gateway().show_transaction(token).get('transaction', {})
    except Exception as e:  # noqa: BLE001 — the provider will retry; nothing was recorded
        raise Refused(502, 'verification_failed', 'Could not confirm the event.') from e

    from apps.transactions.models import Cash
    cash_id = Cash.objects.filter(gateway_transaction_id=token).values_list('pk', flat=True).first()
    order_ref = str(verified.get('order_id') or '')
    if cash_id is None and order_ref.startswith('wc3-') and order_ref[4:].isdigit():
        cash_id = Cash.objects.filter(pk=int(order_ref[4:]), gateway_transaction_id='') \
            .values_list('pk', flat=True).first()     # a charge whose answer never came
    if cash_id is None:
        return {'status': 'ok'}
    state = verified.get('state', '')
    verified = {**verified, 'token': token}
    if state == 'succeeded':
        record_outcome(cash_id, state='succeeded', txn=verified)
    elif state in ('failed', 'gateway_processing_failed'):
        record_outcome(cash_id, state=state, txn=verified)
    return {'status': 'ok'}


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('cash', 'pay', pay)
    register_command('cash', 'refund', refund)
    register_command('cash', 'receive', receive, needs_record=False, public=True)
