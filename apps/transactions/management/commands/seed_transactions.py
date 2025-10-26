from __future__ import annotations

import random
from decimal import Decimal
from functools import lru_cache
from typing import Any, List

from django.apps import apps
from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.db import connection, transaction
from django.db.utils import ProgrammingError

from apps.transactions.models import (
    Invoice,
    InvoiceLine,
    Proposal,
    ProposalLine,
    PurchaseOrder,
    PurchaseOrderLine,
    SalesOrder,
    SalesOrderLine,
)


def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def _ensure_min_items(n: int = 3) -> List[int]:
    ItemModel = apps.get_model("products", "Item")
    ids = list(ItemModel.objects.values_list("id", flat=True)[:n])
    while len(ids) < n:
        idx = len(ids) + 1
        item = ItemModel.objects.create(
            name=f"Demo Item {idx}",
            sku=f"DEMO-{idx:03d}",
            uom="EA",
            price={
                "base": float(12 * idx),
                "currency": "USD",
                "tiers": [],
                "qty_breaks": [],
                "msrp": float(14 * idx),
                "history": [],
            },
            cost={
                "standard": float(7 * idx),
                "currency": "USD",
                "breaks": [],
                "components": {},
                "history": [],
            },
            quantity={
                "on_hand": 100 * idx,
                "allocated": 0,
                "available": 100 * idx,
                "on_order": 0,
            },
        )
        ids.append(int(getattr(item, "id")))
    return ids


def _first_id(app_label: str, model_name: str) -> int | None:
    Model = _get_model(app_label, model_name)
    if not Model:
        return None
    value = Model.objects.order_by("id").values_list("id", flat=True).first()
    return int(value) if value else None


def _ensure_org(org_type: str, proxy_name: str, default_name: str) -> int | None:
    Model = _get_model("orgs", proxy_name)
    if not Model:
        return None
    # Prefer a deterministic demo record if it already exists.
    default_existing = Model.objects.filter(display_name=default_name).values_list("id", flat=True).first()
    if default_existing:
        return int(default_existing)
    existing = Model.objects.order_by("id").values_list("id", flat=True).first()
    if existing:
        return int(existing)
    create_kwargs: dict[str, Any] = {"display_name": default_name, "status": "active"}
    # Ensure org_type is present for concrete model creations.
    concrete = getattr(Model._meta, "concrete_model", Model)
    fields = getattr(concrete._meta, "fields", []) if hasattr(concrete, "_meta") else []
    if any(getattr(field, "name", "") == "org_type" for field in fields):
        create_kwargs.setdefault("org_type", org_type)
    try:
        obj = Model.objects.create(**create_kwargs)
    except Exception:
        return None
    return int(getattr(obj, "id"))


def _pick_contact_id() -> int | None:
    return _first_id("core", "Contact")


def _pick_customer_org_id() -> int | None:
    return _ensure_org("customer", "Customer", "Demo Customer 1")


def _ensure_phone_id() -> int | None:
    Phone = _get_model("communications", "Phone")
    if not Phone:
        return None
    existing = Phone.objects.order_by("id").values_list("id", flat=True).first()
    if existing:
        return int(existing)
    phone = Phone.objects.create(
        number="+1-555-0100",
        country_code="+1",
        format="+1 (555) 010-0000",
        name="Demo Phone",
    )
    return int(getattr(phone, "id"))


def _ensure_email_id() -> int | None:
    Email = _get_model("communications", "Email")
    if not Email:
        return None
    existing = Email.objects.order_by("id").values_list("id", flat=True).first()
    if existing:
        return int(existing)
    email = Email.objects.create(email="demo@example.com", name="Demo Email")
    return int(getattr(email, "id"))


@lru_cache(maxsize=1)
def _existing_tables() -> set[str]:
    return set(connection.introspection.table_names())


def _table_exists(model: type) -> bool:
    return model._meta.db_table in _existing_tables()


def _reset_seed_sequences() -> None:
    if connection.vendor != "postgresql":
        return
    tables = {
        Proposal._meta.db_table,
        ProposalLine._meta.db_table,
        SalesOrder._meta.db_table,
        SalesOrderLine._meta.db_table,
        Invoice._meta.db_table,
        InvoiceLine._meta.db_table,
        PurchaseOrder._meta.db_table,
        PurchaseOrderLine._meta.db_table,
    }
    existing = _existing_tables()
    with connection.cursor() as cursor:
        for table in tables:
            if table not in existing:
                continue
            try:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                    "COALESCE((SELECT MAX(id) FROM " + table + "), 0) + 1, false)",
                    [table],
                )
            except ProgrammingError:
                # Skip tables that do not expose a PostgreSQL-backed sequence (legacy schema).
                continue


