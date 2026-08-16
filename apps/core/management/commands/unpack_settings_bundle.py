"""Unpack a settings bundle into the database.

Imports Setting records from settings-bundle.json. UUID controls merge:
existing records updated, missing records created.

Usage:
    python manage.py unpack_settings_bundle                          # from settings-bundle.json
    python manage.py unpack_settings_bundle --input /tmp/sb.json     # custom path
    python manage.py unpack_settings_bundle --dry-run                # show what would change
    python manage.py unpack_settings_bundle --validate               # unpack + run health check
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import Settings from a canonical bundle (git snapshot → DB)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input', type=str, default='settings-bundle.json',
            help='Input file path (default: settings-bundle.json in project root)',
        )
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without writing')
        parser.add_argument('--validate', action='store_true', help='Run health check after unpacking')

    def handle(self, *args, **options):
        input_path = Path(options['input'])
        if not input_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {input_path}"))
            return

        with open(input_path) as f:
            bundle = json.load(f)

        records = bundle.get('settings', [])
        self.stdout.write(f"\nBundle: {len(records)} records from {bundle.get('source', '?')}")
        self.stdout.write(f"Exported: {bundle.get('dt_exported', '?')}")

        if options['dry_run']:
            from apps.core.models.setting import Setting
            would_create = 0
            would_update = 0
            for rec in records:
                uuid_val = rec.get('uuid')
                if not uuid_val:
                    continue
                if Setting.objects.filter(uuid=uuid_val).exists():
                    would_update += 1
                else:
                    would_create += 1
            self.stdout.write(f"\nDry run: {would_create} would be created, {would_update} would be updated")
            return

        from apps.core.services.settings_bootstrap import import_settings_bundle
        result = import_settings_bundle(bundle)

        self.stdout.write(f"\nCreated: {result['created']}")
        self.stdout.write(f"Updated: {result['updated']}")
        if result['errors']:
            for e in result['errors']:
                self.stderr.write(self.style.ERROR(f"  ERROR: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS('No errors.'))

        if options['validate']:
            from apps.core.services.settings_health import check_settings_health
            report = check_settings_health()
            if report['healthy']:
                self.stdout.write(self.style.SUCCESS(f"Health check: PASSED ({report['summary']})"))
            else:
                self.stdout.write(self.style.ERROR(f"Health check: FAILED ({report['summary']})"))
