"""
Ledger Sync Processor
=====================

Processes unprocessed Pending records with ``purpose='ledger_sync'`` to
ensure every invoice's ledger records and org balance are in sync.

DESIGN RATIONALE
----------------
Every invoice save that impacts ledgers creates a Pending "command" record.
In the happy path the command is marked processed immediately.  Two failure
modes leave the command unprocessed for this processor to retry:

1. **Org balance update failed** — ledger records exist but
   ``invoice.metadata.ledger.dt_sync == 0`` and the org's aging/balances
   may be stale.  The processor re-runs ``update_org_balances`` and, on
   success, stamps ``dt_sync`` and marks the Pending processed.

2. **Ledger write itself failed** — ``metadata.ledger`` is absent or has
   empty entries.  The processor re-runs the full ``on_invoice_save``
   pipeline (which creates its own *new* Pending for the next attempt)
   and marks the *original* Pending processed regardless so it doesn't
   loop.

USAGE
-----
    from apps.accounts.services.ledger_sync_processor import (
        process_ledger_sync_pending,
        process_ledger_sync_for_invoice,
    )

    # Process all unprocessed ledger-sync Pendings (Celery / management cmd)
    summary = process_ledger_sync_pending(limit=100)

    # Process for a specific invoice
    summary = process_ledger_sync_for_invoice(invoice_id=38)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TypedDict

from django.apps import apps as dj_apps
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.core.models import Pending

logger = logging.getLogger(__name__)

PURPOSE_LEDGER_SYNC = 'ledger_sync'


class SyncSummary(TypedDict, total=False):
    """Summary returned by the processor."""
    total_found: int
    synced: int
    skipped_missing_invoice: int
    retried_full: int
    errors: int


def process_ledger_sync_pending(
    limit: int = 100,
    dry_run: bool = False,
    invoice_id: Optional[int] = None,
) -> SyncSummary:
    """
    Process unprocessed ``ledger_sync`` Pending records.

    Args:
        limit: Max number of Pending records to process in this batch.
        dry_run: If True, log what would happen without changing data.
        invoice_id: Restrict to a single invoice (for targeted retry).

    Returns:
        Summary dict with counts.
    """
    summary: SyncSummary = {
        'total_found': 0,
        'synced': 0,
        'skipped_missing_invoice': 0,
        'retried_full': 0,
        'errors': 0,
    }

    qs = Pending.objects.filter(
        purpose=PURPOSE_LEDGER_SYNC,
        dt_processed=0,
    ).order_by('dt_created')

    if invoice_id is not None:
        qs = qs.filter(record_id=str(invoice_id))

    pending_records = list(qs[:limit])
    summary['total_found'] = len(pending_records)

    if not pending_records:
        return summary

    Invoice = dj_apps.get_model('transactions', 'Invoice')

    for pending in pending_records:
        inv_id = (pending.data or {}).get('invoice_id') or pending.record_id
        try:
            inv_id = int(inv_id)
        except (TypeError, ValueError):
            logger.warning("Pending %s has invalid invoice_id=%s, skipping", pending.pk, inv_id)
            summary['errors'] += 1
            continue

        try:
            invoice = Invoice.objects.get(pk=inv_id)
        except Invoice.DoesNotExist:
            logger.warning("Invoice %s not found for Pending %s, marking processed", inv_id, pending.pk)
            summary['skipped_missing_invoice'] += 1
            if not dry_run:
                pending.mark_processed(save=True)
            continue

        try:
            result = _sync_single(invoice, pending, dry_run=dry_run)
            if result == 'synced':
                summary['synced'] += 1
            elif result == 'retried_full':
                summary['retried_full'] += 1
        except Exception as exc:
            logger.error("Error processing ledger-sync Pending %s for invoice %s: %s", pending.pk, inv_id, exc)
            summary['errors'] += 1

    logger.info(
        "Ledger sync processor: found=%d synced=%d retried_full=%d "
        "missing_invoice=%d errors=%d",
        summary['total_found'], summary['synced'], summary['retried_full'],
        summary['skipped_missing_invoice'], summary['errors'],
    )
    return summary


def process_ledger_sync_for_invoice(invoice_id: int, dry_run: bool = False) -> SyncSummary:
    """Convenience wrapper: process all ledger-sync Pendings for one invoice."""
    return process_ledger_sync_pending(limit=1000, dry_run=dry_run, invoice_id=invoice_id)


# ─────────────────────────────────────────────────────────────────────────────
# Internal
# ─────────────────────────────────────────────────────────────────────────────

def _sync_single(invoice, pending: Pending, dry_run: bool = False) -> str:
    """
    Attempt to sync a single invoice.

    Returns:
        'synced'       — org balance updated, metadata stamped, Pending processed.
        'retried_full' — ledger records were missing so we re-ran on_invoice_save
                         (which creates its *own* new Pending for the next cycle);
                         this Pending is marked processed to stop looping.
    """
    from .ledger_balance import (
        _stamp_ledger_metadata,
        update_org_balances,
        on_invoice_save,
    )

    meta = getattr(invoice, 'metadata', None) or {}
    ledger_meta = meta.get('ledger', {})
    entries = ledger_meta.get('entries', [])
    dt_sync = ledger_meta.get('dt_sync', None)

    # ── Case A: Ledger records exist but dt_sync == 0 ────────────────
    # Ledgers were written; only the org balance update failed.
    if entries and dt_sync == 0:
        if dry_run:
            logger.info("[DRY RUN] Would re-sync org balance for invoice %s", invoice.pk)
            return 'synced'

        org = _resolve_org(invoice)
        if org:
            update_org_balances(org)

        # Stamp dt_sync on the invoice
        Ledger = dj_apps.get_model('accounts', 'Ledger')
        ledger_ids = [e['ledger_id'] for e in entries if 'ledger_id' in e]
        ledger_records = list(Ledger.objects.filter(pk__in=ledger_ids)) if ledger_ids else []

        now_ms = int(timezone.now().timestamp() * 1000)
        _stamp_ledger_metadata(invoice, ledger_records, dt_sync=now_ms)
        pending.mark_processed(save=True)

        logger.info("Ledger sync completed for invoice #%s (Pending %s)", invoice.pk, pending.pk)
        return 'synced'

    # ── Case B: No entries — ledger write itself failed ──────────────
    # Re-run the full pipeline.  on_invoice_save will create a *new*
    # Pending for this attempt; mark *this* one processed so we don't
    # accumulate duplicates.
    if dry_run:
        logger.info("[DRY RUN] Would re-run full on_invoice_save for invoice %s", invoice.pk)
        return 'retried_full'

    logger.info(
        "Ledger entries missing for invoice #%s — re-running on_invoice_save (Pending %s)",
        invoice.pk, pending.pk,
    )
    on_invoice_save(invoice, replace_ledgers=True)
    pending.mark_processed(save=True)
    return 'retried_full'


def _resolve_org(invoice):
    """Resolve the OrgBase instance from an invoice."""
    org = getattr(invoice, 'customer', None)
    if org is not None:
        return org
    org_id = getattr(invoice, 'customer_id', None)
    if org_id:
        OrgBase = dj_apps.get_model('orgs', 'OrgBase')
        try:
            return OrgBase.objects.get(id=org_id)
        except OrgBase.DoesNotExist:
            pass
    return None
