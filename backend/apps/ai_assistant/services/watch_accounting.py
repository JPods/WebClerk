"""
Alice Accounting Watchdog — Detect GL imbalances and payment anomalies.

Scans for:
1. GL journal batches where debits != credits
2. Invoices with balance != (total - payments applied)
3. Payments not applied to any invoice
4. Ledger entries with no matching transaction
5. Aging anomalies (past-due invoices with no collection action)

Creates AliceObservation records for anything out of balance.

Called by: accounting_watchdog_task (Celery, nightly)
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db.models import Sum, Q, F, Count
from django.utils import timezone

logger = logging.getLogger('alice.accounting')


def run_accounting_watchdog() -> dict:
    """Run all accounting checks. Returns summary of findings."""
    results = {}
    results['gl_balance'] = check_gl_balance()
    results['invoice_balance'] = check_invoice_balances()
    results['unapplied_payments'] = check_unapplied_payments()
    results['orphan_ledger'] = check_orphan_ledger_entries()
    results['aging'] = check_aging_anomalies()

    total_obs = sum(r.get('observations', 0) for r in results.values())
    logger.info("Accounting watchdog complete: %d observations created", total_obs)
    return results


def check_gl_balance() -> dict:
    """Check that debits == credits per GL journal batch."""
    from apps.accounts.models import GlJournal

    # Aggregate debits and credits per batch
    batches = (
        GlJournal.objects.filter(batch_id__gt='')
        .values('batch_id')
        .annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
            entry_count=Count('id'),
        )
    )

    observations = 0
    imbalanced = []

    for batch in batches:
        debit = Decimal(str(batch['total_debit'] or 0))
        credit = Decimal(str(batch['total_credit'] or 0))
        diff = abs(debit - credit)

        if diff > Decimal('0.01'):  # penny tolerance
            imbalanced.append({
                'batch_id': batch['batch_id'],
                'debit': float(debit),
                'credit': float(credit),
                'diff': float(diff),
                'entries': batch['entry_count'],
            })

            _create_observation(
                category='anomaly',
                model_name='gljournal',
                message=f"GL batch {batch['batch_id']} imbalanced: "
                        f"debits=${debit:.2f} credits=${credit:.2f} diff=${diff:.2f}",
                detail=f"Batch has {batch['entry_count']} entries. "
                       f"Debits and credits must balance within $0.01.",
                dedup_key=f"gl_imbalance_{batch['batch_id']}",
                priority=2,
            )
            observations += 1

    return {
        'batches_checked': batches.count() if hasattr(batches, 'count') else len(list(batches)),
        'imbalanced': len(imbalanced),
        'observations': observations,
        'details': imbalanced[:10],
    }


def check_invoice_balances() -> dict:
    """Check that invoice.balance == invoice.total - sum(payments applied)."""
    from apps.transactions.models import Invoice, Payment

    observations = 0
    mismatches = []

    # Get all non-void invoices with a totals JSON envelope
    from common.json_lookups import totals_total
    invoices = Invoice.objects.exclude(
        status__in=['void', 'cancelled', 'draft']
    ).annotate(_total=totals_total()).filter(_total__isnull=False).only('id', 'ida', 'status', 'totals')

    for inv in invoices[:500]:  # batch limit
        # PJPV: read from JSON envelope, not scalar index fields
        totals_env = inv.totals if isinstance(inv.totals, dict) else {}
        if not totals_env:
            import logging
            logging.getLogger(__name__).warning(
                "Invoice %s missing totals JSON envelope — PJPV violation, skipping", inv.id
            )
            continue
        total = Decimal(str(totals_env.get('total', 0)))
        recorded_balance = Decimal(str(totals_env.get('balance', 0)))

        # Sum payments applied to this invoice
        pay_filter = Q(invoice_id=inv.id)
        payments_applied = (
            Payment.objects.filter(pay_filter)
            .aggregate(total_paid=Sum('amount'))['total_paid'] or 0
        )
        payments_applied = Decimal(str(payments_applied))

        expected_balance = total - payments_applied
        diff = abs(recorded_balance - expected_balance)

        if diff > Decimal('0.01'):
            mismatches.append({
                'invoice_id': inv.id,
                'ida': inv.ida,
                'total': float(total),
                'recorded_balance': float(recorded_balance),
                'expected_balance': float(expected_balance),
                'diff': float(diff),
            })

            _create_observation(
                category='anomaly',
                model_name='invoice',
                record_id=inv.id,
                message=f"Invoice {inv.ida} balance mismatch: "
                        f"recorded=${recorded_balance:.2f} expected=${expected_balance:.2f}",
                detail=f"Total: ${total:.2f}, Payments applied: ${payments_applied:.2f}. "
                       f"Difference: ${diff:.2f}.",
                dedup_key=f"inv_balance_mismatch_{inv.id}",
                priority=1,
            )
            observations += 1

    return {
        'invoices_checked': min(invoices.count(), 500),
        'mismatches': len(mismatches),
        'observations': observations,
    }


def check_unapplied_payments() -> dict:
    """Find payments that aren't applied to any invoice."""
    from apps.transactions.models import Payment

    observations = 0

    # Payments with status=completed but no invoice link
    completed_payments = Payment.objects.filter(
        status='completed',
    ).only('id', 'ida', 'amount', 'status', 'invoice_id', 'refs')

    unapplied_count = 0
    for payment in completed_payments[:200]:
        # Check FK first, then refs.links
        has_invoice = bool(payment.invoice_id)
        if not has_invoice:
            refs = payment.refs if isinstance(payment.refs, dict) else {}
            links = refs.get('links', {})
            has_invoice = bool(links.get('invoice'))

        if not has_invoice:
            unapplied_count += 1
            _create_observation(
                category='anomaly',
                model_name='payment',
                record_id=payment.id,
                message=f"Payment #{payment.id} ({payment.ida}) completed but not applied to any invoice",
                detail=f"Status: {payment.status}, Amount: {payment.amount}. "
                       f"This payment may need to be applied to an invoice.",
                dedup_key=f"unapplied_payment_{payment.id}",
                priority=1,
            )
            observations += 1

    return {
        'unapplied_found': unapplied_count,
        'observations': observations,
    }


