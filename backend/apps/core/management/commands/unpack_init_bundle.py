"""Unpack a recommended set — Settings, Reports and the chart into a database.

uuid controls the merge: existing records are updated, missing ones created,
and the owner's own values are never overwritten. The merge itself lives in
apps/core/services/init_bundle.py, which is also what the runtime uses when it
finds a definition set missing — one loader, one set of rules.

Usage:
    python manage.py unpack_init_bundle                           # from init-bundle.json
    python manage.py unpack_init_bundle --input /tmp/init.json    # custom path
    python manage.py unpack_init_bundle --dry-run                 # show what would change
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import Settings + Reports from init-bundle.json (seed a new database)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input', type=str, default='init-bundle.json',
            help='Input file path (default: init-bundle.json in project root)',
        )
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would change without writing')

    def handle(self, *args, **options):
        from apps.core.services.installation_init import load_bundle, unwrap_envelope

        input_path = Path(options['input'])
        if not input_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {input_path}"))
            return

        with open(input_path) as f:
            payload = json.load(f)

        bundle = unwrap_envelope(payload)
        if bundle is None:
            self.stderr.write(self.style.ERROR(
                f"{input_path} carried no settings, reports or gl_accounts"))
            return

        dry_run = options['dry_run']
        counts = {k: len(bundle.get(k) or []) for k in ('settings', 'reports', 'gl_accounts')}
        self.stdout.write(
            f"\nInit bundle: {counts['settings']} settings, {counts['reports']} reports, "
            f"{counts['gl_accounts']} gl accounts")
        self.stdout.write(
            f"Source: {payload.get('source', bundle.get('source', '?'))} — "
            f"{payload.get('dt_exported', bundle.get('dt_exported', '?'))}")

        result = load_bundle(bundle, dry_run=dry_run)

        label = 'Dry run' if dry_run else 'Result'
        for key in ('settings', 'reports', 'gl_accounts'):
            part = result[key]
            self.stdout.write(
                f"{label} — {key}: {part['created']} created, {part['updated']} updated")

        if result['errors']:
            self.stdout.write(self.style.WARNING(f"\n{len(result['errors'])} error(s):"))
            for err in result['errors'][:20]:
                self.stdout.write(f'  {err}')
        else:
            self.stdout.write(self.style.SUCCESS('\nNo errors.'))
