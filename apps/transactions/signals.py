from __future__ import annotations
import json
from decimal import Decimal
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from apps.transactions.models import ProposalLine, OrderLine, InvoiceLine, PurchaseLine, WorkOrderLine, Proposal, Order, Invoice, Payment
from apps.transactions.services.email_notifications import TransactionEmailService


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


@receiver(post_save, sender=ProposalLine)
def maintain_proposal_links(sender, instance: ProposalLine, created, **kwargs):
    if not created:
        return
    header = instance.parent
    if not header:
        return
    refs = _ensure_refs_dict(header.refs)
    links = refs.setdefault("links", {})
    lst = links.setdefault("proposal_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])


@receiver(post_save, sender=ProposalLine)
def update_proposal_totals_on_line_save(sender, instance: ProposalLine, **kwargs):
    """Update proposal totals when a line is saved."""
    proposal = instance.parent
    if proposal:
        proposal.update_sell_cost_totals(persist=True)


@receiver(post_delete, sender=ProposalLine)
def update_proposal_totals_on_line_delete(sender, instance: ProposalLine, **kwargs):
    """Update proposal totals when a line is deleted."""
    proposal = instance.parent
    if proposal:
        proposal.update_sell_cost_totals(persist=True)

@receiver(post_save, sender=OrderLine)
def maintain_order_links(sender, instance: OrderLine, created, **kwargs):
    if not created:
        return
    header = instance.order
    if not header:
        return
    refs = _ensure_refs_dict(header.refs)
    links = refs.setdefault("links", {})
    lst = links.setdefault("order_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])

@receiver(post_save, sender=InvoiceLine)
def maintain_invoice_links(sender, instance: InvoiceLine, created, **kwargs):
    if not created:
        return
    header = instance.invoice
    if not header:
        return
    refs = _ensure_refs_dict(header.refs)
    links = refs.setdefault("links", {})
    lst = links.setdefault("invoice_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])


@receiver(pre_save, sender=Proposal)
def track_proposal_status_change(sender, instance: Proposal, **kwargs):
    """Track original status for proposal status change detection."""
    if instance.pk:
        try:
            original = Proposal.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Proposal.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Proposal)
def send_proposal_submitted_notification(sender, instance: Proposal, created, **kwargs):
    """Send email when proposal status changes to released (submitted)."""
    if created or instance.status != instance.STATUS_RELEASED:
        return

    # Check if this is a status change to released
    if getattr(instance, '_original_status', None) != instance.STATUS_RELEASED:
        TransactionEmailService.send_proposal_submitted_notification(instance)


@receiver(post_save, sender=Order)
def send_order_created_notification(sender, instance: Order, created, **kwargs):
    """Send email when order is created."""
    if not created:
        return

    TransactionEmailService.send_order_created_notification(instance)


@receiver(pre_save, sender=Invoice)
def track_invoice_status_change(sender, instance: Invoice, **kwargs):
    """Track original status for invoice status change detection."""
    if instance.pk:
        try:
            original = Invoice.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Invoice.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Invoice)
def send_invoice_sent_notification(sender, instance: Invoice, created, **kwargs):
    """Send email when invoice status changes to released (sent)."""
    if created or instance.status != instance.STATUS_RELEASED:
        return

    # Check if this is a status change to released
    if getattr(instance, '_original_status', None) != instance.STATUS_RELEASED:
        TransactionEmailService.send_invoice_sent_notification(instance)


@receiver(pre_save, sender=Payment)
def track_payment_status_change(sender, instance: Payment, **kwargs):
    """Track original status for payment status change detection."""
    if instance.pk:
        try:
            original = Payment.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Payment.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Payment)
def send_payment_received_notification(sender, instance: Payment, created, **kwargs):
    """Send email when payment status changes to completed."""
    if created or instance.status != 'completed':
        return

    # Check if this is a status change to completed
    if getattr(instance, '_original_status', None) != 'completed':
        TransactionEmailService.send_payment_received_notification(instance)


# =============================================================================
# SALES-SIDE LINE INVENTORY TRACKING (Fallback for direct model saves)
# =============================================================================
# Primary inventory tracking flows through LineItemService (DRF views, save_view).
# These signals act as a fallback for direct model.save() calls (imports, shell, tests).
# The _pending_created flag prevents duplicates when LineItemService handles it.
# =============================================================================

