"""
Transaction signals — inventory tracking and header-link maintenance.

Signal factory eliminates ~600 lines of copy-pasted code for 5 line types.
Each line model (QuoteLine, OrderLine, InvoiceLine, PurchaseLine,
WorkOrderLine) registers the same pre_save/post_save/post_delete pattern via
``register_line_inventory_signals()`` and ``register_line_header_links()``.

Header-level status-change + notification signals remain explicit because
their logic genuinely differs per model.
"""
from __future__ import annotations
import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
from django.db.models.signals import post_save, pre_save, post_delete
from common.allie_capture import allie_capture as _allie
from django.dispatch import receiver
from apps.transactions.models import (
    QuoteLine, OrderLine, InvoiceLine, PurchaseLine, WorkOrderLine,
    Quote, Order, Invoice, Cash, Purchase, WorkOrder, Receipt, ReceiptLine,
)
from apps.transactions.services.notify_email import TransactionEmailService


# =============================================================================
# HELPERS
# =============================================================================

def _ensure_refs_dict(refs):
    """Ensure refs is a dict, handling JSON string case."""
    if refs is None:
        return {}
    if isinstance(refs, str):
        try:
            return json.loads(refs)
        except (json.JSONDecodeError, TypeError):
            return {}
    return refs


def _resolve_item_id(line) -> int | None:
    """Extract item ID from any line's ``item`` JSONField or item_fk FK."""
    # Try the FK field first (authoritative)
    fk_id = getattr(line, 'item_fk_id', None)
    if fk_id:
        return fk_id
    # Fall back to JSON item dict
    item = getattr(line, 'item', {}) or {}
    return item.get('id_num') or item.get('id') or item.get('item_id')


def _get_quantity(line) -> Decimal:
    """Get the staged quantity from any line type."""
    qty = getattr(line, 'quantity', {}) or {}
    staged = qty.get('active', 0) or 0
    return Decimal(str(staged))


def _emit_line_event(event_type: str, line, transaction, quantity_before=None):
    """Emit inventory event for LLM observational learning."""
    try:
        from apps.ai_assistant.services.event_emitter import (
            InventoryEventEmitter,
            is_inventory_events_enabled,
        )
        if not is_inventory_events_enabled():
            return
        InventoryEventEmitter.emit_line_event(
            event_type=event_type,
            line=line,
            transaction=transaction,
            quantity_before=quantity_before,
        )
    except Exception:
        pass  # Silent fail - don't break transaction processing


# =============================================================================
# GENERIC SIGNAL FACTORIES
# =============================================================================

