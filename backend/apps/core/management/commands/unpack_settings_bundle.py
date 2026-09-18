"""Unpack a settings bundle into the database.

Imports Setting records from settings-bundle.json. UUID controls merge:
existing records updated (baseline merge), missing records created.

WALL: Settings are protected. This command is one of the approved paths
through the wall. --replace requires double confirmation because it
overwrites existing config (normally baseline merge only adds missing keys).

Usage:
    python manage.py unpack_settings_bundle                          # baseline merge
    python manage.py unpack_settings_bundle --input /tmp/sb.json     # custom path
    python manage.py unpack_settings_bundle --dry-run                # show what would change
    python manage.py unpack_settings_bundle --replace                # FULL REPLACE (double confirm)
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
        parser.add_argument(
            '--replace', action='store_true',
            help='REPLACE existing config instead of baseline merge. '
                 'Use when Settings are corrupted and must be restored to known-good state. '
                 'Requires double confirmation.',
        )
        parser.add_argument(
            '--yes', action='store_true',
            help='Skip first confirmation (still requires second for --replace)',
        )

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
            mode = "REPLACE" if options['replace'] else "baseline merge"
            self.stdout.write(f"\nDry run ({mode}): {would_create} would be created, {would_update} would be updated")
            return

        # ── Confirmation gate ──
        if options['replace']:
            # Double confirmation for replace mode
            if not options['yes']:
                self.stdout.write(self.style.WARNING(
                    '\n  ⚠ REPLACE MODE: This will overwrite existing Setting configs.'
                ))
                self.stdout.write(
                    '  Existing layouts, behaviors, selectlists, and schema maps '
                    'will be replaced with the bundle version.'
                )
                answer1 = input('\n  Are you sure? (yes/no): ')
                if answer1.strip().lower() != 'yes':
                    self.stdout.write('  Cancelled.')
                    return

            self.stdout.write(self.style.ERROR(
                '\n  ⚠ FINAL CONFIRMATION: When you approve this, existing Setting '
                'records will be REPLACED. User customizations in config will be lost.'
            ))
            self.stdout.write(
                '  User prefs (prefs.userdefined) will NOT be touched.'
            )
            answer2 = input('\n  Type REPLACE to confirm: ')
            if answer2.strip() != 'REPLACE':
                self.stdout.write('  Cancelled.')
                return

            self.stdout.write(self.style.SUCCESS('\n  Confirmed. Replacing settings...\n'))

        else:
            # Baseline merge — single confirmation
            if not options['yes']:
                self.stdout.write(self.style.WARNING(
                    '\n  Baseline merge: adds missing keys to existing Settings, never replaces.'
                ))
                answer = input('  Proceed? (yes/no): ')
                if answer.strip().lower() != 'yes':
                    self.stdout.write('  Cancelled.')
                    return

        from apps.core.services.setting_bootstrap import import_settings_bundle
        result = import_settings_bundle(bundle, force_replace=options['replace'])

        self.stdout.write(f"\nCreated: {result['created']}")
        self.stdout.write(f"Updated: {result['updated']}")
        if result.get('replaced'):
            self.stdout.write(f"Replaced: {result['replaced']}")
        if result.get('protected'):
            self.stdout.write(f"Protected (foundational): {result['protected']}")
        if result['errors']:
            for e in result['errors']:
                self.stderr.write(self.style.ERROR(f"  ERROR: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS('No errors.'))

        if options['validate']:
            from apps.core.services.setting_health import check_settings_health
            report = check_settings_health()
            if report['healthy']:
                self.stdout.write(self.style.SUCCESS(f"Health check: PASSED ({report['summary']})"))
            else:
                self.stdout.write(self.style.ERROR(f"Health check: FAILED ({report['summary']})"))
