# python manage.py demo_data_import_export export
# python manage.py demo_data_import_export import
import os
import json
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "Export or import all data from all tables as JSON. Usage: python manage.py demo_data_import_export [import|export]"

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['export', 'import'], help="Choose 'export' or 'import'.")

    def handle(self, *args, **kwargs):
        action = kwargs['action']
        # Save/load file in the same folder as this script
        filename = os.path.join(os.path.dirname(__file__), 'all_tables_export.json')

        if action == 'export':
            self.export_all_data(filename)
        elif action == 'import':
            self.delete_all_data()
            self.import_all_data(filename)

    def export_all_data(self, filename):
        """Export all fields from all tables to a JSON file."""
        all_data = {}
        for model in apps.get_models():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            self.stdout.write(f"Exporting table: {model_name}")
            all_data[model_name] = [
                {field.name: getattr(obj, field.name) for field in model._meta.fields}
                for obj in model.objects.all()
            ]
        with open(filename, 'w') as f:
            json.dump(all_data, f, default=str, indent=4)
        self.stdout.write(f"Export completed: {filename}")

    def delete_all_data(self):
        """Delete all data from all tables."""
        for model in apps.get_models():
            model.objects.all().delete()

    def import_all_data(self, filename):
        """Import all fields into all tables from a JSON file."""
        skip_models = [
            'auth.Permission',
            'contenttypes.ContentType',
            'admin.LogEntry',
            'django_celery_beat.PeriodicTask',
            'django_celery_beat.CrontabSchedule',
            'django_celery_beat.IntervalSchedule',
            'django_celery_beat.ClockedSchedule',
            'django_celery_beat.SolarSchedule',
        ]
        with open(filename, 'r') as f:
            all_data = json.load(f)
        for model in apps.get_models():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            if model_name in skip_models:
                continue
            self.stdout.write(f"Importing table: {model_name}")
            objects = all_data.get(model_name, [])
            for obj_data in objects:
                for field in model._meta.fields:
                    if field.is_relation and field.many_to_one and field.name in obj_data:
                        rel_model = field.related_model
                        rel_value = obj_data[field.name]
                        if rel_value is not None:
                            try:
                                obj_data[field.name] = rel_model.objects.get(pk=rel_value)
                            except rel_model.DoesNotExist:
                                obj_data[field.name] = None
                pk_name = model._meta.pk.name
                pk_value = obj_data.get(pk_name)
                if pk_value is not None:
                    model.objects.update_or_create(
                        defaults=obj_data,
                        **{pk_name: pk_value}
                    )
                else:
                    model.objects.create(**obj_data)
        self.stdout.write(f"Import completed: {filename}")