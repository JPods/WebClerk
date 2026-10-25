"""A customer or vendor with business still open cannot be deleted (Bill, 2026-10-25).

"Refuse to delete a customer if it has unapplied payments, uncollected invoices, or open
orders. Users should clean these up first. Same with vendors on purchases, receipts and
payments." Payments outlive the documents they were made against, and only a user removes
or reverses one — so an org whose money or goods are still in motion stays until that is
cleaned up.

Open is measured, not read from status (statuses vary: cancelled/canceled, released,
confirmed): an order or purchase is open while a line has quantity remaining and it is not
cancelled; an invoice or receipt while its balance is not zero; a payment while it has an
amount available (unapplied). One org may be both customer and vendor, so both sides are
checked. A pre_delete receiver, so a queryset delete or the admin is stopped too.
"""
from __future__ import annotations

from django.db.models.signals import pre_delete

CANCELLED = ('cancelled', 'canceled')


class OrgHasOpenBusiness(ValueError):
    pass


def open_business(org) -> list[tuple[str, list[str]]]:
    """[(what, [ida, …])] still open for this org, as customer and as vendor."""
    from apps.transactions.models import Cash, Invoice, Order, Purchase, Receipt

    def backlog(model, party):
        return (model.objects.filter(**{party: org}, lines__quantity__remaining__gt=0)
                .exclude(status__in=CANCELLED).distinct())

    def owing(model, party):
        return (model.objects.filter(**{party: org})
                .exclude(totals__balance=0).exclude(totals__balance__isnull=True))

    found = [
        ('open orders', backlog(Order, 'customer')),
        ('uncollected invoices', owing(Invoice, 'customer')),
        ('unapplied customer payments', Cash.objects.filter(customer=org).exclude(available=0)),
        ('open purchases', backlog(Purchase, 'vendor')),
        ('unpaid receipts', owing(Receipt, 'vendor')),
        ('unapplied vendor payments', Cash.objects.filter(vendor=org).exclude(available=0)),
    ]
    return [(what, [r.ida or f'#{r.pk}' for r in qs.order_by('pk')])
            for what, qs in found if qs.exists()]


def refuse_delete_with_open_business(sender, instance, **kwargs):
    from apps.orgs.models.base import OrgBase
    if not isinstance(instance, OrgBase):
        return
    still_open = open_business(instance)
    if not still_open:
        return
    listed = '; '.join(f"{len(idas)} {what} ({', '.join(idas[:5])}{', …' if len(idas) > 5 else ''})"
                       for what, idas in still_open)
    name = getattr(instance, 'name', '') or getattr(instance, 'ida', '') or instance.pk
    raise OrgHasOpenBusiness(
        f"{name} still has {listed}. Clean these up first: complete or cancel the orders and "
        f"purchases, collect or credit the invoices, pay the receipts, and apply, remove or "
        f"reverse the payments. Then delete.")


def connect():
    pre_delete.connect(refuse_delete_with_open_business,
                       dispatch_uid='transactions.org_delete_guard.refuse_open_business')
