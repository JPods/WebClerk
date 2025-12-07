import json
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models
from datetime import datetime
# Usage: python manage.py draft_fields app_label.model_name


class Command(BaseCommand):
    help = 'Output JSON with field names as keys and example values as values for a given model'

    def add_arguments(self, parser):
        parser.add_argument('model', help='app_label.model_name')

    def handle(self, *args, **options):
        try:
            app_label, model_name = options['model'].split('.')
            model = apps.get_model(app_label, model_name)
        except ValueError:
            self.stderr.write('Invalid model format. Use app_label.model_name')
            return
        except LookupError:
            self.stderr.write(f'Model {options["model"]} not found')
            return

        data = {}
        for field in model._meta.fields:
            example = self.get_example_value(field)
            data[field.name] = example
        self.stdout.write(json.dumps(data, indent=4))

    def get_example_value(self, field):
        # If field has a default and it's callable, try to call it
        if hasattr(field, 'default') and field.default != models.NOT_PROVIDED:
            if callable(field.default):
                try:
                    return field.default()
                except Exception:
                    pass
            else:
                return field.default

        # Fallback based on field type
        if isinstance(field, models.CharField):
            return "example"
        elif isinstance(field, models.TextField):
            return "example text"
        elif isinstance(field, models.IntegerField):
            return 1
        elif isinstance(field, models.DecimalField):
            return 1.0
        elif isinstance(field, models.BooleanField):
            return True
        elif isinstance(field, models.DateTimeField):
            return datetime.now().isoformat()
        elif isinstance(field, models.DateField):
            return datetime.now().date().isoformat()
        elif isinstance(field, models.JSONField):
            return {}
        elif isinstance(field, models.ForeignKey):
            return None  # or 1, but None is safer
        elif isinstance(field, models.OneToOneField):
            return None
        else:
            return "example"