def _line_payload(item_id: int, idx: int, tx_type: str) -> dict[str, Any]:
    qty = 1 + (idx % 3)
    unit_price = Decimal(10 + 5 * (idx % 4))
    if tx_type == "invoice":
        quantity = {"packed": 0}
    elif tx_type == "order":
        quantity = {
            "placed": qty,
            "backlog": 0,
            "remaining": qty,
            "shipped": 0,
            "invoiced": 0,
            "is_fixed": False,
            "precision": 2,
        }
    else:
        quantity = {
            "placed": qty,
            "backlog": 0,
            "remaining": qty,
            "is_fixed": False,
            "precision": 2,
        }
    return {
        "item": {
            "id": item_id,
            "description": f"Line {idx + 1} for item {item_id}",
            "unit_measure": "EA",
            "line_number": idx + 1,
        },
        "quantity": quantity,
        "price": {
            "unit": float(unit_price),
            "extended": float(unit_price * qty),
            "precision": 2,
        },
        "cost": {
            "unit": float(unit_price * Decimal("0.6")),
            "extended": float(unit_price * Decimal("0.6") * qty),
            "precision": 2,
        },
        "tax": {"sales_rate": 0.0, "sales": 0.0},
        "comments": {"public": ""},
        "prefs": {"currency": "USD", "locale": "en-US", "terms": ""},
    }


