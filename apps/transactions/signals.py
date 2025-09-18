from __future__ import annotations
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.transactions.models import ProposalLine, SalesOrderLine, InvoiceLine

@receiver(post_save, sender=ProposalLine)
def maintain_proposal_links(sender, instance: ProposalLine, created, **kwargs):
    if not created:
        return
    header = instance.parent
    refs = header.refs or {}
    links = refs.setdefault("links", {})
    lst = links.setdefault("proposal_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])

@receiver(post_save, sender=SalesOrderLine)
def maintain_sales_order_links(sender, instance: SalesOrderLine, created, **kwargs):
    if not created:
        return
    header = instance.parent
    refs = header.refs or {}
    links = refs.setdefault("links", {})
    lst = links.setdefault("sales_order_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])

@receiver(post_save, sender=InvoiceLine)
def maintain_invoice_links(sender, instance: InvoiceLine, created, **kwargs):
    if not created:
        return
    header = instance.parent
    refs = header.refs or {}
    links = refs.setdefault("links", {})
    lst = links.setdefault("invoice_line", [])
    if instance.id not in lst:
        lst.append(instance.id)
        header.refs = refs
        header.save(update_fields=["refs", "dt_modified", "version"])