def register_line_inventory_signals(
    line_model,
    parent_attr: str,
    parent_model_key: str,
    transaction_type: str,
):
    """Register pre_save / post_save / post_delete inventory-tracking signals.

    Parameters
    ----------
    line_model : Model class
        e.g. ``OrderLine``
    parent_attr : str
        Attribute on the line that points to the parent header, e.g. ``"order"``
    parent_model_key : str
        Key passed to ``LineItemService``, e.g. ``"order"``
    transaction_type : str
        Inventory bucket key, e.g. ``"order"``
    """

    @receiver(pre_save, sender=line_model)
    def track_quantity_change(sender, instance, **kwargs):
        if instance.pk:
            try:
                original = sender.objects.get(pk=instance.pk)
                instance._original_quantity = _get_quantity(original)
                instance._original_item_id = _resolve_item_id(original)
            except sender.DoesNotExist:
                instance._original_quantity = Decimal('0')
                instance._original_item_id = None
        else:
            instance._original_quantity = Decimal('0')
            instance._original_item_id = None

    @receiver(post_save, sender=line_model)
    def update_inventory_on_save(sender, instance, created, **kwargs):
        if getattr(instance, '_pending_created', False):
            return

        from apps.transactions.services.line_manage import LineItemService

        item_id = _resolve_item_id(instance)
        if not item_id:
            return

        parent = getattr(instance, parent_attr, None)
        new_qty = _get_quantity(instance)
        original_qty = getattr(instance, '_original_quantity', Decimal('0'))
        service = LineItemService(create_pending=True)

        if created:
            if new_qty > 0:
                service._create_pending_for_new_line(
                    parent=parent,
                    parent_model_key=parent_model_key,
                    line=instance,
                    line_data={'quantity': {'staged': float(new_qty), 'active': float(new_qty)}, 'item': instance.item or {}},
                )
                # Emit inventory event for LLM learning
                _emit_line_event(f'{transaction_type}_line_add', instance, parent, None)
        else:
            original_item_id = getattr(instance, '_original_item_id', None)

            if original_item_id and original_item_id != item_id:
                # Item changed — reverse old, add new
                if original_qty > 0:
                    service._create_pending_for_line_delete(
                        transaction=parent,
                        transaction_type=transaction_type,
                        line=instance,
                        quantity_released=float(original_qty),
                    )
                if new_qty > 0:
                    service._create_pending_for_new_line(
                        parent=parent,
                        parent_model_key=parent_model_key,
                        line=instance,
                        line_data={'quantity': {'staged': float(new_qty), 'active': float(new_qty)}, 'item': instance.item or {}},
                    )
                # Emit inventory event for item change
                _emit_line_event(f'{transaction_type}_line_item_change', instance, parent, original_qty)
            else:
                delta = float(new_qty - original_qty)
                if delta != 0:
                    service._create_pending_for_qty_change(
                        transaction=parent,
                        transaction_type=transaction_type,
                        line=instance,
                        quantity_delta=delta,
                    )
                    # Emit inventory event for quantity change
                    _emit_line_event(f'{transaction_type}_line_update', instance, parent, original_qty)

    @receiver(post_delete, sender=line_model)
    def update_inventory_on_delete(sender, instance, **kwargs):
        from apps.transactions.services.line_manage import LineItemService

        item_id = _resolve_item_id(instance)
        if not item_id:
            return

        qty = _get_quantity(instance)
        if qty > 0:
            parent = getattr(instance, parent_attr, None)
            service = LineItemService(create_pending=True)
            service._create_pending_for_line_delete(
                transaction=parent,
                transaction_type=transaction_type,
                line=instance,
                quantity_released=float(qty),
            )
            # Emit inventory event for LLM learning
            _emit_line_event(f'{transaction_type}_line_delete', instance, parent, qty)


def register_line_header_links(line_model, parent_attr: str, link_key: str):
    """Register post_save signal that maintains ``refs.links.<link_key>`` on the parent header."""

    @receiver(post_save, sender=line_model)
    def maintain_header_links(sender, instance, created, **kwargs):
        if not created:
            return
        header = getattr(instance, parent_attr, None)
        if not header:
            return
        refs = _ensure_refs_dict(header.refs)
        links = refs.setdefault("links", {})
        lst = links.setdefault(link_key, [])
        if instance.id not in lst:
            lst.append(instance.id)
            header.refs = refs
            header.save(update_fields=["refs", "dt_modified", "version"])


def register_line_totals_signals(line_model, parent_attr: str):
    """Register post_save/post_delete signals that auto-recalculate parent totals.

    When a line is saved or deleted, calls parent.update_sell_cost_totals(persist=True)
    which triggers the matching compute_*_sell_cost_totals() aggregation.

    Wired for all 5 line types: QuoteLine, OrderLine, InvoiceLine,
    PurchaseLine, and WorkOrderLine (see bottom of this file).

    See: readmes/topics/transactions/transactions-totals.md §3 (signal table)
    """

    def _recalc(parent):
        """The one totals engine.

        Receipt inherits the transaction base as of migration 0032, so it has
        update_sell_cost_totals like every other header and takes the first branch. The
        fallback stays for any parent that does not.
        """
        if hasattr(parent, 'update_sell_cost_totals'):
            parent.update_sell_cost_totals(persist=True)
        else:
            from apps.transactions.services.pricing.totals_compute import recalculate_totals
            recalculate_totals(parent.pk, parent._meta.model_name)
            parent.refresh_from_db(fields=['totals'])

    @receiver(post_save, sender=line_model)
    def update_totals_on_save(sender, instance, **kwargs):
        parent = getattr(instance, parent_attr, None)
        if parent:
            _recalc(parent)
            # The engine wrote this line's totals to the database; the caller holds this instance.
            instance.refresh_from_db(fields=['totals'])

    @receiver(post_delete, sender=line_model)
    def update_totals_on_delete(sender, instance, **kwargs):
        parent = getattr(instance, parent_attr, None)
        if parent:
            _recalc(parent)


