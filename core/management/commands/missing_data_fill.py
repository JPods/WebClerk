from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models

def fill_empty_text_fields():
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            # Get all CharField and TextField names
            text_fields = [
                field.name for field in model._meta.fields
                if isinstance(field, (models.CharField, models.TextField))
            ]
            # Loop through all records
            for obj in model.objects.all():
                updated = False
                for field_name in text_fields:
                    field_obj = model._meta.get_field(field_name)
                    value = getattr(obj, field_name)
                    if not value:
                        fill_value = f"{field_name} ({obj.pk})"
                        if hasattr(field_obj, "max_length") and field_obj.max_length:
                            fill_value = fill_value[:field_obj.max_length]
                        setattr(obj, field_name, fill_value)
                        updated = True
                if updated:
                    obj.save()

class Command(BaseCommand):
    help = "Fill empty CharField and TextField values with field name and record id"

    def handle(self, *args, **options):
        fill_empty_text_fields()
        self.stdout.write(self.style.SUCCESS("Empty text fields filled."))