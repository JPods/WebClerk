import logging

from django.db import models
from django.utils import timezone
from common.models import CoreModel

logger = logging.getLogger(__name__)

# ── Purpose registry ─────────────────────────────────────────────────
# Each purpose that has immediate-apply logic registers here.
# Purposes not listed fall through to celery (try_apply returns False).
# Add new purposes as their apply logic is implemented.

INVENTORY_PURPOSES = (
    'inventory_line_add',
    'inventory_qty_change',
    'inventory_line_delete',
    'inventory_cost_change',
    'receipt_line_add',
)


class Pending(CoreModel):
    """Ephemeral queue / staging record (CoreModel only).

    Lightweight by design: no metadata/refs/prefs/comments overhead.

    EVERY Pending record tries to apply itself on save. This is the
    universal behavior — not specific to inventory. On save, new records
    call try_apply() which dispatches based on model_name/purpose to
    the appropriate apply method. If the target record is locked or the
    purpose has no immediate-apply handler yet, the record stays
    unprocessed (dt_processed=0) for celery to pick up later.

    To add a new apply handler:
    1. Add the purpose to the registry above
    2. Add a dispatch branch in try_apply()
    3. Write the _apply_xxx() method
    """
    # Canonical model identifier
    model_name = models.CharField(max_length=255, blank=True, null=True)
    record_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=120, blank=True, null=True)
    dt_processed = models.BigIntegerField(default=0, db_index=True)
    sequence = models.PositiveIntegerField(default=0, help_text="Order within a connection. 0 = unordered.")
    attempts = models.PositiveIntegerField(default=0)
    changes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'pending'
        indexes = [
            models.Index(fields=['model_name']),
            models.Index(fields=['record_id']),
            models.Index(fields=['dt_processed']),
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.dt_processed == 0:
            self.try_apply()

    def try_apply(self):
        """Try to apply this pending record immediately.

        Called automatically on every new Pending save. Dispatches
        based on model_name/purpose to the appropriate apply method.

        Returns True if applied, False if queued for celery.
        Reasons for False: target locked, no handler for this
        purpose yet, or an error during apply.
        """
        if self.is_processed():
            return True

        # ── Inventory ────────────────────────────────────────────
        if self.model_name == 'item' and self.purpose in INVENTORY_PURPOSES:
            return self._apply_inventory()

        # ── Payment application ──────────────────────────────────
        if self.purpose == 'payment_application':
            return self._apply_payment()

        # ── Future handlers ──────────────────────────────────────
        # if self.purpose == 'ledger_sync':
        #     return self._apply_ledger_sync()
        # if self.purpose == 'denorm_refs':
        #     return self._apply_denorm()
        # if self.purpose == 'sync.bundle_out':
        #     return self._apply_sync_bundle()

        # No handler yet — celery will process
        return False

    def _apply_inventory(self):
        """Apply inventory quantity deltas to the target Item.

        Uses select_for_update(nowait=True). If the item is locked
        (database row lock or OperationalError), returns False and
        leaves this record for celery.
        """
        from django.db import transaction as db_transaction, OperationalError
        from decimal import Decimal
        from apps.products.models import Item

        item_id = int(self.record_id) if self.record_id else None
        if not item_id:
            return False

        data = self.changes if isinstance(self.changes, dict) else (self.config or {})
        if not data:
            return False

        try:
            with db_transaction.atomic():
                try:
                    item = Item.objects.select_for_update(nowait=True).get(pk=item_id)
                except Item.DoesNotExist:
                    logger.warning(f"Pending {self.pk}: Item {item_id} not found")
                    return False

                quantity = item.quantity or {}

                # Apply deltas from the pending data
                for field in ('on_so', 'on_po', 'on_wo', 'on_p', 'on_in', 'on_r', 'on_hand'):
                    delta = data.get(field, 0) or 0
                    if delta:
                        current = Decimal(str(quantity.get(field, 0) or 0))
                        quantity[field] = float(current + Decimal(str(delta)))

                # Recompute available
                alloc = Decimal(str(quantity.get('allocated', 0) or 0))
                quantity['available'] = float(
                    Decimal(str(quantity.get('on_hand', 0) or 0)) - alloc
                )

                Item.objects.filter(pk=item_id).update(quantity=quantity)
                self.mark_processed(save=True)

            logger.debug(f"Pending {self.pk} applied to item {item_id}")
            return True

        except OperationalError:
            # Row locked — celery will pick this up
            logger.debug(f"Pending {self.pk}: Item {item_id} locked, queued for celery")
            return False

    def _apply_payment(self):
        """Apply payment to invoice. Delegates to payment_pending service."""
        try:
            from apps.transactions.services.payment_pending import apply_payment_pending
            return apply_payment_pending(self)
        except Exception:
            logger.debug("Pending %s: payment apply failed, queued for celery", self.pk, exc_info=True)
            return False

    def mark_processed(self, save: bool = True):
        if self.dt_processed == 0:
            self.dt_processed = int(timezone.now().timestamp() * 1000)
            if save:
                self.save(update_fields=['dt_processed', 'dt_modified', 'version'])
        return self.dt_processed

    def is_processed(self):
        return self.dt_processed > 0

    def __str__(self):
        return f"{self.model_name}:{self.record_id} (processed={self.is_processed()})"