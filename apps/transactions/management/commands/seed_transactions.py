from __future__ import annotations

from typing import List, Any
from decimal import Decimal
import random

from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.db import transaction
from django.apps import apps

from apps.transactions.models import (
    Proposal, ProposalLine,
    SalesOrder, SalesOrderLine,
    Invoice, InvoiceLine,
    PurchaseOrder, PurchaseOrderLine,
)


def _ensure_min_items(n: int = 3) -> List[int]:
    """Return a list of Item IDs; create placeholder items if none exist.

    We use the products.Item model via apps registry to avoid tight coupling here.
    """
    ItemModel = apps.get_model('products', 'Item')
    ids = list(ItemModel.objects.values_list('id', flat=True)[:n])
    created: list[int] = []
    while len(ids) + len(created) < n:
        idx = len(ids) + len(created) + 1
        it: Any = ItemModel.objects.create(
            name=f"Demo Item {idx}",
            sku=f"DEMO-{idx:03d}",
            uom="EA",
            price={"base": float(10 * idx), "currency": "USD", "tiers": [], "qty_breaks": [], "msrp": float(12 * idx), "history": []},
            cost={"standard": float(6 * idx), "currency": "USD", "breaks": [], "components": {}, "history": []},
            quantity={"on_hand": 100 * idx, "allocated": 0, "available": 100 * idx, "on_order": 0},
        )
        created.append(int(it.id))
    return ids + created


def _pick_contact_id() -> int | None:
    Contact = apps.get_model('core', 'Contact')
    cid = Contact.objects.values_list('id', flat=True).first()
    return int(cid) if cid else None

def _pick_customer_org_id() -> int | None:
    """Return an existing CustomerOrg id or create a minimal one.

    Uses the OrgBase table via the CustomerOrg proxy. Ensures at least one
    customer org exists so headers can link to customers for forward hydration.
    """
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
        display_name='Demo Customer 1',
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
    p = Phone.objects.create(number="+1-555-0100", name="Main", country_code="+1", format="+1 555-0100")
    return int(getattr(p, 'id'))

def _ensure_email_id() -> int | None:
    try:
        Email = apps.get_model('communications', 'Email')
    except LookupError:
        return None
    eid = Email.objects.values_list('id', flat=True).first()
    if eid:
        return int(eid)
    e = Email.objects.create(email="demo@example.com", name="Main")
    return int(getattr(e, 'id'))


def _line_payload(item_id: int, idx: int, tx_type: str) -> dict:
    qty = 1 + (idx % 3)
    unit_price = Decimal(10 + 5 * (idx % 4))
    # Quantity shape: invoices use quantity.packed; orders include quantity.invoiced per new contract
    if tx_type == "invoice":
        quantity = {"packed": 0}
    elif tx_type == "order":
        quantity = {"placed": qty, "backlog": 0, "remaining": qty, "shipped": 0, "invoiced": 0, "is_fixed": False, "precision": 2}
    else:
        quantity = {"placed": qty, "backlog": 0, "remaining": qty, "is_fixed": False, "precision": 2}
    return {
        "item": {"id": item_id, "description": f"Line {idx} for item {item_id}", "unit_measure": "EA", "line_number": idx + 1},
        "quantity": quantity,
        "price": {"unit": float(unit_price), "extended": float(unit_price * qty), "precision": 2},
        "cost": {"unit": float(unit_price * Decimal("0.6")), "extended": float(unit_price * Decimal("0.6") * qty), "precision": 2},
        "tax": {"sales_rate": 0.0, "sales": 0.0},
        "comments": {"public": ""},
        "prefs": {"currency": "USD", "locale": "en-US", "terms": ""},
    }


class Command(DjangoBaseCommand):
    help = "Seed demo transactions: proposals, sales orders, invoices, and purchase orders with lines."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=2, help='Number of each header type to create')

    @transaction.atomic
    def handle(self, *args, **options):
        count = int(options['count'])
        item_ids = _ensure_min_items(max(3, count))
        contact_id = _pick_contact_id()
        customer_org_id = _pick_customer_org_id()
        # Ensure a vendor org for POs
        def _pick_vendor_org_id() -> int | None:
            try:
                VendorOrg = apps.get_model('orgs', 'VendorOrg')
            except LookupError:
                return None
            vid = VendorOrg.objects.values_list('id', flat=True).first()
            if vid:
                return int(vid)
            try:
                OrgBase = apps.get_model('orgs', 'OrgBase')
            except LookupError:
                return None
            v = OrgBase.objects.create(
                org_type='vendor',
                display_name='Demo Vendor 1',
                status='active',
                contacts=[], locations=[], domains=[], phones=[], emails=[],
                relations={"parents": [], "children": [], "linked_ids": []},
                financial={}, docs=[], connections={}, data={}, metrics={}, gl_accounts={},
            )
            return int(getattr(v, 'id'))
        vendor_org_id = _pick_vendor_org_id()
        phone_id = _ensure_phone_id()
        email_id = _ensure_email_id()

        self.stdout.write(self.style.NOTICE(
            f"Using items: {item_ids}; contact: {contact_id or 'none'}; customer_org: {customer_org_id or 'none'}; vendor_org: {vendor_org_id or 'none'}; phone: {phone_id or 'none'}; email: {email_id or 'none'}"
        ))

        created_ids: dict[str, list[int]] = {"proposals": [], "sales_orders": [], "invoices": [], "purchase_orders": []}

        # Helper to attach minimal refs.links for headers (items, contacts, customers, addresses dict-style)
        def _header_links(kind: str) -> dict:
            links: dict[str, Any] = {"links": {}}
            # items vs item
            if kind == 'purchase_order':
                links["links"]["item"] = item_ids[:2]
                if contact_id:
                    links["links"]["contact"] = [contact_id]
                if vendor_org_id:
                    links["links"]["vendor"] = [vendor_org_id]
            else:
                links["links"]["items"] = item_ids[:2]
                if contact_id:
                    links["links"]["contacts"] = [contact_id]
                if customer_org_id:
                    links["links"]["customers"] = [customer_org_id]
            # dict-style addresses; same key name requested: 'address'
            links["links"]["address"] = [{"billto": 1}, {"shipto": 3}]
            if phone_id:
                links["links"]["phone"] = [phone_id]
            if email_id:
                links["links"]["email"] = [email_id]
            return links

        # Proposals
        for i in range(count):
            p = Proposal.objects.create(name=f"Demo Proposal {i+1}", refs=_header_links('proposal'), prefs={"currency": "USD"})
            created_ids["proposals"].append(int(p.id))
            pr_line_ids: list[int] = []
            for li, item_id in enumerate(random.sample(item_ids, k=min(2, len(item_ids)))):
                payload = _line_payload(item_id, li, tx_type="proposal")
                # ProposalLine uses a FK field named parent_id (legacy schema)
                line = ProposalLine(parent_id=p.id, parent_ref_id=p.id)
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()
                pr_line_ids.append(int(line.id))
            # backfill refs.links with line ids (alias key as requested)
            p.refs = p.refs or {}
            lk = p.refs.get('links') or {}
            lk['proposal_lin'] = pr_line_ids
            p.refs['links'] = lk
            p.save(update_fields=['refs'])

        # Sales Orders
        for i in range(count):
            next_so_num = 1000 + (SalesOrder.objects.count() or 0) + i
            so = SalesOrder.objects.create(order_no=f"SO-{next_so_num}", refs=_header_links('sales_order'), prefs={"currency": "USD"})
            created_ids["sales_orders"].append(int(so.id))
            so_line_ids: list[int] = []
            for li, item_id in enumerate(random.sample(item_ids, k=min(3, len(item_ids)))):
                payload = _line_payload(item_id, li, tx_type="order")
                line = SalesOrderLine(parent=so, parent_ref_id=so.id)
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()
                so_line_ids.append(int(line.id))
            # backfill refs.links
            so.refs = so.refs or {}
            lk = so.refs.get('links') or {}
            # Use singular model name key
            lk['sales_order_line'] = so_line_ids
            so.refs['links'] = lk
            so.save(update_fields=['refs'])

        # Invoices
        for i in range(count):
            next_inv_num = 2000 + (Invoice.objects.count() or 0) + i
            inv = Invoice.objects.create(invoice_no=f"INV-{next_inv_num}", refs=_header_links('invoice'), prefs={"currency": "USD"})
            created_ids["invoices"].append(int(inv.id))
            inv_line_ids: list[int] = []
            for li, item_id in enumerate(random.sample(item_ids, k=min(2, len(item_ids)))):
                payload = _line_payload(item_id, li, tx_type="invoice")
                line = InvoiceLine(parent=inv, parent_ref_id=inv.id)
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()
                inv_line_ids.append(int(line.id))
            inv.refs = inv.refs or {}
            lk = inv.refs.get('links') or {}
            lk['invoice_line'] = inv_line_ids
            inv.refs['links'] = lk
            inv.save(update_fields=['refs'])

        # Purchase Orders
        for i in range(count):
            next_po_num = 3000 + (PurchaseOrder.objects.count() or 0) + i
            po = PurchaseOrder.objects.create(po_no=f"PO-{next_po_num}", refs=_header_links('purchase_order'), prefs={"currency": "USD"})
            created_ids["purchase_orders"].append(int(po.id))
            po_line_ids: list[int] = []
            for li, item_id in enumerate(random.sample(item_ids, k=min(2, len(item_ids)))):
                payload = _line_payload(item_id, li, tx_type="order")
                line = PurchaseOrderLine(parent=po, parent_ref_id=po.id)
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()
                po_line_ids.append(int(line.id))
            po.refs = po.refs or {}
            lk = po.refs.get('links') or {}
            lk['purchase_order_line'] = po_line_ids
            po.refs['links'] = lk
            po.save(update_fields=['refs'])

        self.stdout.write(self.style.SUCCESS(f"Seeded: {created_ids}"))