# =============================================================================
# REGISTER ALL 6 LINE TYPES
#
# All 6 line types get inventory tracking, header-link maintenance,
# AND totals auto-recalc signals.
# See: readmes/topics/transactions/transactions-totals.md §3 (signal table)
#
# ReceiptLine joined 2026-09-21 (D10). Receiving used to hand-write its own Pending on
# create only, so a receipt-line edit or delete moved the money and not the stock.
# Bill: "every change in inventory and cash should generate a pending record."
# =============================================================================

_LINE_CONFIG = [
    # (model,         parent_attr,  model_key,    txn_type,         link_key)
    (QuoteLine,   'parent',     'quote',   'quote',       'quote_line'),
    (OrderLine,      'order',      'order',      'order',          'order_line'),
    (InvoiceLine,    'invoice',    'invoice',    'invoice',        'invoice_line'),
    (PurchaseLine,   'purchase',   'purchase',   'purchase',       'purchase_line'),
    (WorkOrderLine,  'workorder',  'workorder',  'workorder',      'workorder_line'),
    (ReceiptLine,    'receipt',    'receipt',    'receipt',        'receipt_line'),
]

for _model, _parent, _key, _txn, _link in _LINE_CONFIG:
    register_line_inventory_signals(_model, _parent, _key, _txn)
    register_line_header_links(_model, _parent, _link)

# Line types that auto-recalculate parent header totals on save/delete.
# (Previously only QuoteLine was wired; all types added Feb 2026.)
register_line_totals_signals(QuoteLine, 'parent')
register_line_totals_signals(OrderLine, 'order')
register_line_totals_signals(InvoiceLine, 'invoice')
register_line_totals_signals(PurchaseLine, 'purchase')
register_line_totals_signals(WorkOrderLine, 'workorder')
# A payable's money comes from its own lines (Bill, 2026-09-19), so a receipt line
# recalculates its receipt.
register_line_totals_signals(ReceiptLine, 'receipt')


# =============================================================================
# PARENT LINE — a child's active drives its parent line's remaining
# =============================================================================
# readmes/transactions/line-quantity.md. Registered on the model, not in each
# save path, so /save, /wcapi, convert, line_manage and fulfillment all reach the
# parent the same way. Not suppressed by _pending_created: that flag is about
# inventory pending, not about the parent's backlog.

_UNLOADED = object()


def register_line_parent_signals(line_model):
    from apps.transactions.services.line_parent import refresh_parent_line

    model_name = line_model._meta.model_name

    @receiver(post_save, sender=line_model)
    def refresh_parent_on_save(sender, instance, created, **kwargs):
        current_pid = instance.parent_line_id
        current_active = float((instance.quantity or {}).get('active', 0) or 0)
        loaded_pid = getattr(instance, '_loaded_parent_line_id', _UNLOADED)
        loaded_active = getattr(instance, '_loaded_active', _UNLOADED)

        if created or loaded_pid is _UNLOADED or loaded_active is _UNLOADED:
            refresh_parent_line(model_name, current_pid)
        elif loaded_pid != current_pid:
            refresh_parent_line(model_name, loaded_pid)
            refresh_parent_line(model_name, current_pid)
        elif float(loaded_active or 0) != current_active:
            refresh_parent_line(model_name, current_pid)

        instance._loaded_parent_line_id = current_pid
        instance._loaded_active = current_active

    @receiver(post_delete, sender=line_model)
    def refresh_parent_on_delete(sender, instance, **kwargs):
        refresh_parent_line(model_name, instance.parent_line_id)


register_line_parent_signals(OrderLine)
register_line_parent_signals(InvoiceLine)
# The buy chain works the same way: a receipt line reduces the purchase line it received
# against (Bill, 2026-09-19 — one receiving path).
register_line_parent_signals(ReceiptLine)
# A workorder line has no child lines: what happens to it is recorded in its own
# events[], appended by the pending applier (Bill, 2026-09-20).


# =============================================================================
# DOCUMENT DISCOUNT → LINE DISCOUNTS (Bill, 2026-09-19)
# A discount line saved on a quote, order or invoice is spread into the
# product lines' own discounts, then kept at zero as the record of what was
# applied. Every discount and every tax is then a line's.
# =============================================================================

