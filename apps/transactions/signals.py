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