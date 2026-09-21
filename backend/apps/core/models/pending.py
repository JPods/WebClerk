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
    'opening_balance',     # stock a rebalance puts on the shelf, in a new layer
    'allocation',        # a salesperson setting goods aside, or giving them back
    'line_event',          # a change to a line: moves the buckets and records itself
)


class LayerLocked(Exception):
    """The layer a pending must move is locked; the pending waits, item and all."""


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

        applied = None
        # ── Inventory ────────────────────────────────────────────
        if self.model_name == 'item' and self.purpose in INVENTORY_PURPOSES:
            applied = self._apply_inventory()

        # ── Cash application (AR — Invoice) ───────────────────
        elif self.purpose == 'cash_application':
            applied = self._apply_cash()

        # ── Cash application (AP — Receipt) ───────────────────
        elif self.purpose == 'cash_application_receipt':
            applied = self._apply_receipt_cash()

        if applied is not None:
            # Every cash and inventory event, checked once it commits (BALANCE_EVENT_LOG).
            from apps.core.services.balance_checker import log_balance_event
            log_balance_event(self, applied)
            return applied

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

                # Apply deltas from the pending data. 'allocated' is here because a
                # salesperson's allocation is a movement like any other — entered, never
                # derived (Bill, 2026-09-19) — and it must reach available the same way.
                for field in ('on_so', 'on_po', 'on_wo', 'on_qt', 'on_in', 'on_rc', 'on_hand',
                              'allocated'):
                    delta = data.get(field, 0) or 0
                    if delta:
                        current = Decimal(str(quantity.get(field, 0) or 0))
                        quantity[field] = float(current + Decimal(str(delta)))

                # Recompute available
                alloc = Decimal(str(quantity.get('allocated', 0) or 0))
                quantity['available'] = float(
                    Decimal(str(quantity.get('on_hand', 0) or 0)) - alloc
                )

                # The layer moves with on_hand, in this transaction: both saved, or
                # neither and this record stays unprocessed (Bill, 2026-09-21).
                self._apply_layer(item_id, data)

                Item.objects.filter(pk=item_id).update(quantity=quantity)
                self._record_line_event()
                self.mark_processed(save=True)

            logger.debug(f"Pending {self.pk} applied to item {item_id}")
            return True

        except (OperationalError, LayerLocked):
            # Row locked — celery will pick this up
            logger.debug(f"Pending {self.pk}: Item {item_id} or its layer locked, queued for celery")
            return False

    def _apply_layer(self, item_id, data):
        """Move the layer this pending names by the pending's on_hand.

        Bill, 2026-09-21: *"Layers must change with items."* A pending that moves on_hand
        carries its layer in ``changes['layer']``: ``{'layer_id': n}`` to change the one a
        line already has, or ``{'create': {...}, 'line_id': n}`` to land new goods in a new
        layer and point the receipt line at it (no ``line_id`` for an opening balance). Anything that cannot be done raises, so
        the item's change rolls back with it.

        Receipts carry a layer today. Invoices issuing from layers, workorder
        completions and adjustments join next; until then a pending without a layer
        moves the item alone.
        """
        from decimal import Decimal
        from django.core.exceptions import ValidationError

        spec = data.get('layer')
        on_hand = Decimal(str(data.get('on_hand', 0) or 0))
        if data.get('type_id') == 'RC' and on_hand and not spec:
            raise ValidationError({'layer': f'Pending {self.pk} moves on_hand by {on_hand} '
                                            'for a receipt and names no layer'})
        if not spec or not on_hand:
            return

        from apps.products.models.inventory_layer import InventoryLayer, InventoryMovement
        from apps.products.services.inventory.inventory_layers import create_layer, recalc_average_cost

        if spec.get('layer_id'):
            layer = InventoryLayer.objects.select_for_update(nowait=True).select_related(
                'warehouse').get(pk=spec['layer_id'])
            if layer.is_locked:
                raise LayerLocked(layer.pk)
            q = dict(layer.quantity or {})
            received = Decimal(str(q.get('received', 0) or 0)) + on_hand
            used = Decimal(str(q.get('issued', 0) or 0)) + Decimal(str(q.get('scrapped', 0) or 0))
            if received < used:
                raise ValidationError({'layer': f'layer {layer.pk} would hold {received} received '
                                                f'against {used} already issued or scrapped'})
            q['received'] = float(received)
            layer.quantity = q
            layer.save(update_fields=['quantity', 'dt_modified', 'version'])
            InventoryMovement.objects.create(
                item_id=item_id,
                warehouse=layer.warehouse,
                inventory_layer=layer,
                site_code=layer.warehouse.site_code,
                movement_type=InventoryMovement.MOVEMENT_ADJUST,
                quantity=on_hand,
                reason=str(data.get('reason') or self.purpose)[:120],
                source_doc_type=layer.source_doc_type,
                source_doc_id=layer.source_doc_id,
            )
            recalc_average_cost(item_id)
            return

        create = spec.get('create') or {}
        if on_hand <= 0:
            raise ValidationError({'layer': f'Pending {self.pk} would create a layer '
                                            f'holding {on_hand}'})
        layer = create_layer(
            item_id,
            create['warehouse_id'],
            on_hand,
            Decimal(str(create.get('unit_cost') or 0)),
            source_doc_type=create.get('source_doc_type', ''),
            source_doc_id=create.get('source_doc_id'),
            lot=create.get('lot', ''),
            serial_batch=create.get('serial_batch', ''),
            reason=str(data.get('reason') or 'Receipt')[:120],
        )
        if not spec.get('line_id'):
            return                      # an opening balance: no line to point at the layer
        from apps.transactions.models import ReceiptLine
        # .update(): the line's own save would run its signals again inside this apply.
        if not ReceiptLine.objects.filter(pk=spec.get('line_id')).update(inventory_layer=layer):
            raise ValidationError({'layer': f"receipt line {spec.get('line_id')} not found "
                                            f"for layer {layer.pk}"})

    def _record_line_event(self):
        """Append this pending's event to the record it belongs to, in the same
        transaction that moved the money or the stock.

        Bill, 2026-09-20: *"all changes in cash and inventory should be posted via
        pending records... They generate a pending record each for 3 and 7. They get
        applied by the standard behavior."* So the movement and the record of it are one
        apply under one lock — two people completing at the same instant serialize, and
        neither can clobber the other's event.

        The event's ``id`` makes it idempotent: a re-apply finds it already there.
        """
        from django.apps import apps as dj_apps

        config = self.config if isinstance(self.config, dict) else {}
        event = config.get('event')
        # A line for an inventory movement, a document for a cash application — the same
        # array, the same append, whichever record the event belongs to.
        line_model = config.get('event_model') or config.get('line_model')
        line_id = config.get('event_record_id') or config.get('line_id')
        if not (isinstance(event, dict) and line_model and line_id):
            return

        try:
            LineModel = dj_apps.get_model('transactions', line_model)
        except LookupError:
            logger.warning("Pending %s: unknown line model %s", self.pk, line_model)
            return

        line = LineModel.objects.select_for_update().filter(pk=line_id).first()
        if line is None:
            logger.warning("Pending %s: %s #%s not found for its event", self.pk, line_model, line_id)
            return

        events = list(line.events or []) if hasattr(line, 'events') else None
        if events is None:
            logger.warning("Pending %s: %s has no events field", self.pk, line_model)
            return
        if any(isinstance(e, dict) and e.get('id') == event.get('id') for e in events):
            return                      # already recorded — an apply can run twice safely

        events.append(event)
        line.events = events
        # A line recomputes its remaining from its events on save; a document has no
        # quantity to recompute, so it saves the array alone.
        fields = ['events', 'dt_modified', 'version']
        if hasattr(line, 'quantity'):
            fields = ['events', 'quantity', 'status', 'dt_modified', 'version']
        line.save(update_fields=fields)

    def _apply_cash(self):
        """Apply cash to invoice (AR). Delegates to cash_pending service."""
        try:
            from apps.transactions.services.cash.cash_pending import apply_cash_pending
            return apply_cash_pending(self)
        except Exception:
            logger.debug("Pending %s: cash apply failed, queued for celery", self.pk, exc_info=True)
            return False

    def _apply_receipt_cash(self):
        """Apply cash to receipt (AP). Delegates to cash_pending_receipt service."""
        try:
            from apps.transactions.services.cash.cash_pending_receipt import apply_receipt_cash_pending
            return apply_receipt_cash_pending(self)
        except Exception:
            logger.debug("Pending %s: receipt cash apply failed, queued for celery", self.pk, exc_info=True)
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