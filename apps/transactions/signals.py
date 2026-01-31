from __future__ import annotations
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from apps.transactions.models import ProposalLine, OrderLine, InvoiceLine, Proposal, Order, Invoice, Payment
from apps.transactions.services.email_notifications import TransactionEmailService

@receiver(post_save, sender=ProposalLine)
def maintain_proposal_links(sender, instance: ProposalLine, created, **kwargs):
    if not created:
        return
    header = instance.parent
    if not header:
        return
    refs = header.refs or {}
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
    refs = header.refs or {}
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
    header = instance.parent
    if not header:
        return
    refs = header.refs or {}
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
# INVENTORY PENDING SIGNALS - Safety net for all line creation paths
# =============================================================================
import logging
logger = logging.getLogger(__name__)

def _create_inventory_pending_for_line(instance, line_type: str):
    """
    Create inventory pending record for a newly created transaction line.
    
    This is a SAFETY NET that catches any line creation that bypassed
    the LineItemService. The preferred path is still through LineItemService.
    
    Args:
        instance: The line model instance (OrderLine, InvoiceLine, etc.)
        line_type: Type identifier ('order', 'invoice', 'purchase', 'workorder', 'proposal')
    """
    # Skip if pending was already created (flag set by LineItemService)
    if getattr(instance, '_pending_created', False):
        return
    
    # Check if a pending already exists for this line_id (prevents duplicates)
    from apps.core.models import Pending
    existing = Pending.objects.filter(
        purpose='inventory_line_add',
        data__line_id=instance.pk
    ).exists()
    if existing:
        logger.debug(f"Pending already exists for {line_type} line {instance.pk}, skipping")
        return
    
    # Extract item_id from the line's item JSON
    item_data = getattr(instance, 'item', {}) or {}
    item_id = item_data.get('item_id') or item_data.get('id')
    if not item_id:
        logger.debug(f"Skipping pending for {line_type} line {instance.pk}: no item_id")
        return
    
    # Extract quantity
    qty_data = getattr(instance, 'quantity', {}) or {}
    quantity = float(qty_data.get('ordered', 0) or qty_data.get('placed', 0) or 0)
    if not quantity:
        logger.debug(f"Skipping pending for {line_type} line {instance.pk}: zero quantity")
        return
    
    # Get the parent transaction
    parent = None
    for attr in ['order', 'invoice', 'purchase', 'workorder', 'proposal', 'parent']:
        parent = getattr(instance, attr, None)
        if parent is not None:
            break
    
    if not parent:
        logger.warning(f"Cannot create pending for {line_type} line {instance.pk}: no parent found")
        return
    
    try:
        from apps.transactions.services.line_item_service import LineItemService
        service = LineItemService(create_pending=True)
        
        # Build line_data from instance
        line_data = {
            'item': item_data,
            'quantity': qty_data,
            'price': getattr(instance, 'price', {}) or {},
            'cost': getattr(instance, 'cost', {}) or {},
        }
        
        service._create_pending_for_new_line(
            parent=parent,
            parent_model_key=line_type,
            line=instance,
            line_data=line_data,
        )
        logger.info(f"[SIGNAL] Created inventory pending for {line_type} line {instance.pk}")
    except Exception as e:
        logger.warning(f"[SIGNAL] Failed to create inventory pending for {line_type} line {instance.pk}: {e}")


@receiver(post_save, sender=OrderLine)
def create_order_line_inventory_pending(sender, instance: OrderLine, created, **kwargs):
    """Create inventory pending when OrderLine is created (safety net)."""
    if created:
        _create_inventory_pending_for_line(instance, 'order')


@receiver(post_save, sender=InvoiceLine)
def create_invoice_line_inventory_pending(sender, instance: InvoiceLine, created, **kwargs):
    """Create inventory pending when InvoiceLine is created (safety net)."""
    if created:
        _create_inventory_pending_for_line(instance, 'invoice')


# Import additional line models for signals
try:
    from apps.transactions.models import PurchaseLine, WorkOrderLine
    
    @receiver(post_save, sender=PurchaseLine)
    def create_purchase_line_inventory_pending(sender, instance, created, **kwargs):
        """Create inventory pending when PurchaseLine is created (safety net)."""
        if created:
            _create_inventory_pending_for_line(instance, 'purchase')
    
    @receiver(post_save, sender=WorkOrderLine)
    def create_workorder_line_inventory_pending(sender, instance, created, **kwargs):
        """Create inventory pending when WorkOrderLine is created (safety net)."""
        if created:
            _create_inventory_pending_for_line(instance, 'workorder')
except ImportError:
    pass  # Models may not exist in all configurations