"""
seed_tax_jurisdictions — Seed US state sales tax rates.

Usage:
    python manage.py seed_tax_jurisdictions
    python manage.py seed_tax_jurisdictions --force   # overwrite existing rates

Creates TaxJurisdiction records for all 50 US states + DC.
Rates are general state-level rates as of 2026. Local/city rates vary.
Idempotent: skips states that already exist unless --force.
"""
from django.core.management.base import BaseCommand
from apps.accounts.models.tax_jurisdiction import TaxJurisdiction


# US state sales tax rates (general state-level, 2026)
# States with 0.0 have no state sales tax.
# Local jurisdictions (city/county) are NOT included — users add those.
US_STATES = [
    ('AL', 'Alabama',              0.04,   True),
    ('AK', 'Alaska',               0.0,    False),
    ('AZ', 'Arizona',              0.056,  False),
    ('AR', 'Arkansas',             0.065,  True),
    ('CA', 'California',           0.0725, False),
    ('CO', 'Colorado',             0.029,  False),
    ('CT', 'Connecticut',          0.0635, True),
    ('DE', 'Delaware',             0.0,    False),
    ('FL', 'Florida',              0.06,   False),
    ('GA', 'Georgia',              0.04,   True),
    ('HI', 'Hawaii',               0.04,   True),
    ('ID', 'Idaho',                0.06,   False),
    ('IL', 'Illinois',             0.0625, False),
    ('IN', 'Indiana',              0.07,   False),
    ('IA', 'Iowa',                 0.06,   False),
    ('KS', 'Kansas',               0.065,  True),
    ('KY', 'Kentucky',             0.06,   False),
    ('LA', 'Louisiana',            0.0445, False),
    ('ME', 'Maine',                0.055,  False),
    ('MD', 'Maryland',             0.06,   False),
    ('MA', 'Massachusetts',        0.0625, False),
    ('MI', 'Michigan',             0.06,   False),
    ('MN', 'Minnesota',            0.06875,True),
    ('MS', 'Mississippi',          0.07,   True),
    ('MO', 'Missouri',             0.04225,False),
    ('MT', 'Montana',              0.0,    False),
    ('NE', 'Nebraska',             0.055,  True),
    ('NV', 'Nevada',               0.0685, False),
    ('NH', 'New Hampshire',        0.0,    False),
    ('NJ', 'New Jersey',           0.06625,True),
    ('NM', 'New Mexico',           0.05125,True),
    ('NY', 'New York',             0.04,   True),
    ('NC', 'North Carolina',       0.0475, True),
    ('ND', 'North Dakota',         0.05,   True),
    ('OH', 'Ohio',                 0.0575, True),
    ('OK', 'Oklahoma',             0.045,  False),
    ('OR', 'Oregon',               0.0,    False),
    ('PA', 'Pennsylvania',         0.06,   True),
    ('RI', 'Rhode Island',         0.07,   False),
    ('SC', 'South Carolina',       0.06,   False),
    ('SD', 'South Dakota',         0.042,  True),
    ('TN', 'Tennessee',            0.07,   True),
    ('TX', 'Texas',                0.0625, True),
    ('UT', 'Utah',                 0.0485, True),
    ('VT', 'Vermont',              0.06,   True),
    ('VA', 'Virginia',             0.043,  False),
    ('WA', 'Washington',           0.065,  True),
    ('WV', 'West Virginia',        0.06,   True),
    ('WI', 'Wisconsin',            0.05,   True),
    ('WY', 'Wyoming',              0.04,   False),
    ('DC', 'District of Columbia', 0.06,   True),
]


class Command(BaseCommand):
    help = 'Seed US state sales tax jurisdictions'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing jurisdiction rates')

    def handle(self, *args, **options):
        force = options['force']
        created = 0
        updated = 0
        skipped = 0

        for code, name, rate, tax_shipping in US_STATES:
            jurisdiction_id = f'US_{code}'
            tax_name = f'{name} Sales Tax' if rate > 0 else f'{name} (No Sales Tax)'

            existing = TaxJurisdiction.objects.filter(
                tax_jurisdiction=jurisdiction_id
            ).first()

            if existing and not force:
                skipped += 1
                continue

            if existing and force:
                existing.tax_name = tax_name
                existing.tax_rate_sales = rate
                existing.tax_rate_cost = 0.0
                existing.tax_rate_on_shipping = rate if tax_shipping else 0.0
                existing.is_active = rate > 0
                existing.save(update_fields=[
                    'tax_name', 'tax_rate_sales', 'tax_rate_cost',
                    'tax_rate_on_shipping', 'is_active',
                ])
                updated += 1
            else:
                TaxJurisdiction.objects.create(
                    tax_jurisdiction=jurisdiction_id,
                    tax_name=tax_name,
                    tax_rate_sales=rate,
                    tax_rate_cost=0.0,
                    tax_rate_on_shipping=rate if tax_shipping else 0.0,
                    is_active=rate > 0,
                    gl_account_payable='2100-SalesTaxPayable',
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Tax jurisdictions: {created} created, {updated} updated, {skipped} skipped'
        ))