def _resolve_item_id_from_line(line) -> int | None:
    """Extract item ID from a line's item JSONField (works for all line types)."""
    item = getattr(line, 'item', {}) or {}
    return item.get('id_num') or item.get('id') or item.get('item_id')


def _get_line_quantity(line) -> Decimal:
    """Get the placed quantity from a line (works for all line types)."""
    qty = getattr(line, 'quantity', {}) or {}
    placed = qty.get('placed', 0) or 0
    return Decimal(str(placed))


# --- ProposalLine Signals ---
@receiver(pre_save, sender=ProposalLine)
def track_proposal_line_quantity_change(sender, instance: ProposalLine, **kwargs):
    """Track original quantity for proposal line quantity change detection."""
    if instance.pk:
        try:
            original = ProposalLine.objects.get(pk=instance.pk)
            instance._original_quantity = _get_line_quantity(original)
            instance._original_item_id = _resolve_item_id_from_line(original)
        except ProposalLine.DoesNotExist:
            instance._original_quantity = Decimal('0')
            instance._original_item_id = None
    else:
        instance._original_quantity = Decimal('0')
        instance._original_item_id = None


@receiver(post_save, sender=ProposalLine)
def update_inventory_on_proposal_line_save(sender, instance: ProposalLine, created, **kwargs):
    """Create inventory delta for on_p (forecast) when ProposalLine changes."""
    if getattr(instance, '_pending_created', False):
        return
    
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_line(instance)
    if not item_id:
        return
    
    new_qty = _get_line_quantity(instance)
    service = LineItemService(create_pending=True)
    
    if created:
        if new_qty > 0:
            service._create_pending_for_new_line(
                parent=instance.proposal,
                parent_model_key='proposal',
                line=instance,
                line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
            )
    else:
        original_qty = getattr(instance, '_original_quantity', Decimal('0'))
        original_item_id = getattr(instance, '_original_item_id', None)
        
        if original_item_id and original_item_id != item_id:
            if original_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.proposal,
                    transaction_type='proposal',
                    line=instance,
                    quantity_released=float(original_qty),
                )
            if new_qty > 0:
                service._create_pending_for_new_line(
                    parent=instance.proposal,
                    parent_model_key='proposal',
                    line=instance,
                    line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
                )
        else:
            delta = float(new_qty - original_qty)
            if delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.proposal,
                    transaction_type='proposal',
                    line=instance,
                    quantity_delta=delta,
                )


@receiver(post_delete, sender=ProposalLine)
def update_inventory_on_proposal_line_delete(sender, instance: ProposalLine, **kwargs):
    """Create negative inventory delta when ProposalLine is deleted."""
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_line(instance)
    if not item_id:
        return
    
    qty = _get_line_quantity(instance)
    if qty > 0:
        service = LineItemService(create_pending=True)
        service._create_pending_for_line_delete(
            transaction=instance.proposal,
            transaction_type='proposal',
            line=instance,
            quantity_released=float(qty),
        )


# --- OrderLine Signals ---
@receiver(pre_save, sender=OrderLine)
def track_order_line_quantity_change(sender, instance: OrderLine, **kwargs):
    """Track original quantity for order line quantity change detection."""
    if instance.pk:
        try:
            original = OrderLine.objects.get(pk=instance.pk)
            instance._original_quantity = _get_line_quantity(original)
            instance._original_item_id = _resolve_item_id_from_line(original)
        except OrderLine.DoesNotExist:
            instance._original_quantity = Decimal('0')
            instance._original_item_id = None
    else:
        instance._original_quantity = Decimal('0')
        instance._original_item_id = None


@receiver(post_save, sender=OrderLine)
def update_inventory_on_order_line_save(sender, instance: OrderLine, created, **kwargs):
    """Create inventory delta for on_so (reservation) when OrderLine changes."""
    if getattr(instance, '_pending_created', False):
        return
    
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_line(instance)
    if not item_id:
        return
    
    new_qty = _get_line_quantity(instance)
    service = LineItemService(create_pending=True)
    
    if created:
        if new_qty > 0:
            service._create_pending_for_new_line(
                parent=instance.order,
                parent_model_key='order',
                line=instance,
                line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
            )
    else:
        original_qty = getattr(instance, '_original_quantity', Decimal('0'))
        original_item_id = getattr(instance, '_original_item_id', None)
        
        if original_item_id and original_item_id != item_id:
            if original_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.order,
                    transaction_type='sales_order',
                    line=instance,
                    quantity_released=float(original_qty),
                )
            if new_qty > 0:
                service._create_pending_for_new_line(
                    parent=instance.order,
                    parent_model_key='order',
                    line=instance,
                    line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
                )
        else:
            delta = float(new_qty - original_qty)
            if delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.order,
                    transaction_type='sales_order',
                    line=instance,
                    quantity_delta=delta,
                )


