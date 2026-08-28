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
            "carrier_code": "fedex",
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
            "carrier_code": "ups",
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
            "carrier_code": "usps",
            "account": "USPS",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
            "connection_purpose": "",
            "connection_status": "",
        },
        {
            "name": "dhl",
            "type": "api",
            "carrier_code": "dhl",
            "account": "DHL Express",
            "gl_account": "",
            "is_default": False,
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
    help = "Seed the shipping service Setting record with FedEx, UPS, USPS, DHL"

    def handle(self, *args, **options):
        setting, created = Setting.objects.get_or_create(
            purpose='wc:shipping_service',
            parent_model='setting',
            defaults={
                'ida': 'shipping-service',
                'config': SHIPPING_SERVICE_CONFIG,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created shipping_service Setting #{setting.id}"))
            self.stdout.write("Seeded carriers:")
            for svc in SHIPPING_SERVICE_CONFIG['service']:
                self.stdout.write(f"  - {svc['name']} [{svc['type']}] — dormant until Connection created")
            self.stdout.write("\nTo activate a carrier:")
            self.stdout.write("  1. Create a Connection with CarrierCredentials in config")
            self.stdout.write("  2. Set connection_id, connection_purpose, connection_status on the entry")
        else:
            config = setting.config or {}
            for key, val in SHIPPING_SERVICE_CONFIG.items():
                if key == 'service':
                    if 'service' not in config:
                        config['service'] = val
                elif key not in config:
                    config[key] = val
            setting.config = config
            setting.save(update_fields=['config'])
            self.stdout.write(self.style.SUCCESS(f"Updated shipping_service Setting #{setting.id} (merged new keys)"))
