"""Pending Archive Service — extract processed pending records to external storage.

Moves applied/canceled/processed pending records from the operational database
to dated JSONL files organized by type and category. The operational DB stays
lean; the archive becomes the long-term memory for pattern analysis.

Archive structure:
    .local/dated_outside/
    ├── inventory/{product_class}/YYYY-MM.jsonl.gz
    ├── cash_flow/{category}/YYYY-MM.jsonl.gz
    └── queue/{model_name}/YYYY-MM.jsonl.gz

Alice owns the nightly archive task. Pattern analysis reads from the archive.
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps
from django.conf import settings

logger = logging.getLogger(__name__)

# Archive root — inside the project's .local/ directory
ARCHIVE_ROOT = Path(getattr(settings, 'BASE_DIR', '.')) / '.local' / 'dated_outside'


def _get_models():
    """Lazy-load models from across apps."""
    PendingPaymentApplication = dj_apps.get_model('transactions', 'PendingPaymentApplication')
    Pending = dj_apps.get_model('core', 'Pending')
    Item = dj_apps.get_model('products', 'Item')
    return PendingPaymentApplication, Pending, Item


def _now_ms() -> int:
    return int(time.time() * 1000)


def _month_key(epoch_ms: int) -> str:
    """Convert epoch milliseconds to YYYY-MM string."""
    if not epoch_ms or epoch_ms <= 0:
        return datetime.now(timezone.utc).strftime('%Y-%m')
    try:
        dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        return dt.strftime('%Y-%m')
    except (OSError, ValueError):
        return datetime.now(timezone.utc).strftime('%Y-%m')


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _append_jsonl_gz(filepath: Path, records: List[Dict]) -> int:
    """Append records to a gzipped JSONL file. Creates if doesn't exist."""
    _ensure_dir(filepath.parent)
    mode = 'ab'  # append binary
    with gzip.open(filepath, mode) as f:
        for rec in records:
            line = json.dumps(rec, default=str, separators=(',', ':')) + '\n'
            f.write(line.encode('utf-8'))
    return len(records)


def _get_product_class(item_id: Optional[int]) -> str:
    """Resolve product class from Item's refs.categories or catalog.category."""
    if not item_id:
        return '_unclassified'
    try:
        _, _, Item = _get_models()
        item = Item.objects.only('refs', 'catalog').get(pk=item_id)
        # Try refs.categories first
        refs = item.refs if isinstance(item.refs, dict) else {}
        cats = refs.get('categories', [])
        if cats and isinstance(cats, list) and cats[0]:
            return str(cats[0]).lower().replace(' ', '_').replace('/', '_')
        # Try catalog.category
        catalog = item.catalog if isinstance(item.catalog, dict) else {}
        cat = catalog.get('category', '')
        if cat:
            return str(cat).lower().replace(' ', '_').replace('/', '_')
    except Exception:
        pass
    return '_unclassified'


# ── Archive extractors ────────────────────────────────────────────────

def _archive_inventory_pending(batch_size: int = 1000) -> Dict[str, int]:
    """Archive processed inventory Pending records."""
    _, Pending, _ = _get_models()

    qs = (
        Pending.objects
        .filter(model_name='item', purpose__startswith='inventory_')
        .exclude(dt_processed=0)
        .order_by('pk')[:batch_size]
    )

    buckets: Dict[str, List[Dict]] = {}
    pks_to_delete = []

    for rec in qs:
        item_id = int(rec.record_id) if rec.record_id else None
        product_class = _get_product_class(item_id)
        data = rec.changes if isinstance(rec.changes, dict) else {}

        archive_rec = {
            'dt_created': rec.dt_created,
            'dt_processed': rec.dt_processed,
            'processing_ms': (rec.dt_processed - rec.dt_created) if (rec.dt_processed and rec.dt_created) else None,
            'type': 'inventory',
            'purpose': rec.purpose,
            'item_id': item_id,
            'product_class': product_class,
            'changes': data,
        }

        month_key = _month_key(rec.dt_created)
        bucket_key = f"inventory/{product_class}/{month_key}"
        buckets.setdefault(bucket_key, []).append(archive_rec)
        pks_to_delete.append(rec.pk)

    counts = {}
    for bucket_key, records in buckets.items():
        filepath = ARCHIVE_ROOT / f"{bucket_key}.jsonl.gz"
        written = _append_jsonl_gz(filepath, records)
        counts[bucket_key] = written

    if pks_to_delete:
        Pending.objects.filter(pk__in=pks_to_delete).delete()

    total = sum(counts.values())
    if total > 0:
        logger.info("Archived %d inventory pending records to %d files", total, len(counts))
    return counts