@receiver(post_delete, sender=OrderLine)
def update_inventory_on_order_line_delete(sender, instance: OrderLine, **kwargs):
    """Create negative inventory delta when OrderLine is deleted."""
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_line(instance)
    if not item_id:
        return
    
    qty = _get_line_quantity(instance)
    if qty > 0:
        service = LineItemService(create_pending=True)
        service._create_pending_for_line_delete(
            transaction=instance.order,
            transaction_type='sales_order',
            line=instance,
            quantity_released=float(qty),
        )


# --- InvoiceLine Signals ---
@receiver(pre_save, sender=InvoiceLine)
def track_invoice_line_quantity_change(sender, instance: InvoiceLine, **kwargs):
    """Track original quantity for invoice line quantity change detection."""
    if instance.pk:
        try:
            original = InvoiceLine.objects.get(pk=instance.pk)
            instance._original_quantity = _get_line_quantity(original)
            instance._original_item_id = _resolve_item_id_from_line(original)
        except InvoiceLine.DoesNotExist:
            instance._original_quantity = Decimal('0')
            instance._original_item_id = None
    else:
        instance._original_quantity = Decimal('0')
        instance._original_item_id = None


@receiver(post_save, sender=InvoiceLine)
def update_inventory_on_invoice_line_save(sender, instance: InvoiceLine, created, **kwargs):
    """Create inventory delta for on_in (issuance) when InvoiceLine changes."""
    if getattr(instance, '_pending_created', False):
        return
    
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_line(instance)
    if not item_id:
        return
    
    new_qty = _get_line_quantity(instance)
    service = LineItemService(create_pending=True)
    
    if created:
        if new_qty > 0:
            service._create_pending_for_new_line(
                parent=instance.invoice,
                parent_model_key='invoice',
                line=instance,
                line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
            )
    else:
        original_qty = getattr(instance, '_original_quantity', Decimal('0'))
        original_item_id = getattr(instance, '_original_item_id', None)
        
        if original_item_id and original_item_id != item_id:
            if original_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.invoice,
                    transaction_type='invoice',
                    line=instance,
                    quantity_released=float(original_qty),
                )
            if new_qty > 0:
                service._create_pending_for_new_line(
                    parent=instance.invoice,
                    parent_model_key='invoice',
                    line=instance,
                    line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
                )
        else:
            delta = float(new_qty - original_qty)
            if delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.invoice,
                    transaction_type='invoice',
                    line=instance,
                    quantity_delta=delta,
                )


@receiver(post_delete, sender=InvoiceLine)
def update_inventory_on_invoice_line_delete(sender, instance: InvoiceLine, **kwargs):
    """Create negative inventory delta when InvoiceLine is deleted."""
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_line(instance)
    if not item_id:
        return
    
    qty = _get_line_quantity(instance)
    if qty > 0:
        service = LineItemService(create_pending=True)
        service._create_pending_for_line_delete(
            transaction=instance.invoice,
            transaction_type='invoice',
            line=instance,
            quantity_released=float(qty),
        )


# =============================================================================
# PURCHASE LINE INVENTORY TRACKING (Fallback for direct model saves)
# =============================================================================
# Primary inventory tracking flows through LineItemService (DRF views, save_view).
# These signals act as a fallback for direct model.save() calls (imports, shell, tests).
# The _pending_created flag prevents duplicates when LineItemService handles it.
# =============================================================================

def _resolve_item_id_from_purchase_line(line: PurchaseLine) -> int | None:
    """Extract item ID from PurchaseLine's item JSONField."""
    item = getattr(line, 'item', {}) or {}
    return item.get('id_num') or item.get('id') or item.get('item_id')


def _get_purchase_line_quantity(line: PurchaseLine) -> Decimal:
    """Get the ordered quantity from a PurchaseLine."""
    qty = getattr(line, 'quantity', {}) or {}
    placed = qty.get('placed', 0) or 0
    return Decimal(str(placed))


