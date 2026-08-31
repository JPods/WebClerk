from __future__ import annotations

from typing import Dict, List, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.transactions.models import Invoice, Payment


class PaymentApplicationError(Exception):
    """Custom exception for payment application operations."""
    pass


@transaction.atomic
def apply_payment_to_invoice(
    invoice: Invoice,
    payment: Payment,
    amount: Optional[Decimal] = None
) -> Dict[str, any]:
    """DEPRECATED — use payment_pending.apply_payment_to_invoice instead.

    This direct path bypasses the pending record. All payment applications
    must flow through PendingPaymentApplication for a single audit trail.
    Kept only for unapply_payment_from_invoice reference.
    """
    import warnings
    warnings.warn(
        "payment_application.apply_payment_to_invoice is deprecated. "
        "Use payment_pending.apply_payment_to_invoice instead.",
        DeprecationWarning, stacklevel=2,
    )
    # Lock the payment row to prevent double-apply from concurrent requests
    payment = Payment.objects.select_for_update().get(pk=payment.pk)

    if payment.status != 'completed':
        raise PaymentApplicationError("Payment must be completed before application")

    if invoice.status in ['paid', 'canceled']:
        raise PaymentApplicationError(f"Invoice status '{invoice.status}' does not allow payment application")

    apply_amount = Decimal(str(amount)) if amount else Decimal(str(payment.amount))

    # Check if payment is already fully applied
    total_applied = sum(Decimal(str(p.amount)) for p in payment.applications.all())
    remaining_payment = Decimal(str(payment.amount)) - total_applied

    if remaining_payment <= 0:
        raise PaymentApplicationError("Payment is already fully applied")

    apply_amount = min(apply_amount, remaining_payment)

    # Get current invoice balance — read from envelope, don't recompute (PJPV)
    invoice_totals = invoice.totals or {}
    payments_received = Decimal(str(invoice_totals.get('received', 0)))
    current_balance = Decimal(str(invoice_totals.get('balance', 0)))

    if current_balance <= 0:
        raise PaymentApplicationError("Invoice is already fully paid")

    actual_apply = min(apply_amount, current_balance)

    # Create payment application record
    from apps.transactions.models import PaymentApplication
    application = PaymentApplication.objects.create(
        payment=payment,
        invoice=invoice,
        amount=actual_apply,
        applied_at=timezone.now()
    )

    # Update payment refs to include this invoice
    payment.add_invoice_ref(invoice.id)
    payment.add_audit_entry('payment_applied', {
        'invoice_id': invoice.id,
        'amount': float(actual_apply),
        'application_id': application.id
    })

    # Update invoice totals via PJPV single engine
    from apps.transactions.services.pricing.totals_compute import update_received
    new_received = payments_received + actual_apply
    result = update_received(invoice, new_received)
    new_balance = Decimal(str(result['balance']))

    # Update invoice status
    if new_balance <= 0:
        invoice.status = 'paid'
    elif new_received > 0:
        invoice.status = 'partially_paid'

    invoice.save(update_fields=['status', 'dt_modified', 'version'])

    # Update payment status if fully applied
    payment_total_applied = total_applied + actual_apply
    payment_fully_applied = payment_total_applied >= payment.amount

    if payment_fully_applied:
        payment.status = 'fully_applied'
        payment.save(update_fields=['status', 'dt_modified', 'version'])

    return {
        'success': True,
        'amount_applied': float(actual_apply),
        'invoice_balance_remaining': float(new_balance),
        'payment_fully_applied': payment_fully_applied,
        'invoice_fully_paid': new_balance <= 0,
        'application_id': application.id
    }


@transaction.atomic
def unapply_payment_from_invoice(
    payment: Payment,
    invoice: Invoice,
    application_id: Optional[int] = None
) -> Dict[str, any]:
    """
    Remove payment application from invoice.

    Args:
        payment: The payment record
        invoice: The invoice
        application_id: Specific application to remove (optional)

    Returns:
        {
            'success': bool,
            'amount_unapplied': float,
            'invoice_balance_increased': float
        }
    """
    from apps.transactions.models import PaymentApplication

    if application_id:
        try:
            application = PaymentApplication.objects.get(
                id=application_id,
                payment=payment,
                invoice=invoice
            )
        except PaymentApplication.DoesNotExist:
            raise PaymentApplicationError("Payment application not found")
    else:
        # Find the most recent application
        application = PaymentApplication.objects.filter(
            payment=payment,
            invoice=invoice
        ).order_by('-applied_at').first()

        if not application:
            raise PaymentApplicationError("No payment application found")

    unapply_amount = Decimal(str(application.amount))

    # Update invoice totals via PJPV single engine
    from apps.transactions.services.pricing.totals_compute import update_received
    invoice_totals = invoice.totals or {}
    payments_received = Decimal(str(invoice_totals.get('received', 0)))
    new_received = max(Decimal('0'), payments_received - unapply_amount)
    result = update_received(invoice, new_received)
    new_balance = Decimal(str(result['balance']))
    total_due = Decimal(str(result['total']))

    # Update invoice status
    if new_balance >= total_due:
        invoice.status = 'sent'  # Reset to sent if no payments
    elif new_balance > 0:
        invoice.status = 'partially_paid'

    invoice.save(update_fields=['status', 'dt_modified', 'version'])

    # Restore payment.available and update status
    payment.available = Decimal(str(payment.available)) + unapply_amount
    total_applied = sum(Decimal(str(p.amount)) for p in payment.applications.all()) - unapply_amount
    if total_applied < payment.amount:
        payment.status = 'completed'  # Reset if not fully applied
    payment.save(update_fields=['available', 'status', 'dt_modified', 'version'])

    # Delete the application
    application.delete()

    return {
        'success': True,
        'amount_unapplied': float(unapply_amount),
        'invoice_balance_increased': float(unapply_amount)
    }


def get_invoice_payment_status(invoice: Invoice) -> Dict[str, any]:
    """
    Get comprehensive payment status for an invoice.

    Returns:
        {
            'total_due': float,
            'total_paid': float,
            'balance': float,
            'payment_count': int,
            'is_fully_paid': bool,
            'is_overdue': bool,
            'last_payment_date': datetime,
            'payments': List[Dict]
        }
    """
    totals = invoice.totals or {}
    total_due = float(totals.get('total', 0))
    total_paid = float(totals.get('received', 0))
    balance = float(totals.get('balance', 0))  # PJPV: read from envelope, don't recompute

    payments = []
    for application in invoice.payment_applications.select_related('payment').order_by('-applied_at'):
        payments.append({
            'id': application.id,
            'payment_id': application.payment.id,
            'amount': float(application.amount),
            'applied_at': application.applied_at,
            'payment_method': application.payment.method or None,
            'reference': application.payment.reference_number
        })

    # Check if overdue (simplified - could be enhanced with terms)
    is_overdue = balance > 0 and invoice.status == 'overdue'

    last_payment = payments[0]['applied_at'] if payments else None

    return {
        'total_due': total_due,
        'total_paid': total_paid,
        'balance': balance,
        'payment_count': len(payments),
        'is_fully_paid': balance <= 0,
        'is_overdue': is_overdue,
        'last_payment_date': last_payment,
        'payments': payments
    }


__all__ = [
    'apply_payment_to_invoice',
    'unapply_payment_from_invoice',
    'get_invoice_payment_status',
    'PaymentApplicationError',
]