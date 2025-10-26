from __future__ import annotations

"""
Stable transaction seed:

Creates a deterministic set of Proposals, Sales Orders, Invoices, and Purchase Orders
with predictable identifiers and a small number of lines each. Safe to run multiple
times with --reset to wipe and reseed, or idempotent if rows already exist.

Usage:
  python manage.py seed_transactions_stable --count 3 --reset
"""

from typing import List
from decimal import Decimal

from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.db import connection, transaction
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
        existing_tables = set(connection.introspection.table_names())
        warned_labels: set[str] = set()

        def table_exists(model_class) -> bool:
            return getattr(model_class._meta, "db_table", None) in existing_tables

        def warn_skip(label: str) -> None:
            if label not in warned_labels:
                warned_labels.add(label)
                self.stdout.write(self.style.WARNING(f"Skipping {label}: table missing."))

        proposal_table = table_exists(Proposal)
        proposal_line_table = table_exists(ProposalLine)
        sales_order_table = table_exists(SalesOrder)
        sales_order_line_table = table_exists(SalesOrderLine)
        invoice_table = table_exists(Invoice)
        invoice_line_table = table_exists(InvoiceLine)
        purchase_order_table = table_exists(PurchaseOrder)
        purchase_order_line_table = table_exists(PurchaseOrderLine)

        if reset:
            if proposal_table:
                Proposal.objects.filter(ida__startswith="stable-proposal-").delete()
            else:
                warn_skip("proposals (reset)")
            if sales_order_table:
                SalesOrder.objects.filter(ida__startswith="stable-sales-order-").delete()
            else:
                warn_skip("sales orders (reset)")
            if invoice_table:
                Invoice.objects.filter(ida__startswith="stable-invoice-").delete()
            else:
                warn_skip("invoices (reset)")
            if purchase_order_table:
                PurchaseOrder.objects.filter(ida__startswith="stable-purchase-order-").delete()
            else:
                warn_skip("purchase orders (reset)")

        created = {"proposals": [], "sales_orders": [], "invoices": [], "purchase_orders": []}

        # Proposals (Stable Proposal 1..N)
        if not proposal_table:
            warn_skip("proposals")
        else:
            if not proposal_line_table:
                warn_skip("proposal lines")
            for i in range(count):
                ida_value = f"stable-proposal-{i+1:02d}"
                p, _ = Proposal.objects.get_or_create(
                    ida=ida_value,
                    defaults={"prefs": {"currency": "USD"}},
                )
                created["proposals"].append(int(p.id))
                if not proposal_line_table:
                    continue
                for li, item_id in enumerate(item_ids[:2]):
                    payload = _line_payload(item_id, li, tx_type="proposal")
                    line_ida = f"{ida_value}-line-{li+1:02d}"
                    line, _ = ProposalLine.objects.get_or_create(
                        ida=line_ida,
                        defaults={"parent": p},
                    )
                    line.parent = p
                    line.item = payload["item"]
                    line.quantity = payload["quantity"]
                    line.price = payload["price"]
                    line.cost = payload["cost"]
                    line.tax = payload["tax"]
                    line.prefs = payload["prefs"]
                    line.comments = payload["comments"]
                    line.metadata = {**(line.metadata or {}), "seed": "stable", "position": li + 1}
                    line.save()

        # Sales Orders (SOST-1001..)
        if not sales_order_table:
            warn_skip("sales orders")
        else:
            if not sales_order_line_table:
                warn_skip("sales order lines")
            for i in range(count):
                ida_value = f"stable-sales-order-{i+1:02d}"
                so, _ = SalesOrder.objects.get_or_create(
                    ida=ida_value,
                    defaults={"prefs": {"currency": "USD"}},
                )
                current_metadata = dict(so.metadata or {})
                updated_metadata = {**current_metadata, "order_no": f"SOST-{1001 + i}", "seed": "stable"}
                if updated_metadata != current_metadata:
                    so.metadata = updated_metadata
                    so.save(update_fields=["metadata"])
                created["sales_orders"].append(int(so.id))
                if not sales_order_line_table:
                    continue
                for li, item_id in enumerate(item_ids[:3]):
                    payload = _line_payload(item_id, li, tx_type="order")
                    line_ida = f"{ida_value}-line-{li+1:02d}"
                    line, _ = SalesOrderLine.objects.get_or_create(
                        ida=line_ida,
                        defaults={"parent": so},
                    )
                    line.parent = so
                    line.item = payload["item"]
                    line.quantity = payload["quantity"]
                    line.price = payload["price"]
                    line.cost = payload["cost"]
                    line.tax = payload["tax"]
                    line.prefs = payload["prefs"]
                    line.comments = payload["comments"]
                    line.metadata = {**(line.metadata or {}), "seed": "stable", "position": li + 1}
                    line.save()

        # Invoices (INVST-2001..)
        if not invoice_table:
            warn_skip("invoices")
        else:
            if not invoice_line_table:
                warn_skip("invoice lines")
            for i in range(count):
                ida_value = f"stable-invoice-{i+1:02d}"
                inv, _ = Invoice.objects.get_or_create(
                    ida=ida_value,
                    defaults={"prefs": {"currency": "USD"}},
                )
                created["invoices"].append(int(inv.id))
                if not invoice_line_table:
                    continue
                for li, item_id in enumerate(item_ids[:2]):
                    payload = _line_payload(item_id, li, tx_type="invoice")
                    line_ida = f"{ida_value}-line-{li+1:02d}"
                    line, _ = InvoiceLine.objects.get_or_create(
                        ida=line_ida,
                        defaults={"parent": inv},
                    )
                    line.parent = inv
                    line.item = payload["item"]
                    line.quantity = payload["quantity"]
                    line.price = payload["price"]
                    line.cost = payload["cost"]
                    line.tax = payload["tax"]
                    line.prefs = payload["prefs"]
                    line.comments = payload["comments"]
                    line.metadata = {**(line.metadata or {}), "seed": "stable", "position": li + 1}
                    line.save()

        # Purchase Orders (POST-3001..)
        if not purchase_order_table:
            warn_skip("purchase orders")
        else:
            if not purchase_order_line_table:
                warn_skip("purchase order lines")
            for i in range(count):
                ida_value = f"stable-purchase-order-{i+1:02d}"
                po, _ = PurchaseOrder.objects.get_or_create(
                    ida=ida_value,
                    defaults={"prefs": {"currency": "USD"}},
                )
                current_metadata = dict(po.metadata or {})
                updated_metadata = {**current_metadata, "po_no": f"POST-{3001 + i}", "seed": "stable"}
                if updated_metadata != current_metadata:
                    po.metadata = updated_metadata
                    po.save(update_fields=["metadata"])
                created["purchase_orders"].append(int(po.id))
                if not purchase_order_line_table:
                    continue
                for li, item_id in enumerate(item_ids[:2]):
                    payload = _line_payload(item_id, li, tx_type="order")
                    line_ida = f"{ida_value}-line-{li+1:02d}"
                    line, _ = PurchaseOrderLine.objects.get_or_create(
                        ida=line_ida,
                        defaults={"parent": po},
                    )
                    line.parent = po
                    line.item = payload["item"]
                    line.quantity = payload["quantity"]
                    line.price = payload["price"]
                    line.cost = payload["cost"]
                    line.tax = payload["tax"]
                    line.prefs = payload["prefs"]
                    line.comments = payload["comments"]
                    line.metadata = {**(line.metadata or {}), "seed": "stable", "position": li + 1}
                    line.save()

        self.stdout.write(self.style.SUCCESS(f"Stable seed complete: {created}"))


