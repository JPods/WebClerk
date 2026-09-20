"""Cash pending service for Receipts — AP mirror of cash_pending.py.

Every AP cash application flows through a Pending record with
purpose='cash_application_receipt'. Same Pending model, different purpose.

If the receipt is not locked (dt_journaled == 0), applies immediately.
If locked, stays queued for celery.

changes JSON schema:
    {
        "cash_id": int,
        "receipt_id": int,
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

RECEIPT_CASH_PURPOSE = 'cash_application_receipt'


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _applied(**match) -> Decimal:
    """Σ of the applications that match — the AP mirror of cash_pending._applied.

    AP used to increment the stored total (``paid + amount``) and decrement
    ``cash.available``. Two ways to compute one number, and a retry double-counted. The
    applications are the record; paid and available are read from them (Bill, 2026-09-20).
    """
    from django.db.models import DecimalField, Sum
    from django.db.models.fields.json import KeyTextTransform
    from django.db.models.functions import Cast

    from apps.core.models.pending import Pending

    filters = {f'changes__{k}': v for k, v in match.items()}
    total = (
        Pending.objects.filter(purpose=RECEIPT_CASH_PURPOSE, changes__state='applied', **filters)
        .annotate(amt=Cast(KeyTextTransform('amount', 'changes'),
                           DecimalField(max_digits=14, decimal_places=2)))
        .aggregate(s=Sum('amt'))['s']
    )
    return _d(total)


def refresh_receipt_paid(receipt) -> Dict[str, Any]:
    """Recompute the payable's paid and balance from its applications."""
    from apps.accounts.services.terms_ledger import allocate_paid
    from apps.transactions.services.pricing.totals_compute import update_paid

    result = update_paid(receipt, _applied(receipt_id=receipt.pk))
    allocate_paid(receipt)
    return result


def refresh_cash_available(cash) -> Decimal:
    """available = amount − Σ applied, on both sides of the house.

    Cash pays invoices and receipts, so what is left is the amount less everything it has
    been applied to, whichever side that was.
    """
    from apps.transactions.services.cash.cash_pending import _applied as _applied_ar

    available = _d(cash.amount) - _applied_ar(cash_id=cash.pk) - _applied(cash_id=cash.pk)
    if _d(cash.available) != available:
        cash.available = available
        cash.save(update_fields=['available', 'dt_modified', 'version'])
    return available