def _archive_payment_pending(batch_size: int = 1000) -> Dict[str, int]:
    """Archive applied/canceled PendingPaymentApplication records."""
    PendingPaymentApplication, _, _ = _get_models()

    qs = (
        PendingPaymentApplication.objects
        .filter(state__in=['applied', 'canceled'])
        .select_related('payment', 'invoice')
        .order_by('pk')[:batch_size]
    )

    buckets: Dict[str, List[Dict]] = {}
    pks_to_delete = []

    for rec in qs:
        dt_created = getattr(rec, 'dt_created', 0) or 0
        dt_applied = None
        if rec.dt_applied:
            dt_applied = int(rec.dt_applied.timestamp() * 1000)

        processing_ms = (dt_applied - dt_created) if (dt_applied and dt_created) else None

        # Categorize by payment direction
        payment = rec.payment
        payment_type = ''
        if payment:
            payment_type = getattr(payment, 'type', '') or getattr(payment, 'payment_type', '') or ''
        if 'receive' in payment_type.lower() or 'customer' in payment_type.lower():
            category = 'customer_receipts'
        elif 'pay' in payment_type.lower() or 'vendor' in payment_type.lower():
            category = 'vendor_payments'
        else:
            category = 'applied_to_invoice'

        archive_rec = {
            'dt_created': dt_created,
            'dt_applied': dt_applied,
            'processing_ms': processing_ms,
            'state': rec.state,
            'type': 'cash_flow',
            'category': category,
            'payment_id': payment.pk if payment else None,
            'invoice_id': rec.invoice_id if rec.invoice_id else None,
            'amount': float(rec.amount) if rec.amount else 0,
            'reason': rec.reason or '',
            'request_ref': rec.request_ref if isinstance(rec.request_ref, dict) else {},
            'cancel_reason': rec.cancel_reason or '',
        }

        month_key = _month_key(dt_created)
        bucket_key = f"cash_flow/{category}/{month_key}"
        buckets.setdefault(bucket_key, []).append(archive_rec)
        pks_to_delete.append(rec.pk)

    # Write to files
    counts = {}
    for bucket_key, records in buckets.items():
        filepath = ARCHIVE_ROOT / f"{bucket_key}.jsonl.gz"
        written = _append_jsonl_gz(filepath, records)
        counts[bucket_key] = written

    if pks_to_delete:
        PendingPaymentApplication.objects.filter(pk__in=pks_to_delete).delete()

    total = sum(counts.values())
    if total > 0:
        logger.info("Archived %d payment pending records to %d files", total, len(counts))
    return counts


def _archive_generic_pending(batch_size: int = 1000) -> Dict[str, int]:
    """Archive processed generic Pending queue records."""
    _, Pending, _ = _get_models()

    qs = (
        Pending.objects
        .filter(dt_processed__gt=0)
        .order_by('pk')[:batch_size]
    )

    buckets: Dict[str, List[Dict]] = {}
    pks_to_delete = []

    for rec in qs:
        model_name = (rec.model_name or '_unclassified').lower().replace(' ', '_')
        dt_created = getattr(rec, 'dt_created', 0) or 0
        dt_processed = rec.dt_processed or 0
        processing_ms = (dt_processed - dt_created) if (dt_processed and dt_created) else None

        archive_rec = {
            'dt_created': dt_created,
            'dt_processed': dt_processed,
            'processing_ms': processing_ms,
            'type': 'queue',
            'model_name': rec.model_name or '',
            'record_id': rec.record_id or '',
            'name': rec.name or '',
            'changes': rec.changes if isinstance(rec.changes, list) else [],
            'attempts': rec.attempts or 0,
            'sequence': rec.sequence or 0,
        }

        month_key = _month_key(dt_created)
        bucket_key = f"queue/{model_name}/{month_key}"
        buckets.setdefault(bucket_key, []).append(archive_rec)
        pks_to_delete.append(rec.pk)

    counts = {}
    for bucket_key, records in buckets.items():
        filepath = ARCHIVE_ROOT / f"{bucket_key}.jsonl.gz"
        written = _append_jsonl_gz(filepath, records)
        counts[bucket_key] = written

    if pks_to_delete:
        Pending.objects.filter(pk__in=pks_to_delete).delete()

    total = sum(counts.values())
    if total > 0:
        logger.info("Archived %d generic pending records to %d files", total, len(counts))
    return counts


# ── Main archive function ─────────────────────────────────────────────

def archive_processed_pending(batch_size: int = 1000) -> Dict[str, Any]:
    """Archive all processed pending records across all three models.

    Called by Celery nightly task. Extracts applied/canceled/processed records,
    writes to dated JSONL.gz files, deletes from operational DB.

    Args:
        batch_size: Max records per model per run (prevents unbounded processing)

    Returns:
        Summary dict with counts per type and file.
    """
    results = {
        'inventory': _archive_inventory_pending(batch_size),
        'cash_flow': _archive_payment_pending(batch_size),
        'queue': _archive_generic_pending(batch_size),
        'dt_archived': _now_ms(),
    }

    total = sum(
        sum(v.values()) if isinstance(v, dict) else 0
        for v in results.values()
        if isinstance(v, dict)
    )
    results['total_archived'] = total

    if total > 0:
        logger.info("Pending archive complete: %d total records archived", total)

    return results
