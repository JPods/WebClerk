"""
seed_dd_cards — Seed the dd-card base Setting record.

One Setting, one behavior pattern. Contains:
  - cards:      per-model metric definitions (what to show)
  - dashboards: named dashboard compositions (which cards, which list)

Usage:
    ./bin/python manage.py seed_dd_cards           # create if missing
    ./bin/python manage.py seed_dd_cards --force    # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


DD_CARD_CONFIG = {
    "cards": {
        # ── Transaction cards ──
        "order": {
            "label": "Orders",
            "link": "/order",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "total", "agg": "sum", "label": "Value", "format": "currency"},
                {"field": "cost", "agg": "sum", "label": "Cost", "format": "currency"},
                {"agg": "margin_pct", "fields": ["total", "cost"], "label": "Margin", "format": "percent"},
            ],
            "distribution": {
                "field": "margin_pct",
                "buckets": [10, 25, 40],
                "labels": ["<10%", "10-25%", "25-40%", ">40%"],
            },
        },
        "invoice": {
            "label": "Invoices",
            "link": "/invoice",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "total", "agg": "sum", "label": "Total", "format": "currency"},
                {"field": "balance", "agg": "sum", "label": "Balance", "format": "currency"},
                {"agg": "pct", "fields": ["balance", "total"], "label": "Collected", "format": "percent", "invert": True},
            ],
        },
        "proposal": {
            "label": "Proposals",
            "link": "/proposal",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "total", "agg": "sum", "label": "Value", "format": "currency"},
            ],
        },
        "purchase": {
            "label": "Purchases",
            "link": "/purchase",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "total", "agg": "sum", "label": "Total", "format": "currency"},
            ],
        },
        "payment": {
            "label": "Payments",
            "link": "/payment",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "amount", "agg": "sum", "label": "Received", "format": "currency", "filters": {"amount__gt": 0}},
                {"field": "amount", "agg": "sum", "label": "Disbursed", "format": "currency", "filters": {"amount__lt": 0}},
            ],
        },
        "receipt": {
            "label": "Receipts",
            "link": "/receipt",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "workorder": {
            "label": "Work Orders",
            "link": "/workorder",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
            "distribution": {
                "field": "status",
                "type": "category",
                "labels": ["open", "in_progress", "complete"],
            },
        },
        "requisition": {
            "label": "Requisitions",
            "link": "/requisition",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        # ── Org cards ──
        "contact": {
            "label": "Contacts",
            "link": "/contact",
            "server_action": "get_contact_health",
            "metrics": [],
        },
        "customer": {
            "label": "Customers",
            "link": "/customer",
            "server_action": "get_customer_summary",
            "metrics": [],
        },
        "vendor": {
            "label": "Vendors",
            "link": "/vendor",
            "server_action": "get_vendor_summary",
            "metrics": [],
        },
        "manufacturer": {
            "label": "Manufacturers",
            "link": "/manufacturer",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "rep": {
            "label": "Reps",
            "link": "/rep",
            "server_action": "get_rep_summary",
            "metrics": [],
        },
        "employee": {
            "label": "Employees",
            "link": "/employee",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        # ── Product cards ──
        "item": {
            "label": "Items",
            "link": "/item",
            "server_action": "get_item_summary",
            "metrics": [],
        },
        "catalog": {
            "label": "Catalogs",
            "link": "/catalog",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "warehouse": {
            "label": "Warehouses",
            "link": "/warehouse",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "serial": {
            "label": "Serials",
            "link": "/serial",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "specification": {
            "label": "Specifications",
            "link": "/specification",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "bill_of_material": {
            "label": "BOM",
            "link": "/bill_of_material",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "variant": {
            "label": "Variants",
            "link": "/variant",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        # ── Action cards ──
        "action": {
            "label": "Actions",
            "link": "/action",
            "server_action": "get_action_summary",
            "metrics": [],
        },
        # ── Administration cards ──
        "document": {
            "label": "Documents",
            "link": "/document",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
            "distribution": {
                "field": "status",
                "type": "category",
                "labels": ["draft", "active", "archived"],
            },
        },
        "gl_journal": {
            "label": "GL Journal",
            "link": "/gl_journal",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Entries"},
                {"field": "debit", "agg": "sum", "label": "Debits", "format": "currency"},
                {"field": "credit", "agg": "sum", "label": "Credits", "format": "currency"},
            ],
        },
        "ledger": {
            "label": "Ledger",
            "link": "/ledger",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "value_original", "agg": "sum", "label": "Original", "format": "currency"},
                {"field": "value_available", "agg": "sum", "label": "Available", "format": "currency"},
            ],
        },
        "connection": {
            "label": "Sync Connections",
            "link": "/connection",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
            "distribution": {
                "field": "status",
                "type": "category",
                "labels": ["active", "pending", "error", "disabled"],
            },
        },
        "campaign": {
            "label": "Campaigns",
            "link": "/campaign",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "count_customers_actual", "agg": "sum", "label": "Customers"},
                {"field": "value_invoices", "agg": "sum", "label": "Revenue", "format": "currency"},
            ],
        },
        "audit": {
            "label": "Audit",
            "link": "/audit",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "report": {
            "label": "Reports",
            "link": "/report",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "pending": {
            "label": "Pending",
            "link": "/pending",
            "server_action": "get_pending_summary",
            "metrics": [],
        },
        "notification": {
            "label": "Notifications",
            "link": "/notification",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "setting": {
            "label": "Settings",
            "link": "/setting",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "project": {
            "label": "Projects",
            "link": "/project",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
    },
    "dashboards": {
        "sales": {
            "label": "Sales & Service",
            "route": "/dashboard",
            "rows": [
                ["order", "invoice", "proposal", "customer", "contact", "payment", "rep"],
            ],
            "default_model": "action",
            "quick_adds": [
                {"label": "+ Order", "to": "/order?action=new", "accent": "blue"},
                {"label": "+ Proposal", "to": "/proposal?action=new", "accent": "indigo"},
                {"label": "+ Purchase", "to": "/purchase?action=new", "accent": "emerald"},
                {"label": "+ Customer", "to": "/customer?action=new", "accent": "amber"},
                {"label": "+ Contact", "to": "/contact?action=new", "accent": "purple"},
            ],
        },
        "products": {
            "label": "Products",
            "route": "/products",
            "rows": [
                ["item", "catalog", "warehouse", "purchase", "workorder"],
                ["serial", "specification", "bill_of_material"],
            ],
            "default_model": "action",
        },
        "transactions": {
            "label": "Transactions",
            "route": "/transactions",
            "rows": [
                ["order", "invoice", "purchase", "payment"],
                ["proposal", "receipt", "workorder", "requisition"],
            ],
            "default_model": "action",
        },
        "orgs": {
            "label": "Organizations",
            "route": "/orgs",
            "rows": [
                ["customer", "vendor", "manufacturer", "rep", "employee"],
            ],
            "default_model": "action",
        },
        "admin": {
            "label": "Administration",
            "route": "/admin-dashboard",
            "rows": [
                ["document", "gl_journal", "connection", "campaign"],
                ["audit", "report", "pending"],
            ],
            "default_model": "action",
        },
        "alice": {
            "label": "Alice",
            "route": "/alice-dashboard",
            "rows": [
                ["action", "notification", "setting"],
            ],
            "default_model": "notification",
        },
    },
}


class Command(BaseCommand):
    help = "Seed the dd-card base Setting — one record, all card + dashboard configs"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Overwrite existing")

    def handle(self, *args, **options):
        force = options.get("force", False)

        existing = Setting.objects.filter(purpose="dd_card", name="dd_card:base").first()

        if existing and not force:
            self.stdout.write(self.style.WARNING(
                f"dd_card:base already exists (id={existing.id}). Use --force to overwrite."
            ))
            return

        if existing:
            existing.config = DD_CARD_CONFIG
            existing.save()
            self.stdout.write(self.style.SUCCESS(
                f"Updated dd_card:base (id={existing.id}) — "
                f"{len(DD_CARD_CONFIG['cards'])} cards, "
                f"{len(DD_CARD_CONFIG['dashboards'])} dashboards"
            ))
        else:
            obj = Setting.objects.create(
                name="dd_card:base",
                purpose="dd_card",
                config=DD_CARD_CONFIG,
            )
            self.stdout.write(self.style.SUCCESS(
                f"Created dd_card:base (id={obj.id}) — "
                f"{len(DD_CARD_CONFIG['cards'])} cards, "
                f"{len(DD_CARD_CONFIG['dashboards'])} dashboards"
            ))
