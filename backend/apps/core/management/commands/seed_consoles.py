"""seed_consoles — the flight simulator's consoles as wc:console Settings (apps/core/consoles.py).

Usage:
    python manage.py seed_consoles            # create the ones missing
    python manage.py seed_consoles --force    # rewrite every console's steps from the shipped set
"""
from django.core.management.base import BaseCommand

from apps.core.consoles import PURPOSE, console_settings
from apps.core.models.setting import Setting


class Command(BaseCommand):
    help = "Seed wc:console Settings — one per flight-simulator console, with its steps"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing consoles')

    def handle(self, *args, **options):
        force = options.get('force', False)
        made = updated = kept = 0
        for payload in console_settings():
            existing = Setting.objects.filter(purpose=PURPOSE, ida=payload['ida']).first()
            if existing and not force:
                kept += 1
                continue
            if existing:
                existing.name, existing.explanation, existing.config = payload['name'], payload['explanation'], payload['config']
                existing._setting_create_authorized = True
                existing.save()
                updated += 1
            else:
                obj = Setting(**payload, scope='system')
                obj._setting_create_authorized = True
                obj.save()
                made += 1
        self.stdout.write(self.style.SUCCESS(f'consoles: {made} made, {updated} updated, {kept} kept'))
