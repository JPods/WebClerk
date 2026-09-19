"""Seed the shipping service Setting record.

Creates a Setting with purpose='wc:shipping_service' that holds:
  - config.service[] — scannable registry of carrier entries

Each entry is thin — name, type, carrier_code, GL, connection pointer.
Service levels, rules, credentials live on Connection.config.

Usage: ./manage.py seed_shipping_service
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


SHIPPING_SERVICE_CONFIG = {
    "service": [
        {
            "name": "fedex",
            "type": "api",
            "fulfillment": "shipped",
            "comment": "Obtain a connection key: create a Connection with the carrier's API credentials, then set connection_id/purpose/status on this entry. Dormant until then.",
            "carrier_code": "fedex",
            "connection_ida": "conn-carrier-fedex",
            "account": "FedEx",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "ups",
            "type": "api",
            "fulfillment": "shipped",
            "comment": "Obtain a connection key: create a Connection with the carrier's API credentials, then set connection_id/purpose/status on this entry. Dormant until then.",
            "carrier_code": "ups",
            "connection_ida": "conn-carrier-ups",
            "account": "UPS",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "usps",
            "type": "api",
            "fulfillment": "shipped",
            "comment": "Obtain a connection key: create a Connection with the carrier's API credentials, then set connection_id/purpose/status on this entry. Dormant until then.",
            "carrier_code": "usps",
            "account": "USPS",
            "gl_account": "",
            "rate_method": "percent_of_goods",
            "rate_percent": 4,
            "is_default": True,
            "connection_ida": "conn-carrier-usps",
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "dhl",
            "type": "api",
            "fulfillment": "shipped",
            "comment": "Obtain a connection key: create a Connection with the carrier's API credentials, then set connection_id/purpose/status on this entry. Dormant until then.",
            "carrier_code": "dhl",
            "account": "DHL Express",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        # ── Test data (Bill, 2026-09-19) ────────────────────────────────────
        {
            "name": "test_4%",
            "type": "test",
            "fulfillment": "shipped",
            "account": "Test 4% shipping",
            "rate_method": "percent_of_goods",
            "rate_percent": 4,
            "comment": "Test data only: charges shipping at 4% of goods so test documents carry shipping into totals, journal entries (shipping revenue) and values. No connection key needed. Not for customers.",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        # ── Demo rate (Bill, 2026-09-19): shipping at 4% of goods, so documents
        #    carry shipping into totals, journal entries and values. With tax at
        #    test_8% (2 × 4%), a doubling error shows at a glance. ─────────────
        {
            "name": "test_4%",
            "type": "rate",
            "fulfillment": "shipped",
            "account": "Shipping 4% of goods",
            "rate_method": "percent_of_goods",
            "rate_percent": 4,
            "comment": "Shipping charged at 4% of goods. No connection key needed.",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        # ── Local fulfillment: the proximity path (WhatIf C-W38-16) ──────────
        {
            "name": "pickup",
            "type": "local",
            "fulfillment": "pickup",
            "account": "Pickup / Will Call",
            "aliases": ["will call", "will-call", "pick up", "in store", "counter"],
            "comment": "The customer collects at the store. No connection key needed.",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "local_delivery",
            "type": "local",
            "fulfillment": "delivered",
            "account": "Local Delivery (our vehicle)",
            "aliases": ["our truck", "delivery"],
            "comment": "Delivered by the business itself. No connection key needed.",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "courier",
            "type": "api",
            "fulfillment": "delivered",
            "account": "Local Courier",
            "comment": "Same-day local courier service. Obtain a connection key: create a Connection with the courier's API credentials, then set connection_id/purpose/status on this entry. Dormant until then.",
            "gl_account": "",
            "is_default": False,
            "connection_ida": "conn-carrier-courier",
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "jpods",
            "type": "api",
            "fulfillment": "delivered",
            "account": "JPods (Physical Internet)",
            "comment": "Station-to-station delivery on a JPods network. Obtain a connection key: create a Connection to the local JPods network (Natalie, trip booking), then set connection_id/purpose/status on this entry. Dormant until then.",
            "gl_account": "",
            "is_default": False,
            "connection_ida": "conn-carrier-jpods",
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "freight",
            "type": "api",
            "fulfillment": "shipped",
            "account": "Freight (LTL)",
            "comment": "Less-than-truckload freight. Obtain a connection key: create a Connection with the freight broker's or carrier's API credentials, then set connection_id/purpose/status on this entry. Dormant until then.",
            "gl_account": "",
            "is_default": False,
            "connection_ida": "conn-carrier-freight",
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
    ],
    "default_origin_zip": "",
    "default_origin_country": "US",
    "dimensional_weight_divisor": 139,
}


class Command(BaseCommand):
    help = "Seed the shipping service Setting (ship_via choices): carriers, pickup, local delivery, courier, JPods, freight"

    def handle(self, *args, **options):
        setting = Setting.objects.filter(purpose='wc:shipping_service', parent_model='setting').first()
        created = setting is None
        if created:
            setting = Setting(purpose='wc:shipping_service', parent_model='setting',
                              ida='shipping-service', config=SHIPPING_SERVICE_CONFIG)
            setting._setting_create_authorized = True       # a seed command creates it deliberately
            setting.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created shipping_service Setting #{setting.id}"))
            self.stdout.write("Seeded carriers:")
            for svc in SHIPPING_SERVICE_CONFIG['service']:
                self.stdout.write(f"  - {svc['name']} [{svc['type']}] — dormant until Connection created")
            self.stdout.write("\nTo activate a carrier:")
            self.stdout.write("  1. Create a Connection with credentials in config")
            self.stdout.write("  2. Set connection_id, connection_purpose, connection_status on the entry")
        else:
            config = setting.config or {}
            for key, val in SHIPPING_SERVICE_CONFIG.items():
                if key == 'service':
                    existing = {e.get('name'): e for e in config.get('service') or []}
                    for entry in val:
                        if entry['name'] not in existing:
                            config.setdefault('service', []).append(entry)
                        else:
                            for k in ('fulfillment', 'comment', 'aliases'):
                                if k in entry and k not in existing[entry['name']]:
                                    existing[entry['name']][k] = entry[k]
                elif key not in config:
                    config[key] = val
            setting.config = config
            setting.save(update_fields=['config'])
            self.stdout.write(self.style.SUCCESS(f"Updated shipping_service Setting #{setting.id} (merged new keys)"))