def register_discount_line_spread(line_model):
    @receiver(post_save, sender=line_model)
    def spread_on_save(sender, instance, created, **kwargs):
        if (instance.line_type or '') != 'discount':
            return
        from apps.transactions.services.pricing.document_discount import on_discount_line_saved
        on_discount_line_saved(instance, created)

    @receiver(post_delete, sender=line_model)
    def remove_on_delete(sender, instance, **kwargs):
        if (instance.line_type or '') != 'discount':
            return
        from apps.transactions.services.pricing.document_discount import remove_discount_line
        remove_discount_line(instance)


for _sell_line_model in (QuoteLine, OrderLine, InvoiceLine):
    register_discount_line_spread(_sell_line_model)


# =============================================================================
# HEADER TAX CHANGE → RECOMPUTE
#
# Totals were recomputed only when a line was saved, so a tax rate set or
# changed on the header had no effect until some line was saved again.
# A change to finance (jurisdiction, rate) now recomputes the totals itself.
# recalculate_totals saves with update_fields=['totals', …], which never
# includes finance, so this cannot loop.
# =============================================================================

_RECOMPUTE_FIELDS = ('finance', 'allocations')


def register_header_finance_recompute(header_model):
    """A change to the header's tax settings (finance) or its document-level
    inputs (allocations: discount, shipping, other) recomputes the totals."""
    @receiver(pre_save, sender=header_model)
    def remember_inputs(sender, instance, **kwargs):
        update_fields = kwargs.get('update_fields')
        watched = [f for f in _RECOMPUTE_FIELDS
                   if update_fields is None or f in update_fields]
        if not instance.pk or not watched:
            instance._inputs_before = None
            return
        row = sender.objects.filter(pk=instance.pk).values(*watched).first()
        instance._inputs_before = {f: (row or {}).get(f) or {} for f in watched}

    @receiver(post_save, sender=header_model)
    def recompute_on_input_change(sender, instance, created, **kwargs):
        before = getattr(instance, '_inputs_before', None)
        instance._inputs_before = None
        if created or before is None:
            return
        if any((getattr(instance, f, None) or {}) != old for f, old in before.items()):
            instance.update_sell_cost_totals(persist=True)


# Receipt included since 2026-09-20: its landed cost (allocations.freight / duty /
# handling / vat) is a header input, and without this signal entering it changed nothing.
# The line signal below was already wired, so touching any line corrected the total — which
# is how the defect hid: the money was right whenever anything else happened to be saved.
for _header_model in (Quote, Order, Invoice, Purchase, WorkOrder, Receipt):
    register_header_finance_recompute(_header_model)


# =============================================================================
# HEADER STATUS-CHANGE + NOTIFICATION SIGNALS
# =============================================================================

@receiver(pre_save, sender=Quote)
def track_quote_status_change(sender, instance: Quote, **kwargs):
    if instance.pk:
        try:
            instance._original_status = Quote.objects.get(pk=instance.pk).status
        except Quote.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Quote)
def send_quote_submitted_notification(sender, instance: Quote, created, **kwargs):
    if created or instance.status != instance.STATUS_RELEASED:
        return
    if getattr(instance, '_original_status', None) != instance.STATUS_RELEASED:
        TransactionEmailService.send_quote_submitted_notification(instance)


@receiver(post_save, sender=Order)
def send_order_created_notification(sender, instance: Order, created, **kwargs):
    if not created:
        return
    try:
        TransactionEmailService.send_order_created_notification(instance)
    except Exception as e:
        logger.warning(f"Order notification failed for order {instance.ida}: {e}")


@receiver(pre_save, sender=Invoice)
def track_invoice_status_change(sender, instance: Invoice, **kwargs):
    if instance.pk:
        try:
            instance._original_status = Invoice.objects.get(pk=instance.pk).status
        except Invoice.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Invoice)
def send_invoice_sent_notification(sender, instance: Invoice, created, **kwargs):
    if created or instance.status != instance.STATUS_RELEASED:
        return
    if getattr(instance, '_original_status', None) != instance.STATUS_RELEASED:
        TransactionEmailService.send_invoice_sent_notification(instance)


