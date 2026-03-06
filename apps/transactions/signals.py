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
from decimal import Decimal
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from apps.transactions.models import (
    ProposalLine, OrderLine, InvoiceLine, PurchaseLine, WorkOrderLine,
    Proposal, Order, Invoice, Payment,
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
    """Extract item ID from any line's ``item`` JSONField."""
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
    TransactionEmailService.send_order_created_notification(instance)


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