class Command(DjangoBaseCommand):
    help = "Seed demo transactions: proposals, sales orders, invoices, and purchase orders with lines."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=2, help="Number of each header type to create")

    @transaction.atomic
    def handle(self, *args, **options):
        count = int(options["count"])
        _reset_seed_sequences()

        item_ids = _ensure_min_items(max(3, count))
        contact_id = _pick_contact_id()
        customer_org_id = _pick_customer_org_id()
        vendor_org_id = _ensure_org("vendor", "Vendor", "Demo Vendor 1")
        phone_id = _ensure_phone_id()
        email_id = _ensure_email_id()

        proposal_available = _table_exists(Proposal)
        proposal_line_available = _table_exists(ProposalLine)
        sales_order_available = _table_exists(SalesOrder)
        sales_order_line_available = _table_exists(SalesOrderLine)
        invoice_available = _table_exists(Invoice)
        invoice_line_available = _table_exists(InvoiceLine)
        purchase_order_available = _table_exists(PurchaseOrder)
        purchase_order_line_available = _table_exists(PurchaseOrderLine)

        self.stdout.write(
            self.style.NOTICE(
                "Using items: {items}; contact: {contact}; customer_org: {customer}; "
                "vendor_org: {vendor}; phone: {phone}; email: {email}".format(
                    items=item_ids,
                    contact=contact_id or "none",
                    customer=customer_org_id or "none",
                    vendor=vendor_org_id or "none",
                    phone=phone_id or "none",
                    email=email_id or "none",
                )
            )
        )

        created_ids: dict[str, list[int]] = {
            "proposals": [],
            "sales_orders": [],
            "invoices": [],
            "purchase_orders": [],
        }

        def _header_links(kind: str) -> dict[str, Any]:
            links: dict[str, Any] = {"links": {}}
            if kind == "purchase_order":
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
            links["links"]["address"] = [{"billto": 1}, {"shipto": 3}]
            if phone_id:
                links["links"]["phone"] = [phone_id]
            if email_id:
                links["links"]["email"] = [email_id]
            return links

        if not proposal_available:
            self.stdout.write(self.style.WARNING("Skipping proposal seeding: proposal table missing."))
        else:
            warned_proposal_lines = False
            for i in range(count):
                proposal = Proposal.objects.create(
                    name=f"Demo Proposal {i + 1}",
                    refs=_header_links("proposal"),
                    prefs={"currency": "USD"},
                )
                created_ids["proposals"].append(int(proposal.id))
                proposal_line_ids: list[int] = []
                if proposal_line_available:
                    for li, item_id in enumerate(random.sample(item_ids, k=min(2, len(item_ids)))):
                        payload = _line_payload(item_id, li, tx_type="proposal")
                        line = ProposalLine(parent=proposal)
                        line.item = payload["item"]
                        line.quantity = payload["quantity"]
                        line.price = payload["price"]
                        line.cost = payload["cost"]
                        line.tax = payload["tax"]
                        line.prefs = payload["prefs"]
                        line.comments = payload["comments"]
                        line.save()
                        proposal_line_ids.append(int(line.id))
                elif not warned_proposal_lines:
                    self.stdout.write(self.style.WARNING("Skipping proposal lines: table missing."))
                    warned_proposal_lines = True
                links = proposal.refs or {}
                link_bucket = links.get("links") or {}
                link_bucket["proposal_lin"] = proposal_line_ids
                links["links"] = link_bucket
                proposal.refs = links
                proposal.save(update_fields=["refs"])

        if not sales_order_available:
            self.stdout.write(self.style.WARNING("Skipping sales order seeding: table missing."))
        else:
            warned_sales_order_lines = False
            base_so_count = SalesOrder.objects.count() or 0
            for i in range(count):
                order_no = f"SO-{1000 + base_so_count + i}"
                sales_order = SalesOrder.objects.create(
                    order_no=order_no,
                    refs=_header_links("sales_order"),
                    prefs={"currency": "USD"},
                )
                created_ids["sales_orders"].append(int(sales_order.id))
                sales_order_line_ids: list[int] = []
                if sales_order_line_available:
                    for li, item_id in enumerate(random.sample(item_ids, k=min(3, len(item_ids)))):
                        payload = _line_payload(item_id, li, tx_type="order")
                        line = SalesOrderLine(parent=sales_order)
                        line.item = payload["item"]
                        line.quantity = payload["quantity"]
                        line.price = payload["price"]
                        line.cost = payload["cost"]
                        line.tax = payload["tax"]
                        line.prefs = payload["prefs"]
                        line.comments = payload["comments"]
                        line.save()
                        sales_order_line_ids.append(int(line.id))
                elif not warned_sales_order_lines:
                    self.stdout.write(self.style.WARNING("Skipping sales order lines: table missing."))
                    warned_sales_order_lines = True
                links = sales_order.refs or {}
                link_bucket = links.get("links") or {}
                link_bucket["sales_order_line"] = sales_order_line_ids
                links["links"] = link_bucket
                sales_order.refs = links
                sales_order.save(update_fields=["refs"])

        if not invoice_available:
            self.stdout.write(self.style.WARNING("Skipping invoice seeding: invoice table missing."))
        else:
            warned_invoice_lines = False
            for i in range(count):
                invoice = Invoice.objects.create(
                    refs=_header_links("invoice"),
                    prefs={"currency": "USD"},
                )
                created_ids["invoices"].append(int(invoice.id))
                invoice_line_ids: list[int] = []
                if invoice_line_available:
                    for li, item_id in enumerate(random.sample(item_ids, k=min(2, len(item_ids)))):
                        payload = _line_payload(item_id, li, tx_type="invoice")
                        line = InvoiceLine(parent=invoice)
                        line.item = payload["item"]
                        line.quantity = payload["quantity"]
                        line.price = payload["price"]
                        line.cost = payload["cost"]
                        line.tax = payload["tax"]
                        line.prefs = payload["prefs"]
                        line.comments = payload["comments"]
                        line.save()
                        invoice_line_ids.append(int(line.id))
                elif not warned_invoice_lines:
                    self.stdout.write(self.style.WARNING("Skipping invoice lines: table missing."))
                    warned_invoice_lines = True
                links = invoice.refs or {}
                link_bucket = links.get("links") or {}
                link_bucket["invoice_line"] = invoice_line_ids
                links["links"] = link_bucket
                invoice.refs = links
                invoice.save(update_fields=["refs"])

        if not purchase_order_available:
            self.stdout.write(self.style.WARNING("Skipping purchase order seeding: purchase order table missing."))
        else:
            warned_purchase_lines = False
            base_po_count = PurchaseOrder.objects.count() or 0
            for i in range(count):
                po_no = f"PO-{3000 + base_po_count + i}"
                purchase_order = PurchaseOrder.objects.create(
                    po_no=po_no,
                    refs=_header_links("purchase_order"),
                    prefs={"currency": "USD"},
                )
                created_ids["purchase_orders"].append(int(purchase_order.id))
                purchase_order_line_ids: list[int] = []
                if purchase_order_line_available:
                    for li, item_id in enumerate(random.sample(item_ids, k=min(2, len(item_ids)))):
                        payload = _line_payload(item_id, li, tx_type="order")
                        line = PurchaseOrderLine(parent=purchase_order)
                        line.item = payload["item"]
                        line.quantity = payload["quantity"]
                        line.price = payload["price"]
                        line.cost = payload["cost"]
                        line.tax = payload["tax"]
                        line.prefs = payload["prefs"]
                        line.comments = payload["comments"]
                        line.save()
                        purchase_order_line_ids.append(int(line.id))
                elif not warned_purchase_lines:
                    self.stdout.write(self.style.WARNING("Skipping purchase order lines: table missing."))
                    warned_purchase_lines = True
                links = purchase_order.refs or {}
                link_bucket = links.get("links") or {}
                link_bucket["purchase_order_line"] = purchase_order_line_ids
                links["links"] = link_bucket
                purchase_order.refs = links
                purchase_order.save(update_fields=["refs"])

        self.stdout.write(self.style.SUCCESS(f"Seeded: {created_ids}"))