@receiver(pre_save, sender=PurchaseLine)
def track_purchase_line_quantity_change(sender, instance: PurchaseLine, **kwargs):
    """Track original quantity for purchase line quantity change detection."""
    if instance.pk:
        try:
            original = PurchaseLine.objects.get(pk=instance.pk)
            instance._original_quantity = _get_purchase_line_quantity(original)
            instance._original_item_id = _resolve_item_id_from_purchase_line(original)
        except PurchaseLine.DoesNotExist:
            instance._original_quantity = Decimal('0')
            instance._original_item_id = None
    else:
        instance._original_quantity = Decimal('0')
        instance._original_item_id = None


@receiver(post_save, sender=PurchaseLine)
def update_inventory_on_purchase_line_save(sender, instance: PurchaseLine, created, **kwargs):
    """Create inventory delta when PurchaseLine is created or quantity changes.
    
    This is a fallback for direct model saves. Skipped when LineItemService
    handles inventory via _pending_created flag.
    """
    # Skip if LineItemService already handled inventory
    if getattr(instance, '_pending_created', False):
        return
    
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_purchase_line(instance)
    if not item_id:
        return  # No item linked, skip inventory update
    
    new_qty = _get_purchase_line_quantity(instance)
    service = LineItemService(create_pending=True)
    
    if created:
        # New line: create pending via LineItemService
        if new_qty > 0:
            service._create_pending_for_new_line(
                parent=instance.purchase,
                parent_model_key='purchase',
                line=instance,
                line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
            )
    else:
        # Existing line: calculate delta from original
        original_qty = getattr(instance, '_original_quantity', Decimal('0'))
        original_item_id = getattr(instance, '_original_item_id', None)
        
        # If item changed, handle as delete + add
        if original_item_id and original_item_id != item_id:
            # Reverse old item
            if original_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.purchase,
                    transaction_type='purchase_order',
                    line=instance,
                    quantity_released=float(original_qty),
                )
            # Add new item
            if new_qty > 0:
                service._create_pending_for_new_line(
                    parent=instance.purchase,
                    parent_model_key='purchase',
                    line=instance,
                    line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
                )
        else:
            # Same item, check if quantity changed
            delta = float(new_qty - original_qty)
            if delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.purchase,
                    transaction_type='purchase_order',
                    line=instance,
                    quantity_delta=delta,
                )


@receiver(post_delete, sender=PurchaseLine)
def update_inventory_on_purchase_line_delete(sender, instance: PurchaseLine, **kwargs):
    """Create negative inventory delta when PurchaseLine is deleted.
    
    This is a fallback for direct model deletes. DRF views handle via perform_destroy.
    """
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_purchase_line(instance)
    if not item_id:
        return  # No item linked, skip inventory update
    
    qty = _get_purchase_line_quantity(instance)
    if qty > 0:
        service = LineItemService(create_pending=True)
        service._create_pending_for_line_delete(
            transaction=instance.purchase,
            transaction_type='purchase_order',
            line=instance,
            quantity_released=float(qty),
        )


# =============================================================================
# PURCHASE LINE HEADER LINKS
# =============================================================================

