"""Payment pending service — one-path payment application.

Every payment application flows through PendingPaymentApplication first.
If the invoice is unlocked, apply immediately. If locked, queue for later.
One path, one audit trail.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@transaction.atomic
def apply_payment_to_invoice(
    payment_id: int,
    invoice_id: int,
    amount,
    reason: str = '',
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a PendingPaymentApplication.

    If the invoice is not locked, apply immediately (reduce invoice balance,
    update payment). If locked, queue as pending.

    Returns:
        {pending_id, state, amount, applied}
    """
    from apps.transactions.models import Invoice, Payment
    from apps.transactions.models.pending_payment import PendingPaymentApplication

    payment = Payment.objects.select_for_update().get(pk=payment_id)
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValueError("amount must be positive")

    # Build request_ref for audit trail
    request_ref: Dict[str, Any] = {}
    if contact_id:
        request_ref['contact_id'] = contact_id

    pending = PendingPaymentApplication.objects.create(
        payment=payment,
        invoice=invoice,
        amount=amount,
        state=PendingPaymentApplication.STATE_PENDING,
        reason=reason,
        request_ref=request_ref,
    )

    applied = False
    if not getattr(invoice, 'is_locked', False):
        applied = _apply_one(pending, invoice, payment)

    return {
        'pending_id': pending.pk,
        'state': pending.state,
        'amount': float(pending.amount),
        'applied': applied,
    }


def _apply_one(
    pending,
    invoice=None,
    payment=None,
) -> bool:
    """Apply a single pending payment application. Returns True on success."""
    from apps.transactions.models import Invoice, Payment
    from apps.transactions.models.pending_payment import PendingPaymentApplication

    if pending.state != PendingPaymentApplication.STATE_PENDING:
        return False

    if invoice is None:
        invoice = Invoice.objects.select_for_update().get(pk=pending.invoice_id)
    if payment is None:
        payment = Payment.objects.select_for_update().get(pk=pending.payment_id)

    # Don't apply to locked invoices
    if getattr(invoice, 'is_locked', False):
        return False

    amount = pending.amount

    # Update invoice totals
    totals = invoice.totals or {}
    total_due = Decimal(str(totals.get('total', 0)))
    received = Decimal(str(totals.get('received', 0)))
    new_received = received + amount
    new_balance = total_due - new_received

    totals['received'] = float(new_received)
    totals['balance'] = float(new_balance)
    invoice.totals = totals

    # Update invoice status
    if new_balance <= 0:
        invoice.status = 'paid'
    elif new_received > 0:
        invoice.status = 'partially_paid'

    invoice.save(update_fields=['totals', 'status', 'dt_modified', 'version'])

    # Mark pending as applied
    pending.state = PendingPaymentApplication.STATE_APPLIED
    pending.dt_applied = timezone.now()
    pending.save(update_fields=['state', 'dt_applied', 'dt_modified', 'version'])

    logger.info(
        "Applied pending payment %s: payment %s -> invoice %s, $%s",
        pending.pk, payment.pk, invoice.pk, amount,
    )
    return True


@transaction.atomic
def apply_pending_for_invoice(invoice_id: int) -> Dict[str, Any]:
    """Apply all pending payments for an invoice after unlock.

    Returns:
        {applied_count, still_pending}
    """
    from apps.transactions.models import Invoice
    from apps.transactions.models.pending_payment import PendingPaymentApplication

    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)

    if getattr(invoice, 'is_locked', False):
        return {'applied_count': 0, 'still_pending': 0, 'message': 'Invoice is still locked'}

    pendings = (
        PendingPaymentApplication.objects
        .filter(invoice_id=invoice_id, state=PendingPaymentApplication.STATE_PENDING)
        .select_for_update()
        .order_by('dt_created')
    )

    applied_count = 0
    for p in pendings:
        if _apply_one(p, invoice=invoice):
            applied_count += 1
            # Refresh invoice to get updated totals for next iteration
            invoice.refresh_from_db()

    still_pending = (
        PendingPaymentApplication.objects
        .filter(invoice_id=invoice_id, state=PendingPaymentApplication.STATE_PENDING)
        .count()
    )

    return {
        'applied_count': applied_count,
        'still_pending': still_pending,
    }


def get_pending_for_invoice(invoice_id: int) -> Dict[str, Any]:
    """Return all pending payment applications for an invoice.

    Returns:
        {invoice_id, pending: [{id, payment_id, amount, state, reason, dt_created}]}
    """
    from apps.transactions.models.pending_payment import PendingPaymentApplication

    rows = (
        PendingPaymentApplication.objects
        .filter(invoice_id=invoice_id)
        .order_by('-dt_created')
        .values('id', 'payment_id', 'amount', 'state', 'reason', 'dt_created', 'dt_applied')
    )

    return {
        'invoice_id': invoice_id,
        'pending': [
            {
                'id': r['id'],
                'payment_id': r['payment_id'],
                'amount': float(r['amount']),
                'state': r['state'],
                'reason': r['reason'],
                'dt_created': r['dt_created'],
                'dt_applied': r['dt_applied'],
            }
            for r in rows
        ],
    }


__all__ = [
    'apply_payment_to_invoice',
    'apply_pending_for_invoice',
    'get_pending_for_invoice',
]
