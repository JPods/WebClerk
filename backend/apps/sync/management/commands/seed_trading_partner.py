"""
Seed an example trading partner Connection for PO→SO cross-instance commerce.

Creates a pair of Connection records (buyer side and vendor side) that
demonstrate the full PO→SO bundle workflow.

Usage:
    python manage.py seed_trading_partner
    python manage.py seed_trading_partner --key mysharedkey123
"""
import secrets
from django.core.management.base import BaseCommand

from apps.sync.models.connection import Connection


class Command(BaseCommand):
    help = "Create example trading partner Connection records for PO→SO bundles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            type=str,
            default="",
            help="Shared sync key (auto-generated if omitted)",
        )
        parser.add_argument(
            "--vendor-endpoint",
            type=str,
            default="http://localhost:8000/wcapi/sync/receive/",
            help="Vendor's receive endpoint URL",
        )
        parser.add_argument(
            "--buyer-callback",
            type=str,
            default="http://localhost:8000/wcapi/sync/bundle/callback/",
            help="Buyer's callback endpoint URL",
        )

    def handle(self, *args, **options):
        shared_key = options["key"] or secrets.token_urlsafe(32)
        vendor_endpoint = options["vendor_endpoint"]
        buyer_callback = options["buyer_callback"]

        # Buyer-side connection (points to vendor)
        buyer_conn, created = Connection.objects.get_or_create(
            name="Trading Partner — Vendor (buyer side)",
            type="api",
            defaults={
                "status": "active",
                "comment": (
                    "PO→SO trading partner connection. Buyer side.\n"
                    "Send purchase orders as bundles to vendor's WC3 instance.\n"
                    "Cost on PO maps to price on SO via schema_map."
                ),
                "config": {
                    "channel": "bundle",
                    "direction": "push",
                    "endpoint": vendor_endpoint,
                    "callback_endpoint": buyer_callback,
                    "key": shared_key,
                    "auth_method": "sync_key",
                    "content_types": ["po_to_so"],
                    "schema_map": {
                        "cost_to_price": {
                            "unit": "unit",
                            "unit_base": "unit_base",
                            "discount_percent": "discount_percent",
                            "discount_amount": "discount_amount",
                            "extended": "extended",
                            "precision": "precision",
                        },
                    },
                },
                "maps": {
                    "po_to_so": {
                        "header": {
                            "attention": "attention",
                            "address_full": "address_full",
                            "email": "email",
                            "phone": "phone",
                            "ship_via": "ship_via",
                            "dt_needed": "dt_needed",
                        },
                        "line": {
                            "cost": "price",
                            "item": "item",
                            "quantity": "quantity",
                            "physical": "physical",
                        },
                    },
                },
            },
        )

        # Vendor-side connection (accepts from buyer)
        vendor_conn, v_created = Connection.objects.get_or_create(
            name="Trading Partner — Buyer (vendor side)",
            type="api",
            defaults={
                "status": "active",
                "comment": (
                    "PO→SO trading partner connection. Vendor side.\n"
                    "Receives purchase order bundles as pending sales orders.\n"
                    "Sales team reviews and approves."
                ),
                "config": {
                    "channel": "bundle",
                    "direction": "pull",
                    "callback_endpoint": buyer_callback,
                    "key": shared_key,
                    "auth_method": "sync_key",
                    "content_types": ["po_to_so"],
                },
            },
        )

        action = "Created" if created else "Already exists"
        v_action = "Created" if v_created else "Already exists"

        self.stdout.write(self.style.SUCCESS(
            f"\nBuyer connection: {action} (id={buyer_conn.pk})"
            f"\nVendor connection: {v_action} (id={vendor_conn.pk})"
            f"\nShared key: {shared_key}"
            f"\nVendor endpoint: {vendor_endpoint}"
            f"\nBuyer callback: {buyer_callback}"
            f"\n\nPO→SO flow:"
            f"\n  1. POST /wcapi/sync/po-to-so/<purchase_id>/  body: {{\"connection_id\": {buyer_conn.pk}}}"
            f"\n  2. Vendor reviews at /admin/ or databrowser"
            f"\n  3. POST /wcapi/sync/bundle/<uuid>/approve/"
            f"\n  4. GET  /wcapi/sync/po-status/<purchase_id>/<uuid>/"
        ))
