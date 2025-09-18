from __future__ import annotations

from typing import Any, List
from decimal import Decimal
import random

from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.db import transaction
from django.apps import apps

from apps.transactions.models import Invoice, InvoiceLine


def _ensure_min_items(n: int = 3) -> List[int]:
    """Ensure at least n product items exist and return their ids."""
    ItemModel = apps.get_model('products', 'Item')
    ids = list(ItemModel.objects.values_list('id', flat=True)[:n])
    while len(ids) < n:
        idx = len(ids) + 1
        it = ItemModel.objects.create(
            name=f"Seed Item {idx}",
            sku=f"SEED-{idx:03d}",
            uom="EA",
            price={"base": float(10 * idx), "currency": "USD", "tiers": [], "qty_breaks": [], "msrp": float(12 * idx), "history": []},
            cost={"standard": float(6 * idx), "currency": "USD", "breaks": [], "components": {}, "history": []},
            quantity={"on_hand": 100 * idx, "allocated": 0, "available": 100 * idx, "on_order": 0},
        )
        ids.append(int(getattr(it, 'id')))
    return ids


def _pick_contact_id() -> int | None:
    try:
        Contact = apps.get_model('core', 'Contact')
    except LookupError:
        return None
    cid = Contact.objects.values_list('id', flat=True).first()
    return int(cid) if cid else None


def _pick_customer_org_id() -> int | None:
    try:
        CustomerOrg = apps.get_model('orgs', 'CustomerOrg')
    except LookupError:
        return None
    oid = CustomerOrg.objects.values_list('id', flat=True).first()
    if oid:
        return int(oid)
    # Create a minimal customer org using the underlying OrgBase concrete model
    try:
        OrgBase = apps.get_model('orgs', 'OrgBase')
    except LookupError:
        return None
    obj = OrgBase.objects.create(
        org_type='customer',
        display_name='Seed Customer',
        status='active',
        contacts=[], locations=[], domains=[], phones=[], emails=[],
        relations={"parents": [], "children": [], "linked_ids": []},
        financial={}, docs=[], connections={}, data={}, metrics={}, gl_accounts={},
    )
    return int(getattr(obj, 'id'))


def _ensure_phone_id() -> int | None:
    try:
        Phone = apps.get_model('communications', 'Phone')
    except LookupError:
        return None
    pid = Phone.objects.values_list('id', flat=True).first()
    if pid:
        return int(pid)
    p = Phone.objects.create(number="+1-555-0199", name="Main", country_code="+1", format="+1 555-0199")
    return int(getattr(p, 'id'))


def _ensure_email_id() -> int | None:
    try:
        Email = apps.get_model('communications', 'Email')
    except LookupError:
        return None
    eid = Email.objects.values_list('id', flat=True).first()
    if eid:
        return int(eid)
    e = Email.objects.create(email="seed@example.com", name="Main")
    return int(getattr(e, 'id'))


def _line_payload(item_id: int, idx: int) -> dict:
    qty = 1 + (idx % 3)
    unit_price = Decimal(10 + 5 * (idx % 4))
    return {
        "item": {"id": item_id, "description": f"Line {idx+1} (item {item_id})", "unit_measure": "EA", "line_number": idx + 1},
        # Invoices use quantity.packed for confirmation
        "quantity": {"packed": 0},
        "price": {"unit": float(unit_price), "extended": float(unit_price * qty), "precision": 2},
        "cost": {"unit": float(unit_price * Decimal("0.6")), "extended": float(unit_price * Decimal("0.6") * qty), "precision": 2},
        "tax": {"sales_rate": 0.0, "sales": 0.0},
        "comments": {"public": ""},
        "prefs": {"currency": "USD", "locale": "en-US", "terms": "Net 30"},
    }


class Command(DjangoBaseCommand):
    help = "Seed Invoices with related InvoiceLine rows (signals maintain header.refs.links.invoice_line)."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=2, help='Number of invoices to create')
        parser.add_argument('--lines', type=int, default=2, help='Number of lines per invoice')

    @transaction.atomic
    def handle(self, *args, **options):
        count = int(options['count'])
        lines_per = max(1, int(options['lines']))
        item_ids = _ensure_min_items(max(3, lines_per))
        contact_id = _pick_contact_id()
        customer_org_id = _pick_customer_org_id()
        phone_id = _ensure_phone_id()
        email_id = _ensure_email_id()

        self.stdout.write(self.style.NOTICE(
            f"Using items={item_ids}; contact={contact_id or 'none'}; customer_org={customer_org_id or 'none'}; phone={phone_id or 'none'}; email={email_id or 'none'}"
        ))

        def _header_links() -> dict:
            links: dict[str, Any] = {"links": {}}
            links["links"]["items"] = item_ids[:2]
            if contact_id:
                links["links"]["contacts"] = [contact_id]
            if customer_org_id:
                links["links"]["customers"] = [customer_org_id]
            links["links"]["address"] = [{"billto": 1}, {"shipto": 3}]
            if phone_id:
                links["links"]["phone"] = [phone_id]
            if email_id:
                links["links"]["email"] = [email_id]
            return links

        created = {"invoices": []}

        for i in range(count):
            inv = Invoice.objects.create(refs=_header_links(), prefs={"currency": "USD"})
            created["invoices"].append(int(inv.id))
            chosen = random.sample(item_ids, k=min(lines_per, len(item_ids)))
            for li, item_id in enumerate(chosen):
                payload = _line_payload(item_id, li)
                line = InvoiceLine(parent=inv)
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()
            # Signals append to inv.refs.links.invoice_line and save header; nothing more needed.

        self.stdout.write(self.style.SUCCESS(f"Seeded: {created}"))
