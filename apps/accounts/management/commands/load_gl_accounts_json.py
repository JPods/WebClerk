import json
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Load GL accounts from a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Path to the JSON file with GL accounts.')

    def handle(self, *args, **options):
        json_path = options['json_path']
        with open(json_path, 'r') as f:
            data = json.load(f)
        from django.apps import apps
        GlAccount = apps.get_model('accounts', 'GlAccount')
        objs = [GlAccount(**item) for item in data]
        GlAccount.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(objs)} GL accounts from {json_path}'))