@receiver(pre_save, sender=Cash)
def track_cash_status_change(sender, instance: Cash, **kwargs):
    if instance.pk:
        try:
            instance._original_status = Cash.objects.get(pk=instance.pk).status
        except Cash.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Cash)
def send_cash_received_notification(sender, instance: Cash, created, **kwargs):
    if created or instance.status != 'completed':
        return
    if getattr(instance, '_original_status', None) != 'completed':
        TransactionEmailService.send_cash_received_notification(instance)


@receiver(post_save, sender=Receipt)
def create_receipt_ledger(sender, instance, created, **kwargs):
    """A payable's ledger echoes the payable, as an invoice's does (Bill, 2026-09-19)."""
    try:
        from apps.accounts.services.ledger_balance import on_receipt_save
        on_receipt_save(instance)
    except Exception:
        import logging
        logging.getLogger('transactions.signals').warning(
            "Failed to create ledger for receipt #%s", instance.pk, exc_info=True)


@receiver(post_save, sender=Cash)
def create_cash_ledger(sender, instance: Cash, created, **kwargs):
    """Create/replace negative ledger record and update org aging balances."""
    try:
        from apps.accounts.services.ledger_balance import on_cash_save
        on_cash_save(instance)
    except Exception:
        import logging
        logging.getLogger('transactions.signals').warning(
            "Failed to create ledger for cash #%s", instance.pk, exc_info=True
        )
    # Detect late-payment erosion (carrying cost)
    try:
        from apps.accounts.services.value_erosion import detect_late_payment
        detect_late_payment(instance)
    except Exception:
        import logging
        logging.getLogger('transactions.signals').warning(
            "Failed to detect late-payment erosion for cash #%s", instance.pk, exc_info=True
        )


@receiver(post_save, sender=Cash)
def update_order_received(sender, instance: Cash, created, **kwargs):
    """When a cash entry references an order, update order.totals.received and balance."""
    if not created:
        return
    try:
        refs = instance.refs if isinstance(instance.refs, dict) else {}
        order_ids = refs.get('order_ids', [])
        source = refs.get('source', {})
        if source.get('type') == 'order' and source.get('id'):
            oid = source['id']
            if oid not in order_ids:
                order_ids = list(order_ids) + [oid]
        if not order_ids:
            return

        from apps.transactions.services.cash.cash_pending import _applied
        from apps.transactions.services.pricing.totals_compute import update_received
        for oid in order_ids:
            try:
                order = Order.objects.get(pk=oid)
            except Order.DoesNotExist:
                continue
            # What an order has received is what has been APPLIED to it, not the face
            # value of every cash record that mentions it. This used to sum p.amount, so
            # a payment split across documents counted in full against each of them, and
            # it read refs.order_ids — a denormalized cache, not a source of truth.
            # convert.py already states the rule: "someone applies it, which creates the
            # application record received is computed from" (fixed 2026-09-20).
            update_received(order, _applied(order_id=oid))
    except Exception:
        import logging
        logging.getLogger('transactions.signals').warning(
            "Failed to update order received for cash #%s", instance.pk, exc_info=True
        )


# =============================================================================
# ALLIE CAPTURE — development process + transaction monitoring
# Fire-and-forget. These receivers never block the request cycle.
# =============================================================================

@receiver(post_save, sender=Order)
def allie_order_event(sender, instance: Order, created, **kwargs):
    event = "order_created" if created else "order_updated"
    _allie(event,
           f"Order #{instance.pk}",
           {"id": instance.pk, "status": getattr(instance, "status", "")})


@receiver(post_save, sender=Invoice)
def allie_invoice_event(sender, instance: Invoice, created, **kwargs):
    status = getattr(instance, "status", "")
    released = getattr(instance, "STATUS_RELEASED", "released")
    complete  = getattr(instance, "STATUS_COMPLETE", "complete")
    # Distinguish the fulfillment boundary from generic updates.
    # order_fulfilled fires on STATUS_RELEASED (standard) or STATUS_COMPLETE
    # (JPods trip invoices — created directly at complete, no released step).
    fulfillment_statuses = {released, complete}
    prev = getattr(instance, "_original_status", None)
    if status in fulfillment_statuses and (created or prev != status):
        event = "order_fulfilled"
    elif created:
        event = "invoice_created"
    else:
        event = "invoice_updated"
    _allie(event,
           f"Invoice #{instance.pk} status={status}",
           {"id": instance.pk, "status": status,
            "order": getattr(instance, "order_id", None)})


