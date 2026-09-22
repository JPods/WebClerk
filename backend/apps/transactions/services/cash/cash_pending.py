"""Cash pending service — one-path cash application via Pending model.

Every cash application flows through a Pending record with
purpose='cash_application'. Same model as inventory pending,
different purpose. One Pending model, many purposes.

If the invoice is unlocked, Pending.try_apply() fires immediately.
If locked, stays queued (dt_processed=0) for celery.

changes JSON schema:
    {
        "cash_id": int,
        "invoice_id": int,
        "amount": float,
        "reason": str,
        "contact_id": int|null,
        "state": "pending"|"applied"|"canceled",
        "dt_applied": str|null,
    }
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

CASH_PURPOSE = 'cash_application'

# System item IDAs for cash adjustments
SYS_DISCOUNT = 'SYS-DISCOUNT'
SYS_WRITEOFF = 'SYS-WRITEOFF'
SYS_FXDIFF = 'SYS-FXDIFF'


def _create_adjustment_cash(
    invoice, method: str, amount: Decimal, reason: str = '',
    source_cash=None, decision: Optional[Dict[str, Any]] = None,
) -> None:
    """Create an adjustment Cash record and apply it to the invoice.

    Discount, write-off, and FX difference are cash-side events.
    The invoice total stays immutable. Each adjustment is a separate
    Cash record applied via the same Pending path as cash.
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Cash

    adj_cash = Cash.objects.create(
        amount=amount,
        available=amount,
        status='completed',
        method=method,
        reference_number=f'{method.upper()}-{invoice.pk}',
        customer_id=getattr(source_cash, 'customer_id', None) if source_cash else None,
        invoice=invoice,
        metadata={
            'type': method,
            'invoice_id': invoice.pk,
            'source_cash_id': source_cash.pk if source_cash else None,
            'reason': reason,
            'decision': decision or {},
        },
    )

    # Apply via Pending — same path as cash
    Pending.objects.create(
        model_name='cash',
        record_id=str(adj_cash.pk),
        name=f'{method.title()} #{adj_cash.pk} → Invoice #{invoice.pk} ${amount}',
        purpose=CASH_PURPOSE,
        changes={
            'cash_id': adj_cash.pk,
            'invoice_id': invoice.pk,
            'amount': float(amount),
            'reason': reason,
            'state': 'pending',
            # An adjustment (write-off, small balance, FX) is not money received.
            'kind': method,
        },
    )

    logger.info("Created %s cash #%s → invoice %s: $%s (%s)",
                method, adj_cash.pk, invoice.pk, amount, reason)


# ── Balances: one rule ───────────────────────────────────────────────
# invoice received  = Σ applied cash_application amounts for the invoice
# invoice balance   = total − received
# cash available    = amount − Σ applied amounts from that cash
# Nothing increments; everything is recomputed from the application records.

