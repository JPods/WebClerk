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
    write_off_difference: bool = False,
) -> Dict[str, Any]:
    """Create a PendingPaymentApplication.

    If the invoice is not locked, apply immediately (reduce invoice balance,
    update payment). If locked, queue as pending.

    write_off_difference: if True, after applying the payment, any remaining
    balance on the invoice is written off as a separate Payment record posted
    to the write-off GL account. For small differences not worth collecting
    (e.g., customer pays $99.50 on a $100.00 invoice — $0.50 written off).

    Returns:
        {pending_id, state, amount, applied, write_off}
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

    write_off_result = None
    if write_off_difference and applied:
        write_off_result = _write_off_balance(invoice, payment)

    result = {
        'pending_id': pending.pk,
        'state': pending.state,
        'amount': float(pending.amount),
        'applied': applied,
    }
    if write_off_result:
        result['write_off'] = write_off_result
    return result


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

    # ── Early payment discount check ─────────────────────────────────
    # If payment is within the discount window (e.g. 10 days for "2/10
    # Net 30"), create a separate Payment record for the discount amount
    # posted to the discount GL account. The discount is real money —
    # it needs its own Payment, its own GL entry, its own audit trail.
    early_discount = Decimal('0')
    finance = getattr(invoice, 'finance', None) or {}
    discount_days = finance.get('discount_days') or 0
    discount_rate = finance.get('discount_rate') or 0

    if discount_days and discount_rate and not finance.get('discount_taken'):
        invoice_date = getattr(invoice, 'dt_created', None)
        payment_date = getattr(payment, 'dt_created', None) or timezone.now()
        if invoice_date and payment_date:
            from datetime import timedelta

            # Normalize to date objects
            def _to_date(val):
                if isinstance(val, (int, float)):
                    from datetime import datetime as dt
                    return dt.fromtimestamp(val / 1000, tz=timezone.utc).date()
                return val.date() if hasattr(val, 'date') else val

            invoice_dt = _to_date(invoice_date)
            payment_dt = _to_date(payment_date)

            if payment_dt <= invoice_dt + timedelta(days=int(discount_days)):
                totals_check = invoice.totals or {}
                total_due = Decimal(str(totals_check.get('total', 0)))
                early_discount = (total_due * Decimal(str(discount_rate)) / 100).quantize(Decimal('0.01'))

                # Create a Payment record for the discount amount
                discount_payment = Payment.objects.create(
                    amount=early_discount,
                    status='completed',
                    payment_method='discount',
                    reference_number=f'EPD-{invoice.pk}',
                    customer_id=getattr(payment, 'customer_id', None),
                    metadata={
                        'type': 'early_payment_discount',
                        'invoice_id': invoice.pk,
                        'source_payment_id': payment.pk,
                        'discount_rate': float(discount_rate),
                        'discount_days': int(discount_days),
                        'invoice_date': invoice_dt.isoformat(),
                        'payment_date': payment_dt.isoformat(),
                        'gl_account': finance.get('discount_gl_account', ''),
                    },
                )

                # Apply the discount payment to the same invoice
                from apps.transactions.models.pending_payment import PendingPaymentApplication
                discount_pending = PendingPaymentApplication.objects.create(
                    payment=discount_payment,
                    invoice=invoice,
                    amount=early_discount,
                    state=PendingPaymentApplication.STATE_PENDING,
                    reason=f'Early payment discount {discount_rate}% within {discount_days} days',
                )

                logger.info(
                    "Early payment discount: invoice %s, %s%% = $%s → Payment #%s",
                    invoice.pk, discount_rate, early_discount, discount_payment.pk,
                )

                # Record that discount was taken (prevents double application)
                finance['discount_taken'] = float(early_discount)
                finance['discount_date'] = payment_dt.isoformat()
                finance['discount_payment_id'] = discount_payment.pk
                invoice.finance = finance

    # Update invoice totals
    totals = invoice.totals or {}
    total_due = Decimal(str(totals.get('total', 0)))
    received = Decimal(str(totals.get('received', 0)))
    # The discount Payment will be applied separately via its own pending record.
    # Here we only apply the original payment amount.
    new_received = received + amount
    new_balance = total_due - new_received - early_discount

    totals['received'] = float(new_received)
    totals['balance'] = float(new_balance)
    invoice.totals = totals

    # Update invoice status
    if new_balance <= 0:
        invoice.status = 'paid'
    elif new_received > 0:
        invoice.status = 'partially_paid'

    update_fields = ['totals', 'status', 'dt_modified', 'version']
    if early_discount > 0:
        update_fields.append('finance')
    invoice.save(update_fields=update_fields)

    # Now apply the discount payment's pending record
    if early_discount > 0:
        _apply_one(discount_pending, invoice, discount_payment)

    # Mark pending as applied
    pending.state = PendingPaymentApplication.STATE_APPLIED
    pending.dt_applied = timezone.now()
    pending.save(update_fields=['state', 'dt_applied', 'dt_modified', 'version'])

    logger.info(
        "Applied pending payment %s: payment %s -> invoice %s, $%s",
        pending.pk, payment.pk, invoice.pk, amount,
    )
    return True


def _write_off_balance(invoice, source_payment) -> Optional[Dict[str, Any]]:
    """Write off a small remaining balance as a separate Payment.

    Creates a Payment with payment_method='write_off' for the remaining
    balance. Posts to the write-off GL account. Same pattern as the
    early payment discount — every dollar gets its own Payment record.

    WC2 heritage: "Discount Difference" checkbox in Apply Payment dialog.
    Customer pays $99.50 on $100 invoice → $0.50 write-off, not worth calling.
    """
    from apps.transactions.models.pending_payment import PendingPaymentApplication

    invoice.refresh_from_db(fields=['totals', 'status'])
    totals = invoice.totals or {}
    balance = Decimal(str(totals.get('balance', 0)))

    if balance <= 0:
        return None  # nothing to write off

    # Create write-off Payment
    wo_payment = Payment.objects.create(
        amount=balance,
        status='completed',
        payment_method='write_off',
        reference_number=f'WO-{invoice.pk}',
        customer_id=getattr(source_payment, 'customer_id', None),
        metadata={
            'type': 'write_off',
            'invoice_id': invoice.pk,
            'source_payment_id': source_payment.pk,
            'original_balance': float(balance),
            'gl_account': (getattr(invoice, 'finance', None) or {}).get('write_off_gl_account', ''),
        },
    )

    # Apply to invoice
    wo_pending = PendingPaymentApplication.objects.create(
        payment=wo_payment,
        invoice=invoice,
        amount=balance,
        state=PendingPaymentApplication.STATE_PENDING,
        reason=f'Write off balance ${balance}',
    )
    _apply_one(wo_pending, invoice, wo_payment)

    logger.info(
        "Write-off: invoice %s, $%s → Payment #%s",
        invoice.pk, balance, wo_payment.pk,
    )

    return {
        'payment_id': wo_payment.pk,
        'amount': float(balance),
        'reference': wo_payment.reference_number,
    }


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
