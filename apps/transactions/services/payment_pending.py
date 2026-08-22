"""Payment pending service — one-path payment application via Pending model.

Every payment application flows through a Pending record with
purpose='payment_application'. Same model as inventory pending,
different purpose. One Pending model, many purposes.

If the invoice is unlocked, Pending.try_apply() fires immediately.
If locked, stays queued (dt_processed=0) for celery.

changes JSON schema:
    {
        "payment_id": int,
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

PAYMENT_PURPOSE = 'payment_application'

# System item IDAs for payment adjustments
SYS_DISCOUNT = 'SYS-DISCOUNT'
SYS_WRITEOFF = 'SYS-WRITEOFF'
SYS_FXDIFF = 'SYS-FXDIFF'


def _create_adjustment_payment(
    invoice, method: str, amount: Decimal, reason: str = '',
    source_payment=None,
) -> None:
    """Create an adjustment Payment record and apply it to the invoice.

    Discount, write-off, and FX difference are payment-side events.
    The invoice total stays immutable. Each adjustment is a separate
    Payment record applied via the same Pending path as cash payments.
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Payment

    adj_payment = Payment.objects.create(
        amount=amount,
        available=amount,
        status='completed',
        method=method,
        reference_number=f'{method.upper()}-{invoice.pk}',
        customer_id=getattr(source_payment, 'customer_id', None) if source_payment else None,
        invoice=invoice,
        metadata={
            'type': method,
            'invoice_id': invoice.pk,
            'source_payment_id': source_payment.pk if source_payment else None,
            'reason': reason,
        },
    )

    # Apply via Pending — same path as cash payments
    Pending.objects.create(
        model_name='payment',
        record_id=str(adj_payment.pk),
        name=f'{method.title()} #{adj_payment.pk} → Invoice #{invoice.pk} ${amount}',
        purpose=PAYMENT_PURPOSE,
        changes={
            'payment_id': adj_payment.pk,
            'invoice_id': invoice.pk,
            'amount': float(amount),
            'reason': reason,
            'state': 'pending',
        },
    )

    logger.info("Created %s payment #%s → invoice %s: $%s (%s)",
                method, adj_payment.pk, invoice.pk, amount, reason)