@receiver(post_save, sender=Cash)
def allie_cash_event(sender, instance: Cash, created, **kwargs):
    status = getattr(instance, "status", "")
    event = "cash_created" if created else f"cash_{status}"
    _allie(event,
           f"Cash #{instance.pk} status={status}",
           {"id": instance.pk, "status": status})


# =============================================================================
# AGENT BUS — notify Alice of transaction events
# Fire-and-forget. Signal failure must never break the save.
# =============================================================================

def _bus_notify(model_name, instance, created):
    """Send transaction event to Alice via the agent message bus."""
    try:
        from apps.core.services.agent_bus import send_to_bus
        event = 'created' if created else 'updated'
        ida = getattr(instance, 'ida', '') or f'{model_name}({instance.pk})'
        status = getattr(instance, 'status', '')
        total = float(getattr(instance, 'total', 0) or 0)
        balance = float(getattr(instance, 'balance', 0) or 0)
        send_to_bus('wc3', 'alice', f'{model_name} {ida} {event}',
                    category='transaction',
                    context={'model': model_name.lower(), 'id': instance.pk,
                             'ida': ida, 'event': event, 'status': status,
                             'total': total, 'balance': balance})
    except Exception:
        pass


@receiver(post_save, sender=Order)
def bus_order_saved(sender, instance, created, **kwargs):
    _bus_notify('Order', instance, created)


@receiver(post_save, sender=Invoice)
def bus_invoice_saved(sender, instance, created, **kwargs):
    _bus_notify('Invoice', instance, created)


@receiver(post_save, sender=Quote)
def bus_quote_saved(sender, instance, created, **kwargs):
    _bus_notify('Quote', instance, created)


@receiver(post_save, sender=Purchase)
def bus_purchase_saved(sender, instance, created, **kwargs):
    _bus_notify('Purchase', instance, created)


@receiver(post_save, sender=Cash)
def bus_cash_saved(sender, instance, created, **kwargs):
    try:
        from apps.core.services.agent_bus import send_to_bus
        event = 'created' if created else 'updated'
        status = getattr(instance, 'status', '')
        send_to_bus('wc3', 'alice', f'Cash #{instance.pk} {event}',
                    category='transaction',
                    context={'model': 'cash', 'id': instance.pk,
                             'event': event, 'status': status})
    except Exception:
        pass


# =============================================================================
# ALICE AGGREGATE TRACKER — delta updates for dashboard Sum() queries
# Replaces scalar shadow field aggregates with Alice-managed collections.
# =============================================================================

_AGGREGATE_MODELS = [
    (Order, 'order'),
    (Invoice, 'invoice'),
    (Quote, 'quote'),
    (Purchase, 'purchase'),
    (WorkOrder, 'workorder'),
]


def _stash_old_totals(sender, instance, **kwargs):
    """pre_save: stash current totals and status for delta computation."""
    if instance.pk:
        try:
            old = sender.objects.filter(pk=instance.pk).values('totals', 'status').first()
            if old:
                instance._old_totals = old['totals'] or {}
                instance._old_status = old['status'] or ''
                return
        except Exception:
            pass
    instance._old_totals = {}
    instance._old_status = ''


def _apply_aggregate_delta(sender, instance, **kwargs):
    """post_save: apply delta to Alice's aggregate Setting."""
    try:
        from apps.ai_assistant.services.aggregate_tracker import apply_delta
        model_name = sender._meta.model_name
        old_totals = getattr(instance, '_old_totals', {})
        new_totals = getattr(instance, 'totals', None) or {}
        old_status = getattr(instance, '_old_status', '')
        new_status = getattr(instance, 'status', '')
        apply_delta(model_name, old_totals, new_totals, new_status, old_status)
    except Exception:
        logger.debug("Aggregate delta failed for %s #%s", sender.__name__,
                     instance.pk, exc_info=True)


for _agg_model, _agg_name in _AGGREGATE_MODELS:
    pre_save.connect(_stash_old_totals, sender=_agg_model, weak=False)
    post_save.connect(_apply_aggregate_delta, sender=_agg_model, weak=False)