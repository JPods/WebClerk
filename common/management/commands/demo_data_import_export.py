# python manage.py demo_data_import_export export
# python manage.py demo_data_import_export import

import os      # Standard library for file and path operations
import json    # Standard library for working with JSON data
from django.core.management.base import BaseCommand  # Base class for Django management commands
from django.apps import apps  # Utility to access all registered Django models

class Command(BaseCommand):
    # Help text shown when you run 'python manage.py help demo_data_import_export'
    help = "Export or import all data from all tables as JSON. Usage: python manage.py demo_data_import_export [import|export]"

    def add_arguments(self, parser):
        # Adds a required argument 'action' (either 'export' or 'import') to the command
        parser.add_argument('action', choices=['export', 'import'], help="Choose 'export' or 'import'.")

    def handle(self, *args, **kwargs):
        # Main entry point for the command
        action = kwargs['action']  # Get the action argument ('export' or 'import')
        # Build the path to the JSON file in the same folder as this script
        filename = os.path.join(os.path.dirname(__file__), 'all_tables_export.json')

        if action == 'export':
            # If action is 'export', call the export function
            self.export_all_data(filename)
        elif action == 'import':
            # If action is 'import', first delete all data, then import from JSON
            self.delete_all_data()
            self.import_all_data(filename)

    def export_all_data(self, filename):
        """Export all fields from all tables to a JSON file."""
        # List of models to skip during export (system tables, celery tables, etc.)
        skip_models = [
            'core.Pending',
            'auth.Permission',
            'contenttypes.ContentType',
            'admin.LogEntry',
            'django_celery_beat.PeriodicTask',
            'django_celery_beat.CrontabSchedule',
            'django_celery_beat.IntervalSchedule',
            'django_celery_beat.ClockedSchedule',
            'django_celery_beat.SolarSchedule',
        ]
        all_data = {}  # Dictionary to hold all exported data
        for model in apps.get_models():  # Loop through all Django models
            model_name = f"{model._meta.app_label}.{model.__name__}"  # e.g., 'core.Contact'
            if model_name in skip_models:
                continue  # Skip models in the skip list
            self.stdout.write(f"Exporting table: {model_name}")  # Print which table is being exported
            # For each object in the model, create a dict of field values
            all_data[model_name] = [
                {field.name: getattr(obj, field.name) for field in model._meta.fields}
                for obj in model.objects.all()
            ]
        # Write the all_data dictionary to the JSON file
        with open(filename, 'w') as f:
            json.dump(all_data, f, default=str, indent=4)
        self.stdout.write(f"Export completed: {filename}")  # Print completion message

    def delete_all_data(self):
        """Delete all data from all tables."""
        # List of models to skip during deletion (system tables, celery tables, etc.)
        skip_models = [
            'core.Pending',
            'auth.Permission',
            'contenttypes.ContentType',
            'admin.LogEntry',
            'django_celery_beat.PeriodicTask',
            'django_celery_beat.CrontabSchedule',
            'django_celery_beat.IntervalSchedule',
            'django_celery_beat.ClockedSchedule',
            'django_celery_beat.SolarSchedule',
        ]
        for model in apps.get_models():  # Loop through all models
            model_name = f"{model._meta.app_label}.{model.__name__}"
            if model_name in skip_models:
                continue  # Skip models in the skip list
            model.objects.all().delete()  # Delete all records in each model

    def import_all_data(self, filename):
        """Import all fields into all tables from a JSON file."""
        # List of models to skip during import (system tables, celery tables, etc.)
        skip_models = [
            'core.Pending',
            'auth.Permission',
            'contenttypes.ContentType',
            'admin.LogEntry',
            'django_celery_beat.PeriodicTask',
            'django_celery_beat.CrontabSchedule',
            'django_celery_beat.IntervalSchedule',
            'django_celery_beat.ClockedSchedule',
            'django_celery_beat.SolarSchedule',
        ]
        # Open and load the JSON file
        with open(filename, 'r') as f:
            all_data = json.load(f)
        for model in apps.get_models():  # Loop through all models
            model_name = f"{model._meta.app_label}.{model.__name__}"
            if model_name in skip_models:
                continue  # Skip models in the skip list
            self.stdout.write(f"Importing table: {model_name}")  # Print which table is being imported
            objects = all_data.get(model_name, [])  # Get list of objects for this model
            for obj_data in objects:  # Loop through each object to import
                # Resolve ForeignKey fields to actual model instances
                for field in model._meta.fields:
                    if field.is_relation and field.many_to_one and field.name in obj_data:
                        rel_model = field.related_model
                        rel_value = obj_data[field.name]
                        if rel_value is not None:
                            try:
                                obj_data[field.name] = rel_model.objects.get(pk=rel_value)
                            except rel_model.DoesNotExist:
                                obj_data[field.name] = None
                # Always use update_or_create if PK is present
                pk_name = model._meta.pk.name if model._meta.pk else None
                pk_value = obj_data.get(pk_name) if pk_name else None
                if pk_name and pk_value is not None:
                    model.objects.update_or_create(
                        defaults=obj_data,
                        **{pk_name: pk_value}
                    )
                else:
                    model.objects.create(**obj_data)
        self.stdout.write(f"Import completed: {filename}")  # Print completion message