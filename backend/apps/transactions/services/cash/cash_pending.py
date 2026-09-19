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


def _create_discount_line(
    invoice, disc_value: Decimal, discount_pct: float, source_cash=None,
    decision: Optional[Dict[str, Any]] = None,
) -> None:
    """Create a negative invoice line for the discount amount.

    Discount reduces the invoice total (not a separate cash).
    The line has line_type='discount' and purpose='cash_discount'.
    After creating the line, recalculate invoice totals.
    """
    from apps.transactions.models import InvoiceLine

    # Find next line number
    last_line = (
        InvoiceLine.objects.filter(invoice_id=invoice.pk)
        .order_by('-line_number')
        .values_list('line_number', flat=True)
        .first()
    ) or 0
    next_line = (last_line // 10 + 1) * 10

    reason = f'{discount_pct}% cash discount' if discount_pct > 0 else 'Cash discount'

    InvoiceLine.objects.create(
        invoice_id=invoice.pk,
        line_number=next_line,
        line_type='discount',
        purpose='cash_discount',
        item={'name': reason, 'ida': SYS_DISCOUNT},
        quantity={'active': 1},
        price={
            'unit': float(-disc_value),
            'amount': float(-disc_value),
        },
        metadata={
            'discount_pct': discount_pct,
            'discount_amt': float(disc_value),
            'source_cash_id': source_cash.pk if source_cash else None,
            'decision': decision or {},
        },
    )

    # Recalculate invoice totals so balance reflects the discount
    invoice.update_sell_cost_totals(persist=True)
    invoice.refresh_from_db()

    logger.info("Created discount line on invoice %s: -$%s (%s)",
                invoice.pk, disc_value, reason)


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


ADJUSTMENT_METHODS = ('write_off', 'small_balance', 'fx_gain', 'fx_loss')


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
    """available = amount − Σ applied. Saving re-runs the cash ledger (signal)."""
    available = _d(cash.amount) - _applied(cash_id=cash.pk)
    if cash.available != available:
        cash.available = available
        cash.save(update_fields=['available', 'dt_modified', 'version'])
    return available


def _check_application(cash, invoice, amount: Decimal) -> None:
    """The numbers must balance; the user chooses how.

    - amount moves the invoice balance toward zero, never past it
    - cash available moves toward zero, never past it
    """
    if amount == 0:
        raise ValueError("amount must not be zero")
    balance = _d(invoice.totals.get('total')) - _applied(invoice_id=invoice.pk)
    if _sign(amount) != _sign(balance) or abs(amount) > abs(balance):
        raise ValueError(
            f"cannot apply {amount} to invoice {invoice.pk}: balance due is {balance}")
    available = _d(cash.amount) - _applied(cash_id=cash.pk)
    if _sign(amount) != _sign(available) or abs(amount) > abs(available):
        raise ValueError(
            f"cannot apply {amount} from cash {cash.pk}: available is {available}")
    # One customer's money does not pay another customer's invoice.
    cash_customer = getattr(cash, 'customer_id', None)
    if cash_customer and cash_customer != getattr(invoice, 'customer_id', None):
        raise ValueError(
            f"cannot apply cash {cash.pk} (customer {cash_customer}) to invoice {invoice.pk} "
            f"(customer {getattr(invoice, 'customer_id', None)}): the customers differ")


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

    Discount creates an invoice line (reduces invoice total).
    Dismiss creates a separate write-off cash with its own GL.

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

    # ── Discount — creates an invoice line that reduces the total ────
    disc_value = Decimal('0')
    if discount_amt > 0:
        disc_value = Decimal(str(discount_amt))
    elif discount_pct > 0:
        totals = invoice.totals or {}
        invoice_total = Decimal(str(totals.get('total', 0)))
        disc_value = (invoice_total * Decimal(str(discount_pct)) / 100).quantize(Decimal('0.01'))

    if disc_value > 0:
        _check_policy(invoice, 'discount', disc_value)
        _create_discount_line(invoice, disc_value, discount_pct, cash, decision)
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

            _check_application(cash, invoice, amount)

            changes['state'] = 'applied'
            changes['dt_applied'] = timezone.now().isoformat()
            pending.changes = changes
            pending.dt_processed = int(timezone.now().timestamp() * 1000)
            pending.save(update_fields=['changes', 'dt_processed', 'dt_modified', 'version'])

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
def unapply_cash_application(pending_id: int, reason: str = '') -> Dict[str, Any]:
    """Reverse an application. The record stays, marked canceled."""
    from apps.core.models.pending import Pending
    from apps.transactions.models import Invoice, Cash

    pending = Pending.objects.select_for_update().get(pk=pending_id, purpose=CASH_PURPOSE)
    changes = dict(pending.changes or {})
    if changes.get('state') == 'canceled':
        raise ValueError(f"application {pending_id} is already canceled")
    changes['state'] = 'canceled'
    changes['dt_canceled'] = timezone.now().isoformat()
    changes['cancel_reason'] = reason
    pending.changes = changes
    if not pending.dt_processed:
        pending.dt_processed = int(timezone.now().timestamp() * 1000)
    pending.save(update_fields=['changes', 'dt_processed', 'dt_modified', 'version'])

    invoice = Invoice.objects.filter(pk=changes.get('invoice_id')).first()
    cash = Cash.objects.filter(pk=changes.get('cash_id')).first()
    result = {'pending_id': pending.pk, 'state': 'canceled'}
    if invoice:
        result['invoice'] = refresh_invoice_cash(invoice)
    if cash:
        result['cash_available'] = float(refresh_cash_available(cash))
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
    """Record an applied application inside a transfer (both sides or neither)."""
    from apps.core.models.pending import Pending

    balance = _d(invoice.totals.get('total')) - _applied(invoice_id=invoice.pk)
    if _sign(amount) != _sign(balance) or abs(amount) > abs(balance):
        raise ValueError(f"cannot apply {amount} to invoice {invoice.pk}: balance due is {balance}")
    now = timezone.now()
    pending = Pending(
        model_name='cash', record_id=str(cash.pk), purpose=CASH_PURPOSE,
        name=f'Cash #{cash.pk} → Invoice #{invoice.pk} ${amount}',
        dt_processed=int(now.timestamp() * 1000),
        changes={'cash_id': cash.pk, 'invoice_id': invoice.pk, 'amount': float(amount),
                 'reason': reason, 'state': 'applied', 'dt_applied': now.isoformat()},
    )
    pending.save()
    refresh_invoice_cash(invoice)
    refresh_cash_available(cash)
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
