import json
import os
import uuid
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db.models import UUIDField


class Command(BaseCommand):
    help = 'Load demo data from JSON file into specified model'

    def add_arguments(self, parser):
        parser.add_argument(
            'model',
            help='Model name in app_label.model_name format (e.g., products.item)'
        )
        parser.add_argument(
            'json_file',
            help='Path to JSON file containing demo data'
        )
        parser.add_argument(
            '--drop',
            action='store_true',
            help='Delete all existing records before loading new data'
        )

    def handle(self, *args, **options):
        model_str = options['model']
        json_file = options['json_file']
        drop = options['drop']

        # Parse and validate model
        try:
            app_label, model_name = model_str.split('.')
            model = apps.get_model(app_label, model_name)
        except ValueError:
            raise CommandError(
                f"Invalid model format: {model_str}. Use 'app_label.model_name'"
            )
        except LookupError:
            raise CommandError(f"Model '{model_str}' not found")

        # Get valid model fields
        valid_fields = {f.name for f in model._meta.fields}
        uuid_fields = [f.name for f in model._meta.fields if isinstance(f, UUIDField)]

        # Validate JSON file exists
        if not os.path.exists(json_file):
            raise CommandError(f"JSON file not found: {json_file}")

        # Load and validate JSON
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON file: {e}")
        except IOError as e:
            raise CommandError(f"Error reading JSON file: {e}")

        # Validate JSON structure
        if not isinstance(data, list):
            raise CommandError("JSON file must contain an array of objects")

        # Optionally drop existing records
        if drop:
            deleted_count, _ = model.objects.all().delete()
            self.stdout.write(
                f"Deleted {deleted_count} existing records from {model_str}"
            )

        # Create records from JSON data
        created_count = 0
        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                raise CommandError(
                    f"Item {i} is not a dictionary object"
                )

            # Check and replace invalid UUIDs in UUIDField fields
            for key in item:
                if key in uuid_fields:
                    if isinstance(item[key], str):
                        try:
                            uuid.UUID(item[key])
                        except ValueError:
                            item[key] = str(uuid.uuid4())

            filtered_item = {k: v for k, v in item.items() if k in valid_fields}
            try:
                obj = model(**filtered_item)
                obj.save()
                created_count += 1
                self.stdout.write(
                    f"Created {model_str} instance {created_count} of {len(data)}"
                )
            except ValidationError as ve:
                # Handle UUID validation errors by identifying invalid fields and replacing
                if hasattr(ve, 'message_dict'):
                    for field, messages in ve.message_dict.items():
                        if field in uuid_fields and any('uuid' in ' '.join(messages).lower()):
                            filtered_item[field] = str(uuid.uuid4())
                # Retry creation with corrected UUIDs
                obj = model(**filtered_item)
                obj.save()
                created_count += 1
                self.stdout.write(
                    f"Created {model_str} instance {created_count} of {len(data)}"
                )
            except Exception as e:
                raise CommandError(
                    f"Error creating instance {i}: {e}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully loaded {created_count} records into {model_str}"
            )
        )