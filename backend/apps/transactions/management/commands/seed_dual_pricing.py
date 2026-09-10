"""Seed the dual pricing Setting record.

Creates a Setting with purpose='wc:dual_pricing' that configures the
cash discount / dual pricing program. When enabled, card customers
see a higher total; cash/ACH/check customers pay the base price.

Legal in all 50 US states when framed as a cash discount (Durbin
Amendment, Dodd-Frank 2010). Debit cards cannot be surcharged.

Usage: ./manage.py seed_dual_pricing
       ./manage.py seed_dual_pricing --enable    # create enabled
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


DUAL_PRICING_CONFIG = {
    "enabled": False,
    "card_rate": 3.5,
    "disclosure_text": "Save {rate}% by paying with ACH, check, or cash.",
    "gl_account": "REV-SURCHARGE-000",
    "exempt_methods": ["cash", "check", "ach", "wire", "debit"],
    "apply_before_tax": True,
}


class Command(BaseCommand):
    help = "Seed the dual pricing Setting record"

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable', action='store_true',
            help='Create the Setting with enabled=True',
        )

    def handle(self, *args, **options):
        config = {**DUAL_PRICING_CONFIG}
        if options['enable']:
            config['enabled'] = True

        setting, created = Setting.objects.get_or_create(
            purpose='wc:dual_pricing',
            parent_model='setting',
            defaults={
                'ida': 'dual-pricing',
                'config': config,
            },
        )

        if created:
            status = "ENABLED" if config['enabled'] else "DISABLED (run with --enable to activate)"
            self.stdout.write(self.style.SUCCESS(
                f"Created dual_pricing Setting #{setting.id} — {status}"
            ))
            self.stdout.write(f"  Card rate: {config['card_rate']}%")
            self.stdout.write(f"  GL account: {config['gl_account']}")
            self.stdout.write(f"  Exempt methods: {', '.join(config['exempt_methods'])}")
            self.stdout.write(f"  Apply before tax: {config['apply_before_tax']}")
        else:
            # Merge new keys without overwriting existing config
            existing = setting.config or {}
            for key, val in config.items():
                if key not in existing:
                    existing[key] = val
            setting.config = existing
            setting.save(update_fields=['config'])
            enabled = existing.get('enabled', False)
            self.stdout.write(self.style.SUCCESS(
                f"Updated dual_pricing Setting #{setting.id} (merged new keys, enabled={enabled})"
            ))
