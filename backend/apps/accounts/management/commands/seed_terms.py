"""
seed_terms — Seed standard payment terms.

Usage:
    python manage.py seed_terms
    python manage.py seed_terms --force   # delete and re-seed

Universal terms that any business needs. Company-specific terms
(e.g., "Due Dec 8") are not included — add those manually.
"""
from django.core.management.base import BaseCommand
from apps.accounts.models.term import Term


TERMS = [
    {'ida': 'COD',          'name': 'COD',          'description': 'Cash on Delivery',              'days_due': 0,  'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': 'DOR',          'name': 'DOR',          'description': 'Due on Receipt',                'days_due': 0,  'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': 'Prepaid',      'name': 'Prepaid',      'description': 'Payment in Advance',            'days_due': 0,  'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': 'N10',          'name': 'N10',          'description': 'Net 10 Days',                   'days_due': 10, 'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': 'N20',          'name': 'N20',          'description': 'Net 20 Days',                   'days_due': 20, 'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': 'N30',          'name': 'N30',          'description': 'Net 30 Days',                   'days_due': 30, 'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': 'N60',          'name': 'N60',          'description': 'Net 60 Days',                   'days_due': 60, 'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': 'N90',          'name': 'N90',          'description': 'Net 90 Days',                   'days_due': 90, 'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': '2pct10N30',    'name': '2pct10N30',    'description': '2% 10, Net 30 Days',            'days_due': 30, 'discount_rate': 2, 'days_discount': 10,'period_count': 1, 'days_in_period': 0},
    {'ida': 'Deposit50',    'name': 'Deposit50',    'description': '50% Deposit, Balance on Receipt','days_due': 0,  'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
    {'ida': '3Pay30Days',   'name': '3Pay30Days',   'description': '3 Payments Every 30 Days',      'days_due': 90, 'discount_rate': 0, 'days_discount': 0, 'period_count': 3, 'days_in_period': 30},
    {'ida': 'CreditCard',   'name': 'CreditCard',   'description': 'Credit Card Payment',           'days_due': 0,  'discount_rate': 0, 'days_discount': 0, 'period_count': 1, 'days_in_period': 0},
]


class Command(BaseCommand):
    help = 'Seed standard payment terms (12 terms)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Delete existing and re-seed')

    def handle(self, *args, **options):
        if options.get('force'):
            deleted, _ = Term.objects.exclude(ida__startswith='zz').delete()
            self.stdout.write(f'Deleted {deleted} existing terms')

        created = skipped = 0
        for t in TERMS:
            if Term.objects.filter(ida=t['ida']).exists():
                skipped += 1
                continue

            Term.objects.create(
                ida=t['ida'],
                name=t['name'],
                description=t.get('description', ''),
                days_due=t.get('days_due', 0),
                discount_rate=t.get('discount_rate', 0),
                days_discount=t.get('days_discount', 0),
                period_count=t.get('period_count', 1),
                days_in_period=t.get('days_in_period', 0),
                is_active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Terms: {created} created, {skipped} already exist'))
