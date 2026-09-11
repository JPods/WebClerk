"""Seed the financial schedules Setting record.

Defines the system — what schedule types exist, their GL account mappings,
default frequencies, and structure. This is the menu.

Actual schedule data arrives via Connection/Bundle imports with full audit trail.
The forecast engine reads the Setting for structure, then pulls the most recent
successful Bundle for each schedule type to get current amounts.

Connection type='manual', one Connection per schedule type:
  - "Payroll Schedule" → bundles carry payroll entries
  - "Property Schedule" → bundles carry property/lease entries
  - "Depreciation Schedule" → bundles carry depreciation entries

Usage: ./manage.py seed_financial_schedules
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


FINANCIAL_SCHEDULES_CONFIG = {
    "schedule_types": {
        "payroll": {
            "label": "Payroll",
            "default_frequency": "biweekly",
            "gl_accounts": ["6100-SALARY", "6110-WAGES", "6120-BENEFITS", "6130-PAYROLL-TAX"],
            "connection_name": "Payroll Schedule",
        },
        "property": {
            "label": "Property & Facilities",
            "default_frequency": "monthly",
            "gl_accounts": ["6300-RENT", "6310-INSURANCE", "6320-UTILITIES", "6330-MAINTENANCE"],
            "connection_name": "Property Schedule",
        },
        "depreciation": {
            "label": "Depreciation",
            "default_frequency": "monthly",
            "gl_accounts": ["1500-EQUIPMENT", "6500-DEPRECIATION"],
            "connection_name": "Depreciation Schedule",
            "links_to": "purchase.is_capital",
        },
    },
    "entry_schema": {
        "account": "GL account ida (required)",
        "amount": "Monthly amount (required)",
        "frequency": "weekly|biweekly|semimonthly|monthly|quarterly|annual",
        "description": "Line description",
        "purchase_id": "Link to capital Purchase (depreciation only)",
    },
}


class Command(BaseCommand):
    help = 'Seed the financial schedules Setting record and Connection records'

    def handle(self, *args, **options):
        # Seed the Setting (system definition)
        obj, created = Setting.objects.update_or_create(
            purpose='wc:financial_schedules',
            parent_model='setting',
            defaults={
                'ida': 'financial_schedules',
                'name': 'Financial Schedules',
                'config': FINANCIAL_SCHEDULES_CONFIG,
            },
        )
        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{verb} financial_schedules Setting (id={obj.id})'))

        # Seed Connection records for each schedule type
        from apps.sync.models.connection import Connection

        for key, stype in FINANCIAL_SCHEDULES_CONFIG['schedule_types'].items():
            conn, c = Connection.objects.update_or_create(
                name=stype['connection_name'],
                defaults={
                    'type': 'manual',
                    'status': 'active',
                    'ida': f'schedule-{key}',
                    'config': {
                        'schedule_type': key,
                        'default_frequency': stype['default_frequency'],
                        'gl_accounts': stype['gl_accounts'],
                    },
                },
            )
            v = 'Created' if c else 'Updated'
            self.stdout.write(f'  {v} Connection "{stype["connection_name"]}" (id={conn.id})')
