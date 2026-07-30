"""
Pending processor — Celery calls this, it dispatches by purpose.

Celery's only job:
    process_pending.delay()   # hourly via Beat

This function's job:
    for p in Pending.objects.filter(dt_processed=0)[:BATCH_SIZE]:
        dispatch(p.purpose, p)

Handlers register themselves in HANDLERS dict.
"""

import logging

from apps.core.models.pending import Pending

logger = logging.getLogger("sync.pending")

BATCH_SIZE = 50


# ── Handler registry ─────────────────────────────────────────────────────────
# Add new purpose handlers here.  Each handler takes a Pending and returns bool.

def _handle_bundle_out(pending):
    from apps.sync.services.bundle_send import handle_bundle_out
    return handle_bundle_out(pending)


HANDLERS = {
    "sync.bundle_out": _handle_bundle_out,
    # "sync.bundle_in":        _handle_bundle_in,
    # "alice.pattern_review":  _handle_pattern_review,
    # "allie.nightly_reflect": _handle_nightly_reflect,
}


# ── Processor ────────────────────────────────────────────────────────────────

def process_all_pending():
    """Process unprocessed Pending records, oldest first, up to BATCH_SIZE.

    Returns (processed, failed, skipped).
    """
    pending_qs = (
        Pending.objects
        .filter(dt_processed=0, is_active=True, purpose__isnull=False)
        .exclude(purpose="")
        .order_by("dt_created")[:BATCH_SIZE]
    )

    processed = 0
    failed = 0
    skipped = 0

    for p in pending_qs:
        handler = HANDLERS.get(p.purpose)
        if handler is None:
            logger.debug("No handler for purpose=%s (pending.id=%s), skipping", p.purpose, p.id)
            skipped += 1
            continue

        try:
            result = handler(p)
            if result:
                processed += 1
            else:
                failed += 1
        except Exception:
            logger.exception("Handler crashed for pending.id=%s purpose=%s", p.id, p.purpose)
            failed += 1

    logger.info("Pending processor: %d processed, %d failed, %d skipped (batch=%d)",
                processed, failed, skipped, BATCH_SIZE)
    return processed, failed, skipped
