import json
from django.core.management.base import BaseCommand
from core.models import Setting  # Adjust import as needed

def deep_update(target, source):
    """Recursively update target dict with source dict."""
    for k, v in source.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            deep_update(target[k], v)
        else:
            target[k] = v
    return target

class Command(BaseCommand):
    help = 'Load settings from view_edit_to_settings.py JSON file into the Setting table'

    def handle(self, *args, **options):
        path = 'core/management/commands/setup_base_data.json'  # <-- Hardcoded path
        with open(path, 'r') as f:
            data = json.load(f)
        count = 0
        for entry in data:
            # Get or create the record
            obj, created = Setting.objects.update_or_create(
                table_name=entry.get('table_name', ''),
                purpose=entry.get('purpose', ''),
                name=entry.get('name', ''),
                defaults={}
            )
            # Loop through fields and update, including nested dicts
            for field, value in entry.items():
                if field in ['table_name', 'purpose', 'name']:
                    continue
                current = getattr(obj, field, None)
                if isinstance(value, dict) and isinstance(current, dict):
                    setattr(obj, field, deep_update(current, value))
                else:
                    setattr(obj, field, value)
            obj.save()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} settings from {path}'))

