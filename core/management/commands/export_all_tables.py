import json
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "Export all fields from all database tables to a single JSON file"

    def handle(self, *args, **kwargs):
        all_data = {}
        # Loop through all installed models
        for model in apps.get_models():
            model_name = f"{model._meta.app_label}.{model.__name__}"
            all_data[model_name] = []
            for obj in model.objects.all():
                # Use model_to_dict for all fields
                fields = {}
                for field in model._meta.get_fields():
                    if hasattr(obj, field.name):
                        value = getattr(obj, field.name)
                        # Convert UUIDs and other non-serializable types to string
                        if value is not None and not isinstance(value, (str, int, float, bool, dict, list)):
                            value = str(value)
                        fields[field.name] = value
                all_data[model_name].append(fields)
        # Write to JSON file
        with open("all_tables_export.json", "w") as f:
            json.dump(all_data, f, indent=2)
        self.stdout.write(self.style.SUCCESS("Exported all tables to all_tables_export.json"))