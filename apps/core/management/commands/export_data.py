"""
Export all model data to JSON files in the specified directory.
"""
import os
import json
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core import serializers


class Command(BaseCommand):
    help = "Export all model data to JSON files in /Users/williamjames/Documents/CommerceExpert/webclerk3_data"

    def handle(self, *args, **options):
        target_dir = "/Users/williamjames/Documents/CommerceExpert/webclerk3_data"

        # Ensure the target directory exists
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            self.stdout.write(f"Created directory: {target_dir}")

        # Get all models
        models = apps.get_models()

        for model in models:
            model_name = model.__name__.lower()
            filename = f"{model_name}.json"
            filepath = os.path.join(target_dir, filename)

            try:
                # Serialize all objects of the model to JSON
                data = serializers.serialize('json', model.objects.all(), indent=2)

                # Write to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(data)

                self.stdout.write(f"Exported {model._meta.label} to {filepath}")

            except Exception as e:
                self.stderr.write(f"Error exporting {model._meta.label}: {str(e)}")

        self.stdout.write(self.style.SUCCESS("Data export completed"))