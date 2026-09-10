"""
gl_journal_export — Export GL journal entries in accounting program formats.

Usage:
    python manage.py gl_journal_export --period 2026-08
    python manage.py gl_journal_export --period 2026-08 --format generic_csv
    python manage.py gl_journal_export --period 2026-08 --format quickbooks_iif
    python manage.py gl_journal_export --period 2026-08 --format xero_csv
    python manage.py gl_journal_export --period 2026-08 --format sage_csv
    python manage.py gl_journal_export --period 2026-08 --format generic_json --output /tmp/export.json
    python manage.py gl_journal_export --period 2026-08 --division 10

Formats:
    generic_json     Canonical bundle.json (default)
    generic_csv      Standard CSV — importable by most programs
    quickbooks_iif   QuickBooks Desktop IIF format
    xero_csv         Xero manual journal import CSV
    sage_csv         Sage 50 general journal CSV
"""
import os
from django.core.management.base import BaseCommand


FORMATS = ['generic_json', 'generic_csv', 'quickbooks_iif', 'xero_csv', 'sage_csv']

EXTENSIONS = {
    'generic_json': '.json',
    'generic_csv': '.csv',
    'quickbooks_iif': '.iif',
    'xero_csv': '_xero.csv',
    'sage_csv': '_sage.csv',
}


class Command(BaseCommand):
    help = 'Export GL journal entries for a period in accounting program formats'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period', required=True,
            help='Accounting period (YYYY-MM), e.g. 2026-08',
        )
        parser.add_argument(
            '--format', default='generic_json', choices=FORMATS,
            help=f'Output format (default: generic_json). Choices: {", ".join(FORMATS)}',
        )
        parser.add_argument(
            '--output', default='',
            help='Output file path (default: data/bundles/journal/<period>.<ext>)',
        )
        parser.add_argument(
            '--division', default='',
            help='Filter by division code',
        )

    def handle(self, *args, **options):
        from django.conf import settings as django_settings
        from apps.accounts.services.gl_export import gl_export

        period = options['period']
        fmt = options['format']
        division = options['division']

        content, default_filename, content_type = gl_export(period, fmt, division)

        # Determine output path
        if options['output']:
            output = options['output']
        else:
            data_dir = getattr(django_settings, 'DATA_DIR', None)
            if data_dir:
                bundle_dir = os.path.join(data_dir, 'bundles', 'journal')
            else:
                bundle_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
                    '..', '..', 'data', 'bundles', 'journal',
                )
            bundle_dir = os.path.abspath(bundle_dir)
            os.makedirs(bundle_dir, exist_ok=True)
            output = os.path.join(bundle_dir, default_filename)

        with open(output, 'w') as f:
            f.write(content)

        # Parse totals from bundle for summary output
        if fmt == 'generic_json':
            import json
            bundle = json.loads(content)
            totals = bundle['totals']
        else:
            # Re-build bundle just for totals display
            from apps.sync.services.gl_journal_bundle import build_gl_journal_bundle
            bundle = build_gl_journal_bundle(period)
            totals = bundle['totals']

        self.stdout.write(self.style.SUCCESS(
            f"Exported {totals['entry_count']} entries for {period} ({fmt})\n"
            f"  Debits:   ${totals['total_debits']:,.2f}\n"
            f"  Credits:  ${totals['total_credits']:,.2f}\n"
            f"  Balanced: {totals['balanced']}\n"
            f"  File:     {output}"
        ))