@transaction.atomic
def apply_cash_to_receipt(
    cash_id: int,
    receipt_id: int,
    amount,
    reason: str = '',
    contact_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a Pending record for AP cash application to a Receipt.

    Mirrors apply_cash_to_invoice exactly:
    - If receipt is not locked, applies immediately via Pending.try_apply().
    - If locked (dt_journaled != 0), queues for celery.

    Returns:
        {pending_id, state, amount, applied}
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Cash, Receipt

    cash = Cash.objects.select_for_update().get(pk=cash_id)
    receipt = Receipt.objects.select_for_update().get(pk=receipt_id)
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValueError("amount must be positive")

    changes = {
        'cash_id': cash_id,
        'receipt_id': receipt_id,
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
        name=f'Cash #{cash_id} → Receipt #{receipt_id} ${amount}',
        purpose=RECEIPT_CASH_PURPOSE,
        changes=changes,
    )

    applied = pending.is_processed()

    return {
        'pending_id': pending.pk,
        'state': 'applied' if applied else 'pending',
        'amount': float(amount),
        'applied': applied,
    }


def apply_receipt_cash_pending(pending) -> bool:
    """Apply a single receipt cash Pending record. Called from Pending.try_apply().

    AP mirror of apply_cash_pending(). Returns True on success, False if queued.
    """
    from django.db import OperationalError
    from apps.transactions.models import Cash, Receipt

    changes = pending.changes if isinstance(pending.changes, dict) else {}
    cash_id = changes.get('cash_id')
    receipt_id = changes.get('receipt_id')
    amount_val = changes.get('amount', 0)

    if not cash_id or not receipt_id or not amount_val:
        logger.warning("Pending %s: missing cash_id/receipt_id/amount", pending.pk)
        return False

    amount = Decimal(str(amount_val))

    if pending.is_processed() or (changes or {}).get('state') == 'applied':
        return True                     # already applied — a retry records nothing twice

    try:
        with transaction.atomic():
            try:
                cash = Cash.objects.select_for_update(nowait=True).get(pk=cash_id)
                receipt = Receipt.objects.select_for_update(nowait=True).get(pk=receipt_id)
            except (Cash.DoesNotExist, Receipt.DoesNotExist) as e:
                logger.warning("Pending %s: record not found: %s", pending.pk, e)
                return False

            # Don't apply to locked receipts (journalized to GL)
            if getattr(receipt, 'dt_journaled', 0) != 0:
                return False

            # ── The application is the record; paid and available are read from it ──
            changes['state'] = 'applied'
            changes['dt_applied'] = timezone.now().isoformat()
            pending.changes = changes
            pending.dt_processed = int(timezone.now().timestamp() * 1000)
            pending.save(update_fields=['changes', 'dt_processed', 'dt_modified', 'version'])

            from apps.transactions.services.cash.cash_pending import record_application_event
            record_application_event(receipt, pending, changes, cash)

            result = refresh_receipt_paid(receipt)
            new_paid = _d(result['paid']) if 'paid' in result else _applied(receipt_id=receipt.pk)
            new_balance = _d(result['balance'])

            if new_balance <= 0:
                receipt.status = 'paid'
            elif new_paid > 0:
                receipt.status = 'partially_paid'
            receipt.save(update_fields=['status', 'dt_modified', 'version'])

            # No clamp: paying more than is owed shows as a negative balance for a person
            # to resolve, rather than being quietly absorbed (Axiom 6).
            refresh_cash_available(cash)

            logger.info(
                "Applied receipt cash pending %s: cash %s → receipt %s, $%s (available now $%s)",
                pending.pk, cash.pk, receipt.pk, amount, cash.available,
            )
            return True

    except OperationalError:
        logger.debug("Pending %s: record locked, queued for celery", pending.pk)
        return False


@transaction.atomic
def apply_pending_for_receipt(receipt_id: int) -> Dict[str, Any]:
    """Apply all pending cash records for a receipt after unlock.

    AP mirror of apply_pending_for_invoice.

    Returns:
        {applied_count, still_pending}
    """
    from apps.core.models.pending import Pending
    from apps.transactions.models import Receipt

    receipt = Receipt.objects.select_for_update().get(pk=receipt_id)

    if getattr(receipt, 'dt_journaled', 0) != 0:
        return {'applied_count': 0, 'still_pending': 0, 'message': 'Receipt still locked (journalized)'}

    pendings = (
        Pending.objects
        .filter(purpose=RECEIPT_CASH_PURPOSE, dt_processed=0)
        .filter(changes__receipt_id=receipt_id)
        .select_for_update()
        .order_by('dt_created')
    )

    applied_count = 0
    for p in pendings:
        if apply_receipt_cash_pending(p):
            applied_count += 1
            receipt.refresh_from_db()

    still_pending = (
        Pending.objects
        .filter(purpose=RECEIPT_CASH_PURPOSE, dt_processed=0)
        .filter(changes__receipt_id=receipt_id)
        .count()
    )

    return {
        'applied_count': applied_count,
        'still_pending': still_pending,
    }


def get_pending_for_receipt(receipt_id: int) -> Dict[str, Any]:
    """Return all cash pending records for a receipt.

    AP mirror of get_pending_for_invoice.

    Returns:
        {receipt_id, pending: [{id, cash_id, amount, state, reason, dt_created}]}
    """
    from apps.core.models.pending import Pending

    rows = (
        Pending.objects
        .filter(purpose=RECEIPT_CASH_PURPOSE)
        .filter(changes__receipt_id=receipt_id)
        .order_by('-dt_created')
        .values('id', 'changes', 'dt_created', 'dt_processed')
    )

    return {
        'receipt_id': receipt_id,
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
    'apply_cash_to_receipt',
    'apply_receipt_cash_pending',
    'apply_pending_for_receipt',
    'get_pending_for_receipt',
    'RECEIPT_CASH_PURPOSE',
]
