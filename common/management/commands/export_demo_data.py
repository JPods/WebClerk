# python manage.py export_demo_data
import json
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "Export and import all data from all tables as JSON"

    def handle(self, *args, **kwargs):
        # Example usage:
        # self.export_all_data('all_tables_export.json')
        # self.import_all_data('all_tables_export.json')
        pass

    def export_all_data(self, filename):
        """Export all fields from all tables to a JSON file."""
        all_data = {}
        for model in apps.get_models():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            all_data[model_name] = [
                {field.name: getattr(obj, field.name) for field in model._meta.fields}
                for obj in model.objects.all()
            ]
        with open(filename, 'w') as f:
            json.dump(all_data, f, default=str, indent=2)
        self.stdout.write(f"Exported all data to {filename}")

    def import_all_data(self, filename):
        """Import all fields from JSON file into all tables."""
        with open(filename, 'r') as f:
            all_data = json.load(f)
        for model_name, records in all_data.items():
            app_label, model_class = model_name.split('.')
            model = apps.get_model(app_label, model_class)
            for record in records:
                obj, created = model.objects.update_or_create(
                    id=record.get('id'),
                    defaults=record
                )
        self.stdout.write(f"Imported all data from {filename}")