MODEL_LINKS = {
    # Org ↔ communications (populate refs.links)
    "orgs.OrgBase": [
        {"model": "communications.Location", "link_key": "locations", "mode": "refs_links", "count": 3},
        {"model": "communications.Email",    "link_key": "emails",    "mode": "refs_links", "count": 3},
        {"model": "communications.Phone",    "link_key": "phones",    "mode": "refs_links", "count": 3},
        {"model": "communications.Domain",   "link_key": "domains",   "mode": "refs_links", "count": 3},
    ],
    "orgs.Customer": [
        {"model": "communications.Location", "link_key": "locations", "mode": "refs_links", "count": 3},
        {"model": "communications.Email",    "link_key": "emails",    "mode": "refs_links", "count": 3},
        {"model": "communications.Phone",    "link_key": "phones",    "mode": "refs_links", "count": 3},
        {"model": "communications.Domain",   "link_key": "domains",   "mode": "refs_links", "count": 3},
    ],
    "orgs.Vendor": [
        {"model": "communications.Location", "link_key": "locations", "mode": "refs_links", "count": 3},
        {"model": "communications.Email",    "link_key": "emails",    "mode": "refs_links", "count": 3},
        {"model": "communications.Phone",    "link_key": "phones",    "mode": "refs_links", "count": 3},
        {"model": "communications.Domain",   "link_key": "domains",   "mode": "refs_links", "count": 3},
    ],
    "orgs.Rep": [
        {"model": "communications.Location", "link_key": "locations", "mode": "refs_links", "count": 2},
        {"model": "communications.Email",    "link_key": "emails",    "mode": "refs_links", "count": 2},
        {"model": "communications.Phone",    "link_key": "phones",    "mode": "refs_links", "count": 2},
        {"model": "communications.Domain",   "link_key": "domains",   "mode": "refs_links", "count": 2},
    ],
    "orgs.Employee": [
        {"model": "communications.Location", "link_key": "locations", "mode": "refs_links", "count": 2},
        {"model": "communications.Email",    "link_key": "emails",    "mode": "refs_links", "count": 2},
        {"model": "communications.Phone",    "link_key": "phones",    "mode": "refs_links", "count": 2},
        {"model": "communications.Domain",   "link_key": "domains",   "mode": "refs_links", "count": 2},
    ],
    "orgs.Manufacturer": [
        {"model": "communications.Location", "link_key": "locations", "mode": "refs_links", "count": 3},
        {"model": "communications.Email",    "link_key": "emails",    "mode": "refs_links", "count": 3},
        {"model": "communications.Phone",    "link_key": "phones",    "mode": "refs_links", "count": 3},
        {"model": "communications.Domain",   "link_key": "domains",   "mode": "refs_links", "count": 3},
    ],

    # Header ↔ line FK relationships (creates child rows)
    "transactions.Proposal": [
        {"model": "transactions.ProposalLine", "fk_field": "parent", "mode": "create_children", "count": 3},
    ],
    "transactions.SalesOrder": [
        {"model": "transactions.SalesOrderLine", "fk_field": "parent", "mode": "create_children", "count": 3},
    ],
    "transactions.PurchaseOrder": [
        {"model": "transactions.PurchaseOrderLine", "fk_field": "parent", "mode": "create_children", "count": 3},
    ],
    "transactions.Invoice": [
        {"model": "transactions.InvoiceLine", "fk_field": "parent", "mode": "create_children", "count": 3},
    ],
    "transactions.WorkOrder": [
        {"model": "transactions.WorkOrderLine", "fk_field": "parent", "mode": "create_children", "count": 3},
    ],

    # Line ↔ item (each line needs one item)
    "transactions.ProposalLine": [
        {"model": "products.Item", "fk_field": "item_id", "mode": "assign_fk", "count": 1},
    ],
    "transactions.SalesOrderLine": [
        {"model": "products.Item", "fk_field": "item_id", "mode": "assign_fk", "count": 1},
    ],
    "transactions.PurchaseOrderLine": [
        {"model": "products.Item", "fk_field": "item_id", "mode": "assign_fk", "count": 1},
    ],
    "transactions.InvoiceLine": [
        {"model": "products.Item", "fk_field": "item_id", "mode": "assign_fk", "count": 1},
    ],
    "transactions.WorkOrderLine": [
        {"model": "products.Item", "fk_field": "item_id", "mode": "assign_fk", "count": 1},
    ],
}
