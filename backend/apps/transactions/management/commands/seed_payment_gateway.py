"""Seed the payment gateway Setting record.

Creates a Setting with purpose='wc:payment_gateway' that holds:
  - config.gateway[] — scannable registry of gateway entries
  - config.token_rule — what WC3 stores vs never stores
  - config.currency — installation default

Each gateway entry is thin — just name, type, GL, and connection_id.
Rules, statement_source, credentials live on Connection.config.
Manual gateways (wire/check) need no Connection.

Usage: ./manage.py seed_payment_gateway
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


PAYMENT_GATEWAY_CONFIG = {
    "gateway": [
        {
            "name": "wellsfargo_checking",
            "type": "manual",
            "account": "Wells Fargo Business Checking",
            "gl_account": "",
            "is_default": True,
            "connection_id": None,
        },
        {
            "name": "check",
            "type": "manual",
            "account": "Business checks",
            "gl_account": "",
            "is_default": False,
            "connection_id": None,
        },
    ],
    "token_rule": {
        "store": ["pm_token", "last4", "brand", "exp_month", "exp_year", "fingerprint"],
        "never_store": ["card_number", "cvv", "full_token", "replayable_credentials"],
        "note": "Token in a token. WC3 stores a reference to Spreedly's token. Card data never enters WC3.",
    },
    "currency": "USD",
    "test_mode": True,
}


class Command(BaseCommand):
    help = "Seed the payment gateway Setting record"

    def handle(self, *args, **options):
        setting, created = Setting.objects.get_or_create(
            purpose='wc:payment_gateway',
            parent_model='setting',
            defaults={
                'ida': 'payment-gateway',
                'config': PAYMENT_GATEWAY_CONFIG,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created payment_gateway Setting #{setting.id}"))
            self.stdout.write("Seeded gateways:")
            for gw in PAYMENT_GATEWAY_CONFIG['gateway']:
                default = " (default)" if gw.get('is_default') else ""
                self.stdout.write(f"  - {gw['name']} [{gw['type']}]{default}")
            self.stdout.write("\nTo add Spreedly:")
            self.stdout.write("  1. Create a Connection with Spreedly credentials in config.spreedly")
            self.stdout.write("  2. Add a gateway entry with type='spreedly' and connection_id=<Connection.id>")
        else:
            config = setting.config or {}
            for key, val in PAYMENT_GATEWAY_CONFIG.items():
                if key == 'gateway':
                    if 'gateway' not in config:
                        config['gateway'] = val
                elif key not in config:
                    config[key] = val
                elif isinstance(val, dict) and isinstance(config[key], dict):
                    for k, v in val.items():
                        if k not in config[key]:
                            config[key][k] = v
            setting.config = config
            setting.save(update_fields=['config'])
            self.stdout.write(self.style.SUCCESS(f"Updated payment_gateway Setting #{setting.id} (merged new keys)"))
