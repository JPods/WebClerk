"""Pack the recommended set — what WC_HQ publishes to installations.

Every new WC3 database starts from this file, and webclerk.com serves it at
/wcapi/get/bundle_init.json. What goes in it is declared once, in
apps/core/services/bundle_catalogue.py — the same declaration the named
bundle endpoints serve from, so the file and the endpoints cannot drift.

Usage:
    python manage.py pack_init_bundle                             # write to init-bundle.json
    python manage.py pack_init_bundle --output /tmp/init.json     # custom path
    python manage.py pack_init_bundle --dry-run                   # show what would be exported
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Export Settings + Reports + chart as init-bundle.json (the recommended set)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', type=str, default='init-bundle.json',
            help='Output file path (default: init-bundle.json in project root)',
        )
        parser.add_argument('--dry-run', action='store_true',
                            help='Show counts without writing')

    def handle(self, *args, **options):
        from apps.core.services.bundle_catalogue import pack_init
        from apps.core.services.report_registry import seed_shipped_reports

        # The executable reports this release ships must exist as records
        # before they can be packed — otherwise HQ publishes a set without them.
        seeded = seed_shipped_reports()
        self.stdout.write(f'Executable reports present: {len(seeded)}')

        packed = pack_init()
        bundle = {
            'version': '1.0',
            'source': 'pack_init_bundle',
            'dt_exported': datetime.now(timezone.utc).isoformat(),
            **packed,
        }
        for key in ('settings', 'reports', 'gl_accounts'):
            bundle[f'{key}_count'] = len(bundle.get(key) or [])

        self.stdout.write('\n=== Recommended set ===')
        for key in ('settings', 'reports', 'gl_accounts'):
            self.stdout.write(f"  {key}: {bundle[f'{key}_count']}")

        categories = {}
        for r in bundle.get('reports') or []:
            c = r.get('category') or '?'
            categories[c] = categories.get(c, 0) + 1
        self.stdout.write(f'  report categories: {categories}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\nDry run — nothing written.'))
            return

        out = Path(options['output'])
        with open(out, 'w') as fh:
            json.dump(bundle, fh, indent=2, ensure_ascii=False)
        size_kb = out.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(f'\nWrote {out} ({size_kb:.0f} KB)'))
