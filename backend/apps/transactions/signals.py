"""
Transaction signals — inventory tracking and header-link maintenance.

Signal factory eliminates ~600 lines of copy-pasted code for 5 line types.
Each line model (ProposalLine, OrderLine, InvoiceLine, PurchaseLine,
WorkOrderLine) registers the same pre_save/post_save/post_delete pattern via
``register_line_inventory_signals()`` and ``register_line_header_links()``.

Header-level status-change + notification signals remain explicit because
their logic genuinely differs per model.
"""
from __future__ import annotations
import json
import logging
import subprocess
import pathlib
from decimal import Decimal

logger = logging.getLogger(__name__)
from django.db.models.signals import post_save, pre_save, post_delete

_ALLIE_CAPTURE = pathlib.Path.home() / "Allie" / "scripts" / "allie-capture.py"

def _allie(event: str, message: str = "", data: dict | None = None):
    """Fire-and-forget Allie event capture. Never raises, never blocks request cycle."""
    if not _ALLIE_CAPTURE.exists():
        return
    try:
        args = ["python3", str(_ALLIE_CAPTURE),
                "--source", "webclerk3",
                "--event",  event,
                "--message", message]
        if data:
            args += ["--data", json.dumps(data)]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
from django.dispatch import receiver
from apps.transactions.models import (
    ProposalLine, OrderLine, InvoiceLine, PurchaseLine, WorkOrderLine,
    Proposal, Order, Invoice, Payment, Purchase,
)
from apps.transactions.services.email_notifications import TransactionEmailService


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
    staged = qty.get('staged', 0) or qty.get('active', 0) or 0
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

        from apps.transactions.services.line_item_service import LineItemService

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
        from apps.transactions.services.line_item_service import LineItemService

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

    Wired for all 5 line types: ProposalLine, OrderLine, InvoiceLine,
    PurchaseLine, and WorkOrderLine (see bottom of this file).

    See: readmes/topics/transactions/transactions-totals.md §3 (signal table)
    """

    @receiver(post_save, sender=line_model)
    def update_totals_on_save(sender, instance, **kwargs):
        parent = getattr(instance, parent_attr, None)
        if parent:
            parent.update_sell_cost_totals(persist=True)

    @receiver(post_delete, sender=line_model)
    def update_totals_on_delete(sender, instance, **kwargs):
        parent = getattr(instance, parent_attr, None)
        if parent:
            parent.update_sell_cost_totals(persist=True)


# =============================================================================
# REGISTER ALL 5 LINE TYPES
#
# All 5 line types get inventory tracking, header-link maintenance,
# AND totals auto-recalc signals.
# See: readmes/topics/transactions/transactions-totals.md §3 (signal table)
# =============================================================================

_LINE_CONFIG = [
    # (model,         parent_attr,  model_key,    txn_type,         link_key)
    (ProposalLine,   'parent',     'proposal',   'proposal',       'proposal_line'),
    (OrderLine,      'order',      'order',      'order',          'order_line'),
    (InvoiceLine,    'invoice',    'invoice',    'invoice',        'invoice_line'),
    (PurchaseLine,   'purchase',   'purchase',   'purchase',       'purchase_line'),
    (WorkOrderLine,  'workorder',  'workorder',  'workorder',      'workorder_line'),
]

for _model, _parent, _key, _txn, _link in _LINE_CONFIG:
    register_line_inventory_signals(_model, _parent, _key, _txn)
    register_line_header_links(_model, _parent, _link)

# Line types that auto-recalculate parent header totals on save/delete.
# (Previously only ProposalLine was wired; all types added Feb 2026.)
register_line_totals_signals(ProposalLine, 'parent')
register_line_totals_signals(OrderLine, 'order')
register_line_totals_signals(InvoiceLine, 'invoice')
register_line_totals_signals(PurchaseLine, 'purchase')
register_line_totals_signals(WorkOrderLine, 'workorder')


# =============================================================================
# HEADER STATUS-CHANGE + NOTIFICATION SIGNALS
# =============================================================================

@receiver(pre_save, sender=Proposal)
def track_proposal_status_change(sender, instance: Proposal, **kwargs):
    if instance.pk:
        try:
            instance._original_status = Proposal.objects.get(pk=instance.pk).status
        except Proposal.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Proposal)
def send_proposal_submitted_notification(sender, instance: Proposal, created, **kwargs):
    if created or instance.status != instance.STATUS_RELEASED:
        return
    if getattr(instance, '_original_status', None) != instance.STATUS_RELEASED:
        TransactionEmailService.send_proposal_submitted_notification(instance)


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


@receiver(pre_save, sender=Payment)
def track_payment_status_change(sender, instance: Payment, **kwargs):
    if instance.pk:
        try:
            instance._original_status = Payment.objects.get(pk=instance.pk).status
        except Payment.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Payment)
def send_payment_received_notification(sender, instance: Payment, created, **kwargs):
    if created or instance.status != 'completed':
        return
    if getattr(instance, '_original_status', None) != 'completed':
        TransactionEmailService.send_payment_received_notification(instance)


@receiver(post_save, sender=Payment)
def create_payment_ledger(sender, instance: Payment, created, **kwargs):
    """Create/replace negative ledger record and update org aging balances."""
    try:
        from apps.accounts.services.ledger_balance import on_payment_save
        on_payment_save(instance)
    except Exception:
        import logging
        logging.getLogger('transactions.signals').warning(
            "Failed to create ledger for payment #%s", instance.pk, exc_info=True
        )
    # Detect late-payment erosion (carrying cost)
    try:
        from apps.accounts.services.erosion import detect_late_payment
        detect_late_payment(instance)
    except Exception:
        import logging
        logging.getLogger('transactions.signals').warning(
            "Failed to detect late-payment erosion for payment #%s", instance.pk, exc_info=True
        )


@receiver(post_save, sender=Payment)
def update_order_received(sender, instance: Payment, created, **kwargs):
    """When a payment references an order, update order.totals.received and balance."""
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

        from decimal import Decimal
        for oid in order_ids:
            try:
                order = Order.objects.get(pk=oid)
            except Order.DoesNotExist:
                continue
            # Sum all completed payments linked to this order
            all_payments = Payment.objects.filter(
                status='completed', is_active=True,
            )
            total_received = Decimal('0')
            for p in all_payments:
                p_refs = p.refs if isinstance(p.refs, dict) else {}
                p_order_ids = p_refs.get('order_ids', [])
                p_source = p_refs.get('source', {})
                if oid in p_order_ids or (p_source.get('type') == 'order' and p_source.get('id') == oid):
                    total_received += Decimal(str(p.amount or 0))

            totals = order.totals if isinstance(order.totals, dict) else {}
            order_total = Decimal(str(totals.get('total', 0)))
            totals['received'] = float(total_received)
            totals['balance'] = float(order_total - total_received)
            # Use queryset update to avoid version conflicts with open browser sessions
            Order.objects.filter(pk=oid).update(
                totals=totals,
                balance=order_total - total_received,
            )
    except Exception:
        import logging
        logging.getLogger('transactions.signals').warning(
            "Failed to update order received for payment #%s", instance.pk, exc_info=True
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


@receiver(post_save, sender=Payment)
def allie_payment_event(sender, instance: Payment, created, **kwargs):
    status = getattr(instance, "status", "")
    event = "payment_created" if created else f"payment_{status}"
    _allie(event,
           f"Payment #{instance.pk} status={status}",
           {"id": instance.pk, "status": status})


# =============================================================================
# AGENT BUS — notify Alice of transaction events
# Fire-and-forget. Signal failure must never break the save.
# =============================================================================

def _bus_notify(model_name, instance, created):
    """Send transaction event to Alice via the agent message bus."""
    try:
        from apps.core.services.agent_bus_bridge import send_to_bus
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


@receiver(post_save, sender=Proposal)
def bus_proposal_saved(sender, instance, created, **kwargs):
    _bus_notify('Proposal', instance, created)


@receiver(post_save, sender=Purchase)
def bus_purchase_saved(sender, instance, created, **kwargs):
    _bus_notify('Purchase', instance, created)


@receiver(post_save, sender=Payment)
def bus_payment_saved(sender, instance, created, **kwargs):
    try:
        from apps.core.services.agent_bus_bridge import send_to_bus
        event = 'created' if created else 'updated'
        status = getattr(instance, 'status', '')
        send_to_bus('wc3', 'alice', f'Payment #{instance.pk} {event}',
                    category='transaction',
                    context={'model': 'payment', 'id': instance.pk,
                             'event': event, 'status': status})
    except Exception:
        pass