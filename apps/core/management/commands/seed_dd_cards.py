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
                {"field": "amount", "agg": "sum", "label": "Total", "format": "currency"},
            ],
        },
        "contact": {
            "label": "Contacts",
            "link": "/contact",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "customer": {
            "label": "Customers",
            "link": "/customer",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "vendor": {
            "label": "Vendors",
            "link": "/vendor",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
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
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "item": {
            "label": "Items",
            "link": "/item",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
                {"field": "price", "agg": "avg", "label": "Avg Price", "format": "currency"},
            ],
        },
        "action": {
            "label": "Actions",
            "link": "/action",
            "filters": {"is_active": True},
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
            "distribution": {
                "field": "status",
                "type": "category",
                "labels": ["open", "in_progress", "complete", "review"],
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
        "warehouse": {
            "label": "Warehouses",
            "link": "/warehouse",
            "metrics": [
                {"field": "id", "agg": "count", "label": "Count"},
            ],
        },
        "catalog": {
            "label": "Catalogs",
            "link": "/catalog",
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
            "cards": ["order", "invoice", "proposal", "customer", "contact", "purchase"],
            "default_model": "action",
            "quick_adds": [
                {"label": "+ Order", "to": "/order?action=new", "accent": "blue"},
                {"label": "+ Proposal", "to": "/proposal?action=new", "accent": "indigo"},
                {"label": "+ Purchase", "to": "/purchase?action=new", "accent": "emerald"},
                {"label": "+ Customer", "to": "/customer?action=new", "accent": "amber"},
                {"label": "+ Contact", "to": "/contact?action=new", "accent": "purple"},
            ],
        },
        "accounting": {
            "label": "Accounting",
            "route": "/accounting",
            "cards": ["invoice", "payment", "ledger", "gl_journal"],
            "default_model": "gl_journal",
            "quick_adds": [
                {"label": "Payments", "to": "/payment", "accent": "teal"},
                {"label": "Expenses", "to": "/payment?filter=type:expense", "accent": "rose"},
                {"label": "Statements", "to": "/statement_line", "accent": "orange"},
            ],
        },
        "inventory": {
            "label": "Inventory",
            "route": "/inventory-dashboard",
            "cards": ["item", "warehouse"],
            "default_model": "item",
        },
        "operations": {
            "label": "Operations",
            "route": "/operations",
            "cards": ["action", "project"],
            "default_model": "action",
        },
        "products": {
            "label": "Products",
            "route": "/products",
            "cards": ["item", "catalog", "variant"],
            "default_model": "item",
        },
        "transactions": {
            "label": "Transactions",
            "route": "/transactions",
            "cards": ["order", "invoice", "proposal", "purchase"],
            "default_model": "order",
        },
        "orgs": {
            "label": "Organizations",
            "route": "/orgs",
            "cards": ["customer", "vendor", "manufacturer", "rep"],
            "default_model": "customer",
        },
        "alice": {
            "label": "Alice",
            "route": "/alice-dashboard",
            "cards": ["action", "notification", "setting"],
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