def _d(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _sign(value: Decimal) -> int:
    return (value > 0) - (value < 0)


def _applied(**match) -> Decimal:
    from django.db.models import DecimalField, Sum
    from django.db.models.fields.json import KeyTextTransform
    from django.db.models.functions import Cast
    from apps.core.models.pending import Pending

    filters = {f'changes__{k}': v for k, v in match.items()}
    total = (
        Pending.objects.filter(purpose=CASH_PURPOSE, changes__state='applied', **filters)
        .annotate(amt=Cast(KeyTextTransform('amount', 'changes'), DecimalField(max_digits=14, decimal_places=2)))
        .aggregate(s=Sum('amt'))['s']
    )
    return _d(total)


def _committed(**match) -> Decimal:
    """Applied **plus queued** — what the cash is already spoken for at creation time.

    ``_applied`` answers what has moved. A check at creation has to count what is about to
    move as well: two queued applications of the same cash each passed alone, and together
    they spent it twice (Fable, 2026-09-21). The appliers no longer check at all (Rule 10),
    so this is the only place it is asked.
    """
    from apps.core.models.pending import Pending

    filters = {f'changes__{k}': v for k, v in match.items()}
    queued = Decimal('0')
    for p in Pending.objects.filter(purpose=CASH_PURPOSE, dt_processed=0,
                                    changes__state='pending', **filters).only('changes'):
        queued += _d((p.changes or {}).get('amount'))
    return _applied(**match) + queued


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _check_policy(invoice, kind: str, value: Decimal) -> None:
    """The company's policy for adjustments, if it has one (company profile
    config.cash_policy): {discount_limit, discount_limit_pct, write_off_limit,
    write_off_limit_pct}. No policy = the user decides."""
    from apps.core.models import Setting
    company = Setting.objects.filter(purpose='wc:company_profile').only('config').first()
    policy = ((company.config or {}).get('cash_policy') or {}) if company else {}
    total = _d((invoice.totals or {}).get('total'))
    limit = policy.get(f'{kind}_limit')
    if limit not in (None, '') and value > _d(limit):
        raise ValueError(f"Company policy: a {kind.replace('_', ' ')} may not exceed {_d(limit)} (asked {value})")
    pct = policy.get(f'{kind}_limit_pct')
    if pct not in (None, '') and total and value > (total * _d(pct) / 100).quantize(Decimal('0.01')):
        raise ValueError(f"Company policy: a {kind.replace('_', ' ')} may not exceed {pct}% of the invoice (asked {value} of {total})")


# A settlement adjustment settles the balance without money: it is a cash-side event,
# and the invoice total keeps meaning what was sold. 'discount' joined them 2026-09-22
# (Bill): it used to write a negative invoice line, which changed the total — impossible
# on a journalized invoice, which is exactly when a settlement discount is taken.
ADJUSTMENT_METHODS = ('write_off', 'small_balance', 'fx_gain', 'fx_loss', 'discount')


def _applied_split(**match):
    """(money received, adjustments) applied — both settle the balance, only one is cash."""
    from apps.core.models.pending import Pending
    total = _applied(**match)
    filters = {f'changes__{k}': v for k, v in match.items()}
    adjusted = Decimal('0')
    for p in Pending.objects.filter(purpose=CASH_PURPOSE, changes__state='applied',
                                    changes__kind__in=ADJUSTMENT_METHODS, **filters).only('changes'):
        adjusted += _d((p.changes or {}).get('amount'))
    return total - adjusted, adjusted



def record_application_event(document, pending, changes, cash=None) -> None:
    """Append the application to the document it settled.

    The ledger says how deep the water is; this says how it got there (Bill, 2026-09-20).
    The pending's uuid is the event id, so an apply that runs twice records once.

    Called inside the apply's atomic block, with the document already locked, so the
    money and the record of it land together.
    """
    from datetime import datetime, timezone as _tz

    if document is None or not hasattr(document, 'events'):
        return
    event_id = str(getattr(pending, 'uuid', '') or pending.pk)
    events = list(document.events or [])
    if any(isinstance(e, dict) and e.get('id') == event_id for e in events):
        return

    kind = (changes or {}).get('kind') or 'cash_application'
    events.append({
        'id': event_id,
        'kind': 'adjustment' if kind in ADJUSTMENT_METHODS else 'cash_application',
        'method': kind,
        'dt': int(datetime.now(_tz.utc).timestamp() * 1000),
        'by': (changes or {}).get('acted_by') or '',
        'amount': float(_d((changes or {}).get('amount'))),
        'cash_id': (changes or {}).get('cash_id'),
        'cash_ida': getattr(cash, 'ida', None) if cash is not None else None,
        'reason': (changes or {}).get('reason') or '',
        'pending_id': pending.pk,
    })
    document.events = events
    document.save(update_fields=['events', 'dt_modified', 'version'])

def cash_state(total: Decimal, received: Decimal) -> str:
    """open | partial | paid | credit | over — derived, never typed.

    over: applied cash exceeds the total (e.g. lines removed after cash was
    applied). The numbers no longer balance; Alice flags it for the user.
    """
    total, received = _d(total), _d(received)
    if total == received:
        return 'paid'
    if received == 0:
        return 'credit' if total < 0 else 'open'
    if _sign(received) != _sign(total) or abs(received) > abs(total):
        return 'over'
    return 'partial'


def refresh_invoice_cash(invoice) -> Dict[str, Any]:
    """Recompute received/balance/cash_state from applications, then ledgers and org."""
    from apps.transactions.services.pricing.totals_compute import update_received
    from apps.accounts.services.terms_ledger import allocate_received

    received, adjusted = _applied_split(invoice_id=invoice.pk)
    result = update_received(invoice, received, adjusted)
    allocate_received(invoice)
    return result


def refresh_cash_available(cash) -> Decimal:
    """What this cash still has to give, counting both sides of the house.

    **One function** (2026-09-22). There were two, with different formulas: this one
    ignored AP applications entirely, so a cash that had paid a vendor still reported the
    money as available. Both reviewers found it independently in the recheck-3 audit.

    An application carries its *document's* sign. On AR the invoice points the same way as
    the cash, so an application is subtracted. On AP they are opposed — a payable is stored
    positive and the payment out that settles it is negative — so an AP application is
    **added**, and available moves toward zero on both sides.
    """
    from apps.transactions.services.cash.cash_pending_receipt import _applied as _applied_ap

    available = _d(cash.amount) - _applied(cash_id=cash.pk) + _applied_ap(cash_id=cash.pk)
    if _d(cash.available) != available:
        cash.available = available
        cash.save(update_fields=['available', 'dt_modified', 'version'])
    return available


def _check_application(cash, target, amount: Decimal, *,
                       target_applied: Optional[Decimal] = None,
                       cash_applied: Optional[Decimal] = None,
                       bound_cash: bool = True,
                       party_attr: str = 'customer_id',
                       party_label: str = 'customer') -> None:
    """What must be true for an application to be recorded. One check, both sides.

    **Balance, not buckets** — Bill, 2026-09-20: *"We care that things balance, not that
    they are in the perfect bucket."* The user decides how to apply their money. The only
    arithmetic limit is that they cannot apply money that does not exist, so the bound is
    on the **running total**, never on the sign of any single application. A negative
    application that unwinds part of an earlier one still balances, and is allowed; so is
    an odd split across documents. Neither is ours to refuse.

    This replaced a per-amount sign mandate, and on the AP side a flat "amount must be
    positive" that made a legitimate correction impossible to record.

    What is still refused, and why:

    - **zero** — there is nothing to record.
    - **a total beyond the document, or beyond the cash.** Past that point the books stop
      balancing: money is being applied that was never received.
    - **one party's money against another party's document.** Not a balance rule — it
      balances fine — but the relationship it publishes. WebClerk's promise is that each
      customer sees the details of *their* relationship; applying across parties puts
      someone else's paid invoice on their statement. A genuine shift between sister
      divisions listed as separate customers is documented as a negative application on
      one and a positive on the other, which balances and leaves both statements honest
      (Bill, 2026-09-20). That path exists only because the positive-amount mandate is gone.

    ``target`` is an invoice (AR) or a receipt (AP). Callers pass the sums, because what
    counts as applied to a cash differs by side: an AP payment's cash may also carry AR
    applications, and both spend it.

    The amount carries the **document's** sign — the convention the AP path has always
    had: a +100 payable takes a +60 application even though the -60 payment that settles it
    is negative, and ``paid``/``balance`` are derived from those applications. The document
    therefore carries the sign check and the cash bounds magnitude only.
    """
    if amount == 0:
        raise ValueError("amount must not be zero: there is nothing to record")

    # Applied **and queued**: this check runs at creation, and a queued application is
    # money already spoken for. The appliers do not re-check (Rule 10).
    if target_applied is None:
        target_applied = _committed(invoice_id=target.pk)
    if cash_applied is None:
        cash_applied = _committed(cash_id=cash.pk)

    kind = target._meta.model_name

    # The document carries the sign. An application is in its document's convention — a
    # +100 invoice takes +60, a -40 credit memo takes -40 (which is why a *positive* cash
    # cannot settle a credit memo), and a +100 payable takes +60 even though the payment
    # out that settles it is negative.
    total = _d((target.totals or {}).get('total'))
    after = _d(target_applied) + amount
    if (_sign(after) not in (0, _sign(total))) or abs(after) > abs(total):
        raise ValueError(
            f"cannot apply {amount} to {kind} {target.pk}: that would put {after} against "
            f"a {kind} of {total}. {total - _d(target_applied)} of it is still open.")

    # The cash bounds magnitude only, because on AP it points the other way: a -60.00
    # payment can give 60.00 to a payable and no more. Requiring its sign here would
    # forbid every AP application there is.
    cash_amount = _d(cash.amount)
    cash_after = _d(cash_applied) + amount
    # A credit transfer carries no money of its own (amount 0) and its two legs net to
    # zero, so there is no cash to bound — only the two documents.
    if bound_cash and abs(cash_after) > abs(cash_amount):
        raise ValueError(
            f"cannot apply {amount} from cash {cash.pk}: that would put {abs(cash_after)} "
            f"against a payment of {abs(cash_amount)}. "
            f"{abs(cash_amount) - abs(_d(cash_applied))} of it is still unapplied.")

    party = getattr(cash, party_attr, None)
    target_party = getattr(target, party_attr, None)
    if party and party != target_party:
        raise ValueError(
            f"cannot apply cash {cash.pk} ({party_label} {party}) to {kind} {target.pk} "
            f"({party_label} {target_party}): the {party_label}s differ. To move money "
            f"between them, record a negative application on one and a positive on the "
            f"other — the books balance and each statement stays its own.")


@transaction.atomic
def apply_cash_to_invoice(
    cash_id: int,
    invoice_id: int,
    amount,
    reason: str = '',
    contact_id: Optional[int] = None,
    discount_pct: float = 0,
    discount_amt: float = 0,
    dismiss_balance: bool = False,
    fx_difference: float = 0,
    acted_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a Pending record for cash application.

    Amounts are signed: a positive amount pays an invoice, a negative amount
    settles a credit memo (refund cash is negative). If the invoice is not
    locked, applies immediately; if locked, queues for celery.

    A discount, a write-off, a dismissed balance and an FX difference are all cash-side
    adjustments: each is its own Cash record applied through this same Pending path, and
    the invoice total stays what was sold.

    Returns:
        {pending_id, state, amount, applied, adjustments}
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Invoice, Cash

    cash = Cash.objects.select_for_update().get(pk=cash_id)
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    amount = _d(amount)

    # Bill (2026-09-19): an adjustment — a discount, a write-off, a dismissed balance,
    # an FX difference — is never automatic. It is a positive action by a user,
    # recorded as theirs, within the company's policy.
    wants_adjustment = discount_amt > 0 or discount_pct > 0 or dismiss_balance or fx_difference != 0
    if wants_adjustment and not acted_by:
        raise ValueError("An adjustment (discount, write-off, dismissed balance, FX) is a user's "
                         "decision: it needs the signed-in user who made it.")
    decision = {'decided_by_user_id': acted_by, 'dt_decided': _utc_now_iso()} if wants_adjustment else None

    adjustments = []

    # ── Discount — an adjustment cash that settles part of the balance ──
    disc_value = Decimal('0')
    if discount_amt > 0:
        disc_value = Decimal(str(discount_amt))
    elif discount_pct > 0:
        totals = invoice.totals or {}
        invoice_total = Decimal(str(totals.get('total', 0)))
        disc_value = (invoice_total * Decimal(str(discount_pct)) / 100).quantize(Decimal('0.01'))

    if disc_value > 0:
        _check_policy(invoice, 'discount', disc_value)
        _create_adjustment_cash(
            invoice, 'discount', disc_value,
            reason=(f'{discount_pct}% cash discount' if discount_pct > 0 else 'Cash discount'),
            source_cash=cash, decision=decision,
        )
        adjustments.append({'type': 'discount', 'amount': float(disc_value)})

    # ── FX difference (cash-side) ────────────────────────────────
    if fx_difference != 0:
        fx_amt = abs(Decimal(str(fx_difference)))
        method = 'fx_gain' if fx_difference > 0 else 'fx_loss'
        _create_adjustment_cash(
            invoice, method, fx_amt,
            reason='Currency exchange difference',
            source_cash=cash, decision=decision,
        )
        adjustments.append({'type': method, 'amount': float(fx_amt)})

    _check_application(cash, invoice, amount)

    changes = {
        'cash_id': cash_id,
        'invoice_id': invoice_id,
        'amount': float(amount),
        'reason': reason,
        'contact_id': contact_id,
        'state': 'pending',
        'dt_applied': None,
    }

    # Creating the Pending record triggers try_apply() on save
    pending = Pending.objects.create(
        model_name='cash',
        record_id=str(cash_id),
        name=f'Cash #{cash_id} → Invoice #{invoice_id} ${amount}',
        purpose=CASH_PURPOSE,
        changes=changes,
    )

    applied = pending.is_processed()

    # ── Dismiss remaining balance ───────────────────────────────────
    if dismiss_balance and applied:
        invoice.refresh_from_db()
        remaining = Decimal(str((invoice.totals or {}).get('balance', 0)))
        if remaining > 0:
            _check_policy(invoice, 'write_off', remaining)
            _create_adjustment_cash(
                invoice, 'small_balance', remaining,
                reason=reason or 'Balance dismissed by user',
                source_cash=cash, decision=decision,
            )
            adjustments.append({'type': 'write_off', 'amount': float(remaining)})

    result = {
        'pending_id': pending.pk,
        'state': 'applied' if applied else 'pending',
        'amount': float(amount),
        'applied': applied,
    }
    if adjustments:
        result['adjustments'] = adjustments
    return result


def apply_cash_pending(pending) -> bool:
    """Apply one cash application Pending record. Called from Pending.try_apply().

    Returns True on success, False if queued for celery.
    """
    from django.db import OperationalError
    from apps.transactions.models import Invoice, Cash

    changes = pending.changes if isinstance(pending.changes, dict) else {}
    cash_id = changes.get('cash_id')
    invoice_id = changes.get('invoice_id')
    amount = _d(changes.get('amount'))

    if not cash_id or not invoice_id or not amount:
        logger.warning("Pending %s: missing cash_id/invoice_id/amount", pending.pk)
        return False

    if pending.is_processed() or (changes or {}).get('state') == 'applied':
        return True                     # already applied — a retry records nothing twice

    try:
        with transaction.atomic():
            try:
                cash = Cash.objects.select_for_update(nowait=True).get(pk=cash_id)
                invoice = Invoice.objects.select_for_update(nowait=True).get(pk=invoice_id)
            except (Cash.DoesNotExist, Invoice.DoesNotExist) as e:
                logger.warning("Pending %s: record not found: %s", pending.pk, e)
                return False

            # A journalized invoice is locked against content edits, not against cash:
            # received/balance/cash_state are derived from applications.
            #
            # **Rule 10 (Bill, 2026-09-21): a Pending's sole purpose is to apply**, "regardless
            # of common sense". The check belongs at creation, where a person can still be
            # coached; here it only stranded records that the books had already counted on.
            # A value that ends up strange surfaces as cash_state 'over' for Alice and the user.

            changes['state'] = 'applied'
            changes['dt_applied'] = timezone.now().isoformat()
            pending.changes = changes
            pending.dt_processed = int(timezone.now().timestamp() * 1000)
            pending.save(update_fields=['changes', 'dt_processed', 'dt_modified', 'version'])

            record_application_event(invoice, pending, changes, cash)
            refresh_invoice_cash(invoice)
            available = refresh_cash_available(cash)

            logger.info(
                "Applied cash pending %s: cash %s → invoice %s, $%s (available now $%s)",
                pending.pk, cash.pk, invoice.pk, amount, available,
            )
            return True

    except OperationalError:
        logger.debug("Pending %s: record locked, queued for celery", pending.pk)
        return False


@transaction.atomic
def unapply_cash_application(pending_id: int, reason: str = '', acted_by=None) -> Dict[str, Any]:
    """Undo an application by **writing a reversing application**, never by editing it.

    Bill, 2026-09-22: every apply, change, unapply and delete writes a new signed Pending.
    This used to set ``state='canceled'`` on the original, which made the record say
    something other than what happened: the money had moved, and the row denied it.

    An application that never applied is a different thing: nothing moved, so it is closed
    with its reason instead (``cash_door.close_queued``).

    Works for both sides — AP had no unapply at all.
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Cash, Invoice, Receipt
    from apps.transactions.services.cash import cash_door

    pending = (Pending.objects.select_for_update()
               .get(pk=pending_id, purpose__in=cash_door.CASH_PURPOSES))
    changes = pending.changes if isinstance(pending.changes, dict) else {}

    if (changes.get('kind') or '') in ADJUSTMENT_METHODS:
        raise ValueError(
            f"application {pending_id} is a {changes['kind']} adjustment, not money received. "
            f"To undo it, delete the adjustment cash record — that reverses it through the "
            f"same door and leaves the trail.")

    if changes.get('state') != 'applied':
        cash_door.close_queued(pending, reason or 'canceled', acted_by=acted_by)
        return {'pending_id': pending.pk, 'state': 'canceled', 'reversal_id': None}

    reversal = cash_door.reverse_application(pending, reason or 'unapplied', acted_by=acted_by)
    if reversal is None:
        raise ValueError(
            f"application {pending_id} has already been fully reversed; there is nothing "
            f"left to unapply.")

    from apps.core.services.balance_checker import log_balance_event
    log_balance_event(reversal, True, event='unapply')

    target_key = cash_door._target_key(pending.purpose)
    result = {'pending_id': pending.pk, 'state': 'reversed',
              'reversal_id': reversal.pk,
              'amount': reversal.changes['amount']}
    cash = Cash.objects.filter(pk=changes.get('cash_id')).first()
    if cash:
        result['cash_available'] = float(refresh_cash_available(cash))
    if target_key == 'invoice_id':
        invoice = Invoice.objects.filter(pk=changes.get('invoice_id')).first()
        if invoice:
            result['invoice'] = refresh_invoice_cash(invoice)
    else:
        receipt = Receipt.objects.filter(pk=changes.get('receipt_id')).first()
        if receipt:
            from apps.transactions.services.cash.cash_pending_receipt import refresh_receipt_paid
            result['receipt'] = refresh_receipt_paid(receipt)
    return result


@transaction.atomic
def transfer_credit(credit_invoice_id: int, invoice_id: int, amount, reason: str = '') -> Dict[str, Any]:
    """Use a credit memo's credit on another invoice of the same customer.

    A non-bank cash record (method credit_transfer, amount 0) carries two
    applications: −amount to the credit memo, +amount to the invoice.
    """
    from apps.transactions.models import Invoice, Cash

    amount = abs(_d(amount))
    memo = Invoice.objects.select_for_update().get(pk=credit_invoice_id)
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    if memo.customer_id != invoice.customer_id:
        raise ValueError("credit can only move between invoices of the same customer")

    transfer = Cash.objects.create(
        amount=Decimal('0'), available=Decimal('0'), status='completed',
        method='credit_transfer', customer_id=memo.customer_id,
        reference_number=f'CREDIT-{memo.pk}-{invoice.pk}',
        metadata={'type': 'credit_transfer', 'reason': reason,
                  'credit_invoice_id': memo.pk, 'invoice_id': invoice.pk},
    )
    out = _apply_now(transfer, memo, -amount, reason)
    into = _apply_now(transfer, invoice, amount, reason)
    return {'cash_id': transfer.pk, 'applications': [out, into]}


def _apply_now(cash, invoice, amount: Decimal, reason: str) -> int:
    """One leg of a transfer, applied through the same door as everything else.

    This used to write a Pending already marked ``applied``, which is the one thing no
    caller may do: it is the applier's word that the money moved. Now it creates the
    application and lets ``try_apply`` do it, inside the transfer's transaction — the rows
    are already locked by this transaction, so the applier's ``nowait`` lock is free. If a
    leg does not apply, this raises and both legs roll back.
    """
    from apps.core.models.pending import Pending

    # The document bound, as everywhere else. The cash bound is skipped: a credit transfer
    # carries amount 0 and its two legs net to zero by construction.
    _check_application(cash, invoice, amount, bound_cash=False)

    pending = Pending.objects.create(
        model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
        name=f'Cash #{cash.pk} → Invoice #{invoice.pk} ${amount}',
        changes={'cash_id': cash.pk, 'invoice_id': invoice.pk, 'amount': float(amount),
                 'reason': reason, 'kind': 'credit_transfer',
                 'state': 'pending', 'dt_applied': None},
    )
    pending.refresh_from_db()
    if not pending.is_processed():
        raise ValueError(
            f"the credit transfer to invoice {invoice.pk} could not be applied, so none of "
            f"it was. The invoice or the credit memo is locked by another write; try again.")
    return pending.pk


@transaction.atomic
def apply_pending_for_invoice(invoice_id: int) -> Dict[str, Any]:
    """Apply all pending cash records for an invoice after unlock.

    Returns:
        {applied_count, still_pending}
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Invoice

    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)

    pendings = (
        Pending.objects
        .filter(purpose=CASH_PURPOSE, dt_processed=0)
        .filter(changes__invoice_id=invoice_id)
        .select_for_update()
        .order_by('dt_created')
    )

    applied_count = 0
    for p in pendings:
        if apply_cash_pending(p):
            applied_count += 1
            invoice.refresh_from_db()

    still_pending = (
        Pending.objects
        .filter(purpose=CASH_PURPOSE, dt_processed=0)
        .filter(changes__invoice_id=invoice_id)
        .count()
    )

    return {
        'applied_count': applied_count,
        'still_pending': still_pending,
    }


def get_pending_for_invoice(invoice_id: int) -> Dict[str, Any]:
    """Return all cash pending records for an invoice.

    Returns:
        {invoice_id, pending: [{id, cash_id, amount, state, reason, dt_created}]}
    """
    from apps.core.models.pending import Pending

    rows = (
        Pending.objects
        .filter(purpose=CASH_PURPOSE)
        .filter(changes__invoice_id=invoice_id)
        .order_by('-dt_created')
        .values('id', 'changes', 'dt_created', 'dt_processed')
    )

    return {
        'invoice_id': invoice_id,
        'pending': [
            {
                'id': r['id'],
                'cash_id': r['changes'].get('cash_id'),
                'amount': r['changes'].get('amount'),
                'state': r['changes'].get('state', 'pending'),
                'reason': r['changes'].get('reason', ''),
                'dt_created': r['dt_created'],
                'dt_processed': r['dt_processed'],
            }
            for r in rows
        ],
    }


__all__ = [
    'apply_cash_to_invoice',
    'apply_cash_pending',
    'unapply_cash_application',
    'transfer_credit',
    'refresh_invoice_cash',
    'refresh_cash_available',
    'cash_state',
    'apply_pending_for_invoice',
    'get_pending_for_invoice',
    'CASH_PURPOSE',
]
