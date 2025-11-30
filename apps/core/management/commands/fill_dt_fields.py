"""
Fill dt_<keyword> fields in JSONFields and BigIntegerFields with Unix timestamps.
"""
import json
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models
from django.utils import timezone
from common.models import BaseModel
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fill dt_<keyword> fields in all JSONFields of BaseModel instances with current Unix timestamp"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--apps',
            nargs='*',
            help='Specific apps to process (default: all)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_apps = options.get('apps')

        # Get all models that inherit from BaseModel
        all_models = []
        exclude_apps = {'contenttypes', 'auth', 'sessions', 'admin'}
        for app_config in apps.get_app_configs():
            if app_config.label in exclude_apps:
                continue
            if specific_apps and app_config.label not in specific_apps:
                continue
            for model in app_config.get_models():
                if issubclass(model, BaseModel) and not model._meta.abstract:
                    all_models.append(model)

        if dry_run:
            self.stdout.write(f"Would process {len(all_models)} models:")
            for model in all_models:
                count = model.objects.count()
                self.stdout.write(f"  - {model._meta.label}: {count} instances")
            return

        self.stdout.write(f"Processing {len(all_models)} models...")

        now_ms = int(timezone.now().timestamp() * 1000)

        for model in all_models:
            self.stdout.write(f"Processing {model._meta.label}...")
            json_fields = ['metadata', 'refs', 'prefs', 'comments', 'actions']

            # Get all instances (since we need to check BigIntegerFields too)
            instances = model.objects.all().iterator(chunk_size=1000)

            updated_count = 0
            for instance in instances:
                changed = False
                update_fields = []

                # Handle BigIntegerFields starting with 'dt_'
                for field in model._meta.get_fields():
                    if field.name.startswith('dt_') and isinstance(field, models.BigIntegerField):
                        current_value = getattr(instance, field.name)
                        if current_value is None or current_value == 0:
                            setattr(instance, field.name, now_ms)
                            changed = True
                            update_fields.append(field.name)

                # Handle JSONFields
                for field_name in json_fields:
                    if hasattr(instance, field_name):
                        field_value = getattr(instance, field_name)
                        if isinstance(field_value, dict):
                            new_value = self.fill_dt_fields_recursive(field_value, now_ms)
                            if new_value != field_value:
                                setattr(instance, field_name, new_value)
                                changed = True
                                update_fields.append(field_name)

                if changed:
                    update_fields.extend(['dt_modified', 'version'])
                    instance.save(update_fields=update_fields)
                    updated_count += 1
                    if updated_count % 100 == 0:
                        self.stdout.write(f"  Updated {updated_count} instances so far...")

            self.stdout.write(f"  Updated {updated_count} instances")

        self.stdout.write(self.style.SUCCESS("dt_ fields filling completed"))

    def fill_dt_fields_recursive(self, data, timestamp):
        """Recursively traverse dict and fill dt_ keys with timestamp if they are 0, None, or missing."""
        if not isinstance(data, dict):
            return data

        new_data = {}
        for key, value in data.items():
            if key.startswith('dt_'):
                # If it's a dt_ key, set to timestamp if 0 or None
                if value is None or value == 0:
                    new_data[key] = timestamp
                else:
                    new_data[key] = value
            elif isinstance(value, dict):
                new_data[key] = self.fill_dt_fields_recursive(value, timestamp)
            elif isinstance(value, list):
                new_data[key] = [self.fill_dt_fields_recursive(item, timestamp) if isinstance(item, dict) else item for item in value]
            else:
                new_data[key] = value

        return new_data