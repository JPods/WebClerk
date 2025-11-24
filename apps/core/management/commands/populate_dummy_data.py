"""
Populate all models with dummy data.
"""
import random
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
from faker import Faker
from common.models import default_metadata, default_refs, default_prefs, default_comments
from apps.core.constants.model_registry import VALID_MODEL_NAMES
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate all models with realistic dummy data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of dummy records per model (default: 5)'
        )
        parser.add_argument(
            '--reset-sequences',
            action='store_true',
            help='Reset auto increment sequences to 1'
        )
        parser.add_argument(
            '--apps',
            nargs='*',
            help='Specific apps to populate (default: all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        count = options['count']
        reset_sequences = options['reset_sequences']
        specific_apps = options.get('apps')
        dry_run = options['dry_run']

        fake = Faker()

        # Global unique trackers
        self.global_used_values = {}
        self.used_emails = set()

        # Get all models
        all_models = []
        exclude_apps = {'contenttypes', 'auth', 'sessions', 'admin'}
        for app_config in apps.get_app_configs():
            if app_config.label in exclude_apps:
                continue
            if specific_apps and app_config.label not in specific_apps:
                continue
            for model in app_config.get_models():
                if model._meta.abstract or model._meta.proxy:
                    continue
                all_models.append(model)

        if dry_run:
            self.stdout.write(f"Would process {len(all_models)} models:")
            for model in all_models:
                self.stdout.write(f"  - {model._meta.label}")
            return

        self.stdout.write(f"Processing {len(all_models)} models...")

        # Sort models by dependencies (simple heuristic: models with fewer FKs first)
        def sort_key(model):
            fks = sum(1 for f in model._meta.get_fields() if f.many_to_one)
            return fks

        all_models.sort(key=sort_key)

        for model in all_models:
            self.stdout.write(f"Processing {model._meta.label}...")

            # Delete existing data
            deleted_count = model.objects.all().delete()[0]
            if deleted_count > 0:
                self.stdout.write(f"  Deleted {deleted_count} existing records")

            # Reset sequence
            if reset_sequences:
                self.reset_sequence(model)

            # Track used values for unique fields
            used_values = {}

            # Generate dummy data
            for i in range(count):
                try:
                    obj = self.create_dummy_instance(model, fake, used_values)
                    if obj:
                        obj.save()
                        self.stdout.write(f"  Created record {i+1}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  Failed to create record {i+1}: {e}"))

        self.stdout.write(self.style.SUCCESS("Dummy data population completed"))

    def reset_sequence(self, model):
        """Reset auto increment sequence for the model."""
        table_name = model._meta.db_table
        with connection.cursor() as cursor:
            # PostgreSQL specific
            sequence_name = f"{table_name}_id_seq"
            try:
                cursor.execute(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")
                self.stdout.write(f"  Reset sequence {sequence_name}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Could not reset sequence: {e}"))

    def create_dummy_instance(self, model, fake, used_values=None):
        """Create a dummy instance of the model."""
        if used_values is None:
            used_values = {}
        data = {}

        for field in model._meta.get_fields():
            if field.name in ['id', 'uuid', 'dt_created', 'dt_modified', 'version', 'is_active', 'is_deleted', 'is_archived']:
                continue  # Skip auto fields

            # Skip reverse relations
            if field.is_relation and not field.many_to_one and not field.one_to_one:
                continue

            if field.many_to_one:  # Foreign key
                related_model = field.related_model
                if field.null:
                    # Set to None for nullable FKs
                    data[field_name] = None
                else:
                    # Try to create a dummy related object
                    try:
                        related_obj = self.create_dummy_related_object(related_model, fake)
                        if related_obj:
                            related_obj.save()
                            data[field_name] = related_obj
                        else:
                            # Skip this record if can't create related
                            return None
                    except Exception:
                        # Skip this record
                        return None
                continue

            if field.many_to_many:
                continue

            field_name = field.name
            field_type = type(field).__name__

            # Skip if already set or auto
            if field_name in data or getattr(field, 'primary_key', False) or getattr(field, 'auto_created', False):
                continue

            # Generate value
            value = None

            if field_type == 'CharField':
                max_length = getattr(field, 'max_length', 100)
                if field_name == 'model_name' and model._meta.label == 'core.Setting':
                    value = random.choice(VALID_MODEL_NAMES)
                elif field_name == 'email' and model._meta.label == 'core.Contact':
                    # Generate unique email
                    while True:
                        value = fake.email()
                        if value not in self.used_emails:
                            self.used_emails.add(value)
                            break
                elif 'email' in field_name.lower():
                    value = fake.email()
                elif 'phone' in field_name.lower() or 'number' in field_name.lower():
                    value = fake.phone_number()[:max_length]
                elif 'name' in field_name.lower():
                    value = fake.name()[:max_length]
                elif 'address' in field_name.lower():
                    value = fake.address().replace('\n', ', ')[:max_length]
                elif 'city' in field_name.lower():
                    value = fake.city()[:max_length]
                elif 'country' in field_name.lower():
                    value = fake.country()[:max_length]
                elif 'state' in field_name.lower():
                    value = fake.state()[:max_length]
                elif 'zip' in field_name.lower():
                    value = fake.zipcode()[:max_length]
                elif 'code' in field_name.lower():
                    value = fake.currency_code() if 'currency' in model._meta.label.lower() else fake.lexify(text='???')[:max_length]
                elif field_name == 'status' and model._meta.label == 'products.OrgItem':
                    value = 'active'
                elif field_name == 'movement_type' and model._meta.label == 'products.InventoryMovement':
                    value = 'issue'
                elif field_name == 'site' and model._meta.label == 'products.Serial':
                    value = fake.city()[:max_length]  # dummy site
                elif field.choices:
                    value = random.choice([choice[0] for choice in field.choices])
                else:
                    value = fake.text(max_nb_chars=max_length)[:max_length]

            elif field_type == 'TextField':
                value = fake.text()

            elif field_type == 'BooleanField':
                value = fake.boolean()

            elif field_type == 'IntegerField':
                if 'precision' in field_name.lower():
                    value = random.randint(0, 4)
                else:
                    value = fake.random_int(min=0, max=1000)

            elif field_type == 'FloatField':
                value = fake.latitude() if 'lat' in field_name.lower() else fake.longitude() if 'lon' in field_name.lower() else random.uniform(0, 100)

            elif field_type == 'DecimalField':
                max_digits = getattr(field, 'max_digits', 10)
                decimal_places = getattr(field, 'decimal_places', 2)
                max_value = 10 ** (max_digits - decimal_places) - 1 / (10 ** decimal_places)
                value = fake.pydecimal(left_digits=max_digits - decimal_places, right_digits=decimal_places, positive=True, max_value=max_value)

            elif field_type == 'DateTimeField':
                from django.utils import timezone
                value = timezone.make_aware(fake.date_time_this_year())

            elif field_type == 'DateField':
                value = fake.date_this_year()

            elif field_type == 'BigIntegerField':
                if field.null and random.choice([True, False]):  # randomly set to None for nullable fields
                    value = None
                elif 'dt_' in field_name:
                    if field_name == 'dt_effective_end' and model._meta.label == 'products.Catalog':
                        # For Catalog, ensure end >= start
                        start_value = data.get('dt_effective_start')
                        if start_value:
                            value = start_value + fake.random_int(min=0, max=365*24*60*60*1000)  # up to 1 year later
                        else:
                            value = int(fake.date_time_this_year().timestamp() * 1000)
                    else:
                        value = int(fake.date_time_this_year().timestamp() * 1000)
                elif field_name == 'year' and model._meta.label == 'products.ItemUsage':
                    value = fake.year()
                else:
                    value = fake.random_int(min=0, max=1000000)

            elif field_type == 'JSONField':
                if field_name == 'metadata':
                    value = default_metadata()
                elif field_name == 'refs':
                    value = default_refs()
                elif field_name == 'prefs':
                    value = default_prefs()
                elif field_name == 'comments':
                    value = default_comments()
                elif field_name == 'actions':
                    value = {}
                else:
                    value = {}

            else:
                # Skip unknown field types
                continue

            # Ensure unique if needed
            if field.unique and value is not None:
                while value in used_values.get(field_name, set()):
                    # Regenerate
                    if field_type == 'CharField':
                        max_length = getattr(field, 'max_length', 100)
                        if 'email' in field_name.lower():
                            value = fake.email()
                        else:
                            value = fake.text(max_nb_chars=max_length)[:max_length]
                used_values.setdefault(field_name, set()).add(value)

            if value is not None:
                data[field_name] = value

        # Ensure BaseModel defaults
        if hasattr(model, 'health_rating') and 'health_rating' not in data:
            data['health_rating'] = 0

        return model(**data)

    def create_dummy_related_object(self, model, fake):
        """Create a dummy instance for related model, used for FKs."""
        return self.create_dummy_instance(model, fake, {})