@receiver(post_save, sender=PurchaseLine)
def maintain_purchase_links(sender, instance: PurchaseLine, created, **kwargs):
    """Maintain refs.links.purchase_line list on parent Purchase header."""
    if not created:
        return
    header = instance.purchase
    if not header:
        return
    refs = _ensure_refs_dict(header.refs)
    links = refs.setdefault("links", {})
    lst = links.setdefault("purchase_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])


# =============================================================================
# WORKORDER LINE INVENTORY TRACKING (Fallback for direct model saves)
# =============================================================================
# Primary inventory tracking flows through LineItemService (DRF views, save_view).
# These signals act as a fallback for direct model.save() calls (imports, shell, tests).
# The _pending_created flag prevents duplicates when LineItemService handles it.
# =============================================================================

def _resolve_item_id_from_workorder_line(line: WorkOrderLine) -> int | None:
    """Extract item ID from WorkOrderLine's item JSONField."""
    item = getattr(line, 'item', {}) or {}
    return item.get('id_num') or item.get('id') or item.get('item_id')


def _get_workorder_line_quantity(line: WorkOrderLine) -> Decimal:
    """Get the ordered quantity from a WorkOrderLine."""
    qty = getattr(line, 'quantity', {}) or {}
    placed = qty.get('placed', 0) or 0
    return Decimal(str(placed))


@receiver(pre_save, sender=WorkOrderLine)
def track_workorder_line_quantity_change(sender, instance: WorkOrderLine, **kwargs):
    """Track original quantity for workorder line quantity change detection."""
    if instance.pk:
        try:
            original = WorkOrderLine.objects.get(pk=instance.pk)
            instance._original_quantity = _get_workorder_line_quantity(original)
            instance._original_item_id = _resolve_item_id_from_workorder_line(original)
        except WorkOrderLine.DoesNotExist:
            instance._original_quantity = Decimal('0')
            instance._original_item_id = None
    else:
        instance._original_quantity = Decimal('0')
        instance._original_item_id = None


@receiver(post_save, sender=WorkOrderLine)
def update_inventory_on_workorder_line_save(sender, instance: WorkOrderLine, created, **kwargs):
    """Create inventory delta when WorkOrderLine is created or quantity changes.
    
    This is a fallback for direct model saves. Skipped when LineItemService
    handles inventory via _pending_created flag.
    """
    # Skip if LineItemService already handled inventory
    if getattr(instance, '_pending_created', False):
        return
    
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_workorder_line(instance)
    if not item_id:
        return  # No item linked, skip inventory update
    
    new_qty = _get_workorder_line_quantity(instance)
    service = LineItemService(create_pending=True)
    
    if created:
        # New line: create pending via LineItemService
        if new_qty > 0:
            service._create_pending_for_new_line(
                parent=instance.workorder,
                parent_model_key='workorder',
                line=instance,
                line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
            )
    else:
        # Existing line: calculate delta from original
        original_qty = getattr(instance, '_original_quantity', Decimal('0'))
        original_item_id = getattr(instance, '_original_item_id', None)
        
        # If item changed, handle as delete + add
        if original_item_id and original_item_id != item_id:
            # Reverse old item
            if original_qty > 0:
                service._create_pending_for_line_delete(
                    transaction=instance.workorder,
                    transaction_type='workorder',
                    line=instance,
                    quantity_released=float(original_qty),
                )
            # Add new item
            if new_qty > 0:
                service._create_pending_for_new_line(
                    parent=instance.workorder,
                    parent_model_key='workorder',
                    line=instance,
                    line_data={'quantity': {'placed': float(new_qty)}, 'item': instance.item or {}},
                )
        else:
            # Same item, check if quantity changed
            delta = float(new_qty - original_qty)
            if delta != 0:
                service._create_pending_for_qty_change(
                    transaction=instance.workorder,
                    transaction_type='workorder',
                    line=instance,
                    quantity_delta=delta,
                )


@receiver(post_delete, sender=WorkOrderLine)
def update_inventory_on_workorder_line_delete(sender, instance: WorkOrderLine, **kwargs):
    """Create negative inventory delta when WorkOrderLine is deleted.
    
    This is a fallback for direct model deletes. DRF views handle via perform_destroy.
    """
    from apps.transactions.services.line_item_service import LineItemService
    
    item_id = _resolve_item_id_from_workorder_line(instance)
    if not item_id:
        return  # No item linked, skip inventory update
    
    qty = _get_workorder_line_quantity(instance)
    if qty > 0:
        service = LineItemService(create_pending=True)
        service._create_pending_for_line_delete(
            transaction=instance.workorder,
            transaction_type='work_order',
            line=instance,
            quantity_released=float(qty),
        )


# =============================================================================
# WORKORDER LINE HEADER LINKS
# =============================================================================

@receiver(post_save, sender=WorkOrderLine)
def maintain_workorder_links(sender, instance: WorkOrderLine, created, **kwargs):
    """Maintain refs.links.workorder_line list on parent WorkOrder header."""
    if not created:
        return
    header = instance.workorder
    if not header:
        return
    refs = _ensure_refs_dict(header.refs)
    links = refs.setdefault("links", {})
    lst = links.setdefault("workorder_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])


# =============================================================================
# INVENTORY PENDING - NOTE
# =============================================================================
# Primary path: LineItemService creates Pending records (DRF views, save_view).
# Fallback path: Signals create Pending records for direct model saves.
# The _pending_created flag ensures no duplicates.
#
# Pending record processing/clearing is handled by Celery tasks:
#   - apps.transactions.tasks.process_pending_inventory
#   - apps.products.tasks.expire_inventory_reservations
# =============================================================================