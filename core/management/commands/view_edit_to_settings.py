# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/management/commands/view_edit_to_settings.py
import json
"""
Django management command to load default access settings from a JSON file into the Setting model.

This command reads the 'common/default_access.json' file, parses its contents, and updates or creates
Setting objects in the database for each entry found in the JSON. Each entry should contain the fields:
'name', 'is_active', 'purpose', 'role', 'table_name', 'data', and 'comment'. If a field is missing,
a default value is used.

Attributes:
    help (str): Description of the command for Django's help system.

Methods:
    handle(*args, **kwargs): Main entry point for the command. Loads the JSON file, processes each entry,
    and updates or creates Setting objects accordingly. Outputs the number of settings loaded upon success.
"""
from django.core.management.base import BaseCommand
from core.models import Setting  # Use your actual model name

# Load default access settings
class Command(BaseCommand):
    help = 'Load default_access.json into the settings table'

    def handle(self, *args, **kwargs):
        path = 'common/defaults/view_edit.json'
        with open(path, 'r') as f:
            data = json.load(f)
        count = 0
        for entry in data:
            table_name = entry.get('table_name')
            obj, created = Setting.objects.update_or_create(
                purpose="view_edit",
                table_name=table_name,
                defaults={
                    'name': table_name,
                    'role': 'all',
                    'is_active': True,
                    'data': entry.get('data', {}),
                    'comment': entry.get('comment', ''),
                }
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} settings from default_access.json'))