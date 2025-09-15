from __future__ import annotations

"""
Stable transaction seed:

Creates a deterministic set of Proposals, Sales Orders, Invoices, and Purchase Orders
with predictable identifiers and a small number of lines each. Safe to run multiple
times with --reset to wipe and reseed, or idempotent if rows already exist.

Usage:
  python manage.py seed_transactions_stable --count 3 --reset
"""

from typing import Any, List
from decimal import Decimal

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
    ItemModel = apps.get_model('products', 'Item')
    ids = list(ItemModel.objects.values_list('id', flat=True)[:n])
    while len(ids) < n:
        idx = len(ids) + 1
        it = ItemModel.objects.create(
            name=f"Stable Item {idx}",
            sku=f"STABLE-{idx:03d}",
            uom="EA",
            price={"base": float(10 * idx), "currency": "USD", "tiers": [], "qty_breaks": [], "msrp": float(12 * idx), "history": []},
            cost={"standard": float(6 * idx), "currency": "USD", "breaks": [], "components": {}, "history": []},
            quantity={"on_hand": 100 * idx, "allocated": 0, "available": 100 * idx, "on_order": 0},
        )
        # use getattr to appease static analysis on dynamic Django model attrs
        ids.append(int(getattr(it, "id")))
    return ids


def _pick_contact_id() -> int | None:
    try:
        Contact = apps.get_model('core', 'Contact')
    except LookupError:
        return None
    cid = Contact.objects.values_list('id', flat=True).first()
    return int(cid) if cid else None


def _line_payload(item_id: int, idx: int, tx_type: str) -> dict:
    qty = 1 + (idx % 2)
    unit_price = Decimal(15 + 5 * (idx % 3))
    return {
        "item": {"id": item_id, "description": f"Line {idx+1} (item {item_id})", "unit_measure": "EA", "line_number": idx + 1},
        "quantity": {"placed": qty, "backlog": 0, "remaining": qty, "is_fixed": False, "precision": 2} if tx_type != "invoice" else {"packed": 0},
        "price": {"unit": float(unit_price), "extended": float(unit_price * qty), "precision": 2},
        "cost": {"unit": float(unit_price * Decimal("0.6")), "extended": float(unit_price * Decimal("0.6") * qty), "precision": 2},
        "tax": {"sales_rate": 0.0, "sales": 0.0},
        "comments": {"public": ""},
        "prefs": {"currency": "USD", "locale": "en-US", "terms": "Net 30"},
    }


class Command(DjangoBaseCommand):
    help = "Seed a deterministic set of transaction headers and lines for development."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=2, help='Number of each header type to create (proposals, orders, invoices, POs)')
        parser.add_argument('--reset', action='store_true', help='Delete existing seeded records before creating new ones')

    @transaction.atomic
    def handle(self, *args, **options):
        count = int(options['count'])
        reset = bool(options['reset'])

        item_ids = _ensure_min_items(max(3, count))

        # Optional: clear existing (only headers created by this command heuristically)
        if reset:
            Proposal.objects.filter(name__startswith="Stable Proposal ").delete()
            SalesOrder.objects.filter(order_no__startswith="SOST-").delete()
            Invoice.objects.filter(invoice_no__startswith="INVST-").delete()
            PurchaseOrder.objects.filter(po_no__startswith="POST-").delete()

        created = {"proposals": [], "sales_orders": [], "invoices": [], "purchase_orders": []}

        # Proposals (Stable Proposal 1..N)
        for i in range(count):
            name = f"Stable Proposal {i+1}"
            p, _ = Proposal.objects.get_or_create(name=name, defaults={"prefs": {"currency": "USD"}})
            created["proposals"].append(int(p.id))
            # lines (2 per header, idempotent by line_number)
            for li, item_id in enumerate(item_ids[:2]):
                payload = _line_payload(item_id, li, tx_type="proposal")
                line, _ = ProposalLine.objects.get_or_create(parent=p, parent_ref_id=p.id, item={"id": item_id, "line_number": li+1}, defaults={})
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()

        # Sales Orders (SOST-1001..)
        base_so = 1001
        for i in range(count):
            so_no = f"SOST-{base_so + i}"
            so, _ = SalesOrder.objects.get_or_create(order_no=so_no, defaults={"prefs": {"currency": "USD"}})
            created["sales_orders"].append(int(so.id))
            for li, item_id in enumerate(item_ids[:3]):
                payload = _line_payload(item_id, li, tx_type="order")
                line, _ = SalesOrderLine.objects.get_or_create(parent=so, parent_ref_id=so.id, item={"id": item_id, "line_number": li+1}, defaults={})
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()

        # Invoices (INVST-2001..)
        base_inv = 2001
        for i in range(count):
            inv_no = f"INVST-{base_inv + i}"
            inv, _ = Invoice.objects.get_or_create(invoice_no=inv_no, defaults={"prefs": {"currency": "USD"}})
            created["invoices"].append(int(inv.id))
            for li, item_id in enumerate(item_ids[:2]):
                payload = _line_payload(item_id, li, tx_type="invoice")
                line, _ = InvoiceLine.objects.get_or_create(parent=inv, parent_ref_id=inv.id, item={"id": item_id, "line_number": li+1}, defaults={})
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()

        # Purchase Orders (POST-3001..)
        base_po = 3001
        for i in range(count):
            po_no = f"POST-{base_po + i}"
            po, _ = PurchaseOrder.objects.get_or_create(po_no=po_no, defaults={"prefs": {"currency": "USD"}})
            created["purchase_orders"].append(int(po.id))
            for li, item_id in enumerate(item_ids[:2]):
                payload = _line_payload(item_id, li, tx_type="order")
                line, _ = PurchaseOrderLine.objects.get_or_create(parent=po, parent_ref_id=po.id, item={"id": item_id, "line_number": li+1}, defaults={})
                line.item = payload["item"]
                line.quantity = payload["quantity"]
                line.price = payload["price"]
                line.cost = payload["cost"]
                line.tax = payload["tax"]
                line.prefs = payload["prefs"]
                line.comments = payload["comments"]
                line.save()

        self.stdout.write(self.style.SUCCESS(f"Stable seed complete: {created}"))
