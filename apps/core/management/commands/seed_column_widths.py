"""
seed_column_widths — Alice's recommended column widths by field type and name.

Creates a Setting record (purpose='alice_coaching', parent_model='column_widths')
with recommended pixel widths. Alice adjusts these over time as she sees what
users actually choose.

Usage:
    ./bin/python manage.py seed_column_widths
    ./bin/python manage.py seed_column_widths --force
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


# Recommended widths by exact field name (highest priority)
BY_NAME = {
    'id': 60,
    'ida': 100,
    'uuid': 220,
    'display_name': 200,
    'name': 180,
    'description': 250,
    'email': 180,
    'phone': 120,
    'address_full': 250,
    'full': 250,
    'attention': 150,
    'company': 180,
    'status': 90,
    'org_type': 90,
    'price_level': 100,
    'terms': 80,
    'priority': 70,
    'kanban_column': 100,
    'percent_complete': 80,
    'total': 100,
    'balance': 100,
    'amount': 100,
    'sku': 100,
    'kind': 80,
    'uom': 60,
    'code': 80,
    'type': 80,
    'category': 100,
    'purpose': 100,
    'role': 80,
    'sequence': 60,
    'line_number': 70,
    'division': 70,
    'used_for': 100,
    'debit': 100,
    'credit': 100,
    'source': 80,
    'source_model': 100,
    'model_name': 120,
    'record_id': 70,
    'parent_model': 120,
    'parent_id': 70,
    'parent_ida': 100,
    'child_ida': 100,
    'child_description': 200,
    'quantity': 70,
    'scrap_factor': 80,
    'yield_pct': 70,
    'revision': 70,
    'serial_ida': 120,
    'model_ida': 100,
    'qr_code': 120,
    'tax_jurisdiction': 150,
    'tax_rate_sales': 80,
    'tax_rate_cost': 80,
    'service_provider': 120,
    'days_due': 70,
    'discount_rate': 80,
    'name_first': 100,
    'name_last': 100,
    'title': 120,
    'department': 100,
    'reference_number': 120,
    'gateway': 80,
    'reconciled': 70,
    'fee_amount': 80,
    'is_active': 60,
    'is_primary': 60,
    'is_verified': 60,
    'opt_out': 60,
    'confidential': 80,
    'mime_type': 80,
    'size_bytes': 70,
    'count_accessed': 70,
    'question': 250,
    'answer': 250,
    'path': 200,
    'slug': 150,
    'comment': 200,
    'notes': 200,
    'dt_created': 130,
    'dt_modified': 130,
    'dt_payment': 130,
    'dt_due': 130,
    'dt_deadline': 130,
    'dt_start': 130,
    'dt_completed': 130,
    'version': 55,
    'number': 110,
    'country_code': 50,
    'format': 120,
    'address1': 200,
    'city': 100,
    'state': 60,
    'zip': 70,
    'country': 80,
    'address_type': 80,
    'latitude': 90,
    'longitude': 90,
}

# Recommended widths by field behavior type (fallback)
BY_TYPE = {
    'readonly': 80,
    'email': 180,
    'phone': 120,
    'address': 250,
    'geo': 90,
    'url': 200,
    'select': 100,
    'lookup': 100,
    'currency': 100,
    'boolean': 60,
    'json': 200,
    'textarea': 250,
    'timestamp': 130,
    'date': 110,
    'number': 80,
    'text': 140,
}

# Recommended widths by Django field class (lowest priority fallback)
BY_DJANGO_TYPE = {
    'AutoField': 60,
    'BigAutoField': 60,
    'SmallAutoField': 60,
    'CharField': 140,
    'TextField': 250,
    'EmailField': 180,
    'URLField': 200,
    'SlugField': 150,
    'IntegerField': 70,
    'BigIntegerField': 80,
    'SmallIntegerField': 60,
    'PositiveIntegerField': 70,
    'PositiveSmallIntegerField': 60,
    'FloatField': 80,
    'DecimalField': 100,
    'BooleanField': 60,
    'NullBooleanField': 60,
    'DateField': 100,
    'DateTimeField': 130,
    'TimeField': 80,
    'UUIDField': 220,
    'JSONField': 200,
    'ForeignKey': 100,
    'OneToOneField': 100,
    'GenericIPAddressField': 120,
    'FileField': 180,
    'ImageField': 180,
    'BinaryField': 80,
    'SearchVectorField': 0,  # never show
}

# Recommended by common name patterns (regex-like prefix/suffix matching)
BY_PATTERN = {
    'dt_': 130,         # any timestamp field
    'is_': 60,          # any boolean flag
    'has_': 60,         # any boolean flag
    'count_': 70,       # counters
    '_id': 70,          # FK integer IDs
    '_ida': 100,        # soft IDs
    '_name': 150,       # name fields
    '_email': 180,      # email fields
    '_phone': 120,      # phone fields
    '_address': 200,    # address fields
    '_date': 110,       # date fields
    '_amount': 100,     # money fields
    '_total': 100,      # total fields
    '_rate': 80,        # rate/percentage fields
    '_qty': 70,         # quantity fields
    '_pct': 70,         # percentage fields
    '_code': 80,        # code fields
    '_type': 80,        # type discriminators
    '_status': 90,      # status fields
}

# Default if nothing matches
DEFAULT_WIDTH = 120


class Command(BaseCommand):
    help = 'Seed Alice recommended column widths Setting'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        data = {
            'by_name': BY_NAME,
            'by_type': BY_TYPE,
            'by_django_type': BY_DJANGO_TYPE,
            'by_pattern': BY_PATTERN,
            'default': DEFAULT_WIDTH,
            'version': 1,
            'note': 'Alice adjusts these based on user behavior over time. Synced from WCHQ.',
        }

        existing = Setting.objects.filter(
            purpose='alice_coaching',
            name='column_widths',
        ).first()

        if existing and not options.get('force'):
            self.stdout.write('Column widths setting already exists (use --force)')
            return

        if existing:
            existing.config = data
            existing.save()
            self.stdout.write(self.style.SUCCESS(f'Updated: {len(BY_NAME)} by-name, {len(BY_TYPE)} by-type'))
        else:
            Setting.objects.create(
                name='column_widths',
                purpose='alice_coaching',
                parent_model='',
                config=data,
            )
            self.stdout.write(self.style.SUCCESS(f'Created: {len(BY_NAME)} by-name, {len(BY_TYPE)} by-type'))
