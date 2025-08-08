import json
from django.core.management.base import BaseCommand
from core.models import Setting  # Use your actual model name

class Command(BaseCommand):
    help = 'Load default_access.json into the settings table'

    def handle(self, *args, **kwargs):
        path = 'common/default_access.json'
        with open(path, 'r') as f:
            data = json.load(f)
        count = 0
        for entry in data:
            obj, created = Setting.objects.update_or_create(
                name=entry.get('name'),
                defaults={
                    'is_active': entry.get('is_active', True),
                    'purpose': entry.get('purpose', ''),
                    'role': entry.get('role', ''),
                    'table_name': entry.get('table_name', ''),
                    'data': entry.get('data', {}),
                    'comment': entry.get('comment', ''),
                }
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} settings from default_access.json'))