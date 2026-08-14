"""Seed the payment gateway Setting record for Spreedly.

Creates a Setting with purpose='wc:payment_gateway' that holds:
  - Spreedly environment key and access secret
  - Active gateway token (Stripe, PayPal, etc. configured in Spreedly)
  - Webhook signing key
  - Token storage rules

Users configure their own Spreedly account and gateway credentials.
WC3 never sees card data — Spreedly's client-side SDK handles collection.

Usage: ./manage.py seed_payment_gateway
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


PAYMENT_GATEWAY_CONFIG = {
    "spreedly": {
        "environment_key": "",       # public — used in client-side SDK
        "access_secret": "",         # server-only — NEVER in client code
        "webhook_signing_key": "",   # for verifying webhook callbacks
    },
    "active_gateway_token": "",      # Spreedly gateway token for the user's chosen gateway
    "active_gateway_type": "",       # stripe, paypal, braintree, etc.
    "supported_gateways": {
        "stripe": {
            "description": "Stripe via Spreedly",
            "fields": ["login"],
            "notes": "Use a Stripe Restricted API Key (rk_live_...)",
        },
        "paypal": {
            "description": "PayPal via Spreedly",
            "fields": ["login", "password", "signature"],
            "notes": "PayPal NVP credentials",
        },
        "braintree": {
            "description": "Braintree via Spreedly",
            "fields": ["merchant_id", "public_key", "private_key"],
            "notes": "Braintree API credentials",
        },
        "authorize_net": {
            "description": "Authorize.Net via Spreedly",
            "fields": ["login", "password"],
            "notes": "API Login ID and Transaction Key",
        },
    },
    "token_rule": {
        "store": ["pm_token", "last4", "brand", "exp_month", "exp_year", "fingerprint"],
        "never_store": ["card_number", "cvv", "full_token", "replayable_credentials"],
        "note": "Token in a token. WC3 stores a reference to Spreedly's token, which is itself a reference to the card. Card data never enters WC3.",
    },
    "currency": "USD",
    "test_mode": True,
}


class Command(BaseCommand):
    help = "Seed the payment gateway Setting record for Spreedly"

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
            self.stdout.write("Next steps:")
            self.stdout.write("  1. Create a Spreedly account at spreedly.com")
            self.stdout.write("  2. Add your environment_key and access_secret to the Setting")
            self.stdout.write("  3. Add your gateway (Stripe/PayPal) in Spreedly dashboard")
            self.stdout.write("  4. Copy the gateway token to active_gateway_token")
            self.stdout.write("  5. Set test_mode to False when ready for production")
        else:
            config = setting.config or {}
            for section, defaults in PAYMENT_GATEWAY_CONFIG.items():
                if section not in config:
                    config[section] = defaults
                elif isinstance(defaults, dict) and isinstance(config[section], dict):
                    for key, val in defaults.items():
                        if key not in config[section]:
                            config[section][key] = val
            setting.config = config
            setting.save(update_fields=['config'])
            self.stdout.write(self.style.SUCCESS(f"Updated payment_gateway Setting #{setting.id} (merged new keys)"))