def check_orphan_ledger_entries() -> dict:
    """Find ledger entries that reference non-existent transactions."""
    from apps.accounts.models import Ledger
    from apps.transactions.models import Invoice

    observations = 0

    # Ledger entries linked to invoices
    invoice_ledgers = Ledger.objects.filter(
        model_name='invoice', parent_id__isnull=False
    ).values_list('parent_id', flat=True)

    if invoice_ledgers:
        # Find which parent_ids don't exist in Invoice
        existing_ids = set(Invoice.objects.filter(
            id__in=list(invoice_ledgers)
        ).values_list('id', flat=True))

        orphans = [pid for pid in invoice_ledgers if pid not in existing_ids]

        if orphans:
            _create_observation(
                category='anomaly',
                model_name='ledger',
                message=f"{len(orphans)} ledger entries reference deleted invoices",
                detail=f"Parent IDs with no matching invoice: {orphans[:20]}. "
                       f"These may need to be voided or reassigned.",
                dedup_key=f"orphan_ledger_invoice_{len(orphans)}",
                priority=1,
            )
            observations += 1

    orphan_count = len(orphans) if invoice_ledgers and 'orphans' in locals() else 0
    return {
        'orphans_found': orphan_count,
        'observations': observations,
    }


def check_aging_anomalies() -> dict:
    """Find significantly past-due invoices with no recent activity."""
    from apps.accounts.models import Ledger

    observations = 0
    now = timezone.now()

    # Ledger entries past due by more than 90 days, not cleared, not void
    past_due = Ledger.objects.filter(
        dt_due__lt=now - timezone.timedelta(days=90),
        is_cleared=False,
        is_void=False,
        value_available__gt=0,
    ).select_related('org')

    count = past_due.count()
    if count > 0:
        # Group by org for a cleaner observation
        org_totals = past_due.values('org__id', 'org__name').annotate(
            total_due=Sum('value_available'),
            count=Count('id'),
        ).order_by('-total_due')[:20]

        detail_lines = []
        for ot in org_totals:
            org_name = ot.get('org__name', 'Unknown')
            detail_lines.append(
                f"  {org_name}: {ot['count']} entries, ${ot['total_due']:.2f}"
            )

        _create_observation(
            category='alert',
            model_name='ledger',
            message=f"{count} ledger entries past due >90 days with open balances",
            detail="By organization:\n" + "\n".join(detail_lines),
            dedup_key=f"aging_90day_{now.strftime('%Y-%W')}",  # weekly dedup
            priority=1,
        )
        observations += 1

    return {
        'past_due_90_count': count,
        'observations': observations,
    }


# ── Helpers ──────────────────────────────────────────────────────────

def _create_observation(category, model_name, message, detail='',
                        record_id=None, dedup_key='', priority=0):
    """Create an AliceObservation, deduped."""
    try:
        from apps.ai_assistant.models.alice import AliceObservation

        if dedup_key:
            if AliceObservation.objects.filter(
                dedup_key=dedup_key, resolved=False
            ).exists():
                return

        AliceObservation.objects.create(
            category=category,
            source='alice',
            priority=priority,
            message=message,
            detail=detail,
            model_name=model_name,
            record_id=record_id,
            dedup_key=dedup_key,
        )
    except Exception as e:
        logger.warning("Failed to create accounting observation: %s", e)