@transaction.atomic
def apply_payment_to_invoice(
    payment_id: int,
    invoice_id: int,
    amount,
    reason: str = '',
    contact_id: Optional[int] = None,
    discount_pct: float = 0,
    dismiss_balance: bool = False,
    fx_difference: float = 0,
) -> Dict[str, Any]:
    """Create a Pending record for payment application.

    If the invoice is not locked, applies immediately (reduce invoice balance,
    update payment). If locked, queues for celery.

    Adjustments (discount, dismiss, fx) add SYS-* lines to the invoice
    before applying the payment. The lines reduce the invoice total through
    normal totals recalculation.

    Returns:
        {pending_id, state, amount, applied, adjustments}
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Invoice, Payment

    payment = Payment.objects.select_for_update().get(pk=payment_id)
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValueError("amount must be positive")

    adjustments = []

    # ── Discount (payment-side — separate Payment record) ─────────
    if discount_pct > 0:
        totals = invoice.totals or {}
        invoice_total = Decimal(str(totals.get('total') or invoice.total or 0))
        discount_amt = (invoice_total * Decimal(str(discount_pct)) / 100).quantize(Decimal('0.01'))
        _create_adjustment_payment(
            invoice, 'discount', discount_amt,
            reason=f'{discount_pct}% payment discount',
            source_payment=payment,
        )
        adjustments.append({'type': 'discount', 'amount': float(discount_amt)})

    # ── FX difference (payment-side) ────────────────────────────────
    if fx_difference != 0:
        fx_amt = abs(Decimal(str(fx_difference)))
        method = 'fx_gain' if fx_difference > 0 else 'fx_loss'
        _create_adjustment_payment(
            invoice, method, fx_amt,
            reason='Currency exchange difference',
            source_payment=payment,
        )
        adjustments.append({'type': method, 'amount': float(fx_amt)})

    # ── Dismiss balance (after payment applied) ─────────────────────
    # Handled after the payment is applied — see below

    changes = {
        'payment_id': payment_id,
        'invoice_id': invoice_id,
        'amount': float(amount),
        'reason': reason,
        'contact_id': contact_id,
        'state': 'pending',
        'dt_applied': None,
    }

    # Creating the Pending record triggers try_apply() on save
    pending = Pending.objects.create(
        model_name='payment',
        record_id=str(payment_id),
        name=f'Payment #{payment_id} → Invoice #{invoice_id} ${amount}',
        purpose=PAYMENT_PURPOSE,
        changes=changes,
    )

    applied = pending.is_processed()

    # ── Dismiss remaining balance ───────────────────────────────────
    if dismiss_balance and applied:
        invoice.refresh_from_db()
        remaining = Decimal(str((invoice.totals or {}).get('balance') or invoice.balance or 0))
        if remaining > 0:
            _create_adjustment_payment(
                invoice, 'write_off', remaining,
                reason='Balance dismissed — too small to chase',
                source_payment=payment,
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


def apply_payment_pending(pending) -> bool:
    """Apply a single payment Pending record. Called from Pending.try_apply().

    Returns True on success, False if queued for celery.
    """
    from django.db import OperationalError
    from apps.transactions.models import Invoice, Payment

    changes = pending.changes if isinstance(pending.changes, dict) else {}
    payment_id = changes.get('payment_id')
    invoice_id = changes.get('invoice_id')
    amount_val = changes.get('amount', 0)

    if not payment_id or not invoice_id or not amount_val:
        logger.warning("Pending %s: missing payment_id/invoice_id/amount", pending.pk)
        return False

    amount = Decimal(str(amount_val))

    try:
        with transaction.atomic():
            try:
                payment = Payment.objects.select_for_update(nowait=True).get(pk=payment_id)
                invoice = Invoice.objects.select_for_update(nowait=True).get(pk=invoice_id)
            except (Payment.DoesNotExist, Invoice.DoesNotExist) as e:
                logger.warning("Pending %s: record not found: %s", pending.pk, e)
                return False

            # Don't apply to locked invoices
            if getattr(invoice, 'is_locked', False):
                return False

            # ── Update invoice totals ───────────────────────────────
            totals = invoice.totals or {}
            total_due = Decimal(str(totals.get('total') or 0))
            received = Decimal(str(totals.get('received') or 0))
            new_received = received + amount
            new_balance = total_due - new_received

            totals['received'] = float(new_received)
            totals['balance'] = float(new_balance)
            invoice.totals = totals
            invoice.balance = new_balance

            if new_balance <= 0:
                invoice.status = 'paid'
            elif new_received > 0:
                invoice.status = 'partially_paid'

            invoice.save(update_fields=['totals', 'balance', 'status', 'dt_modified', 'version'])

            # ── Decrement payment.available ─────────────────────────
            payment.available = max(Decimal('0'), payment.available - amount)
            payment.save(update_fields=['available', 'dt_modified', 'version'])

            # ── Mark pending as processed ───────────────────────────
            changes['state'] = 'applied'
            changes['dt_applied'] = timezone.now().isoformat()
            pending.changes = changes
            pending.dt_processed = int(timezone.now().timestamp() * 1000)
            pending.save(update_fields=['changes', 'dt_processed', 'dt_modified', 'version'])

            logger.info(
                "Applied payment pending %s: payment %s → invoice %s, $%s (available now $%s)",
                pending.pk, payment.pk, invoice.pk, amount, payment.available,
            )
            return True

    except OperationalError:
        logger.debug("Pending %s: record locked, queued for celery", pending.pk)
        return False


@transaction.atomic
def apply_pending_for_invoice(invoice_id: int) -> Dict[str, Any]:
    """Apply all pending payment records for an invoice after unlock.

    Returns:
        {applied_count, still_pending}
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Invoice

    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)

    if getattr(invoice, 'is_locked', False):
        return {'applied_count': 0, 'still_pending': 0, 'message': 'Invoice still locked'}

    pendings = (
        Pending.objects
        .filter(purpose=PAYMENT_PURPOSE, dt_processed=0)
        .filter(changes__invoice_id=invoice_id)
        .select_for_update()
        .order_by('dt_created')
    )

    applied_count = 0
    for p in pendings:
        if apply_payment_pending(p):
            applied_count += 1
            invoice.refresh_from_db()

    still_pending = (
        Pending.objects
        .filter(purpose=PAYMENT_PURPOSE, dt_processed=0)
        .filter(changes__invoice_id=invoice_id)
        .count()
    )

    return {
        'applied_count': applied_count,
        'still_pending': still_pending,
    }


def get_pending_for_invoice(invoice_id: int) -> Dict[str, Any]:
    """Return all payment pending records for an invoice.

    Returns:
        {invoice_id, pending: [{id, payment_id, amount, state, reason, dt_created}]}
    """
    from apps.core.models.pending import Pending

    rows = (
        Pending.objects
        .filter(purpose=PAYMENT_PURPOSE)
        .filter(changes__invoice_id=invoice_id)
        .order_by('-dt_created')
        .values('id', 'changes', 'dt_created', 'dt_processed')
    )

    return {
        'invoice_id': invoice_id,
        'pending': [
            {
                'id': r['id'],
                'payment_id': r['changes'].get('payment_id'),
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
    'apply_payment_to_invoice',
    'apply_payment_pending',
    'apply_pending_for_invoice',
    'get_pending_for_invoice',
    'PAYMENT_PURPOSE',
]
