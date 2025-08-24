import json
from django.core.management.base import BaseCommand
from django.apps import apps
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Delete all data except contact superusers and import demo data from JSON"

    def handle(self, *args, **kwargs):
        filename = 'all_tables_export.json'  # Change as needed
        self.delete_all_data_except_superusers()
        self.import_all_data(filename)

    def delete_all_data_except_superusers(self):
        """Delete all data except contact superusers."""
        User = get_user_model()
        # Delete all users except superusers
        User.objects.filter(is_superuser=False).delete()
        # Delete all other models
        for model in apps.get_models():
            if model == User:
                continue
            model.objects.all().delete()
        self.stdout.write("Deleted all data except contact superusers.")

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