"""
gl_journal_export — Export GL journal entries as bundle.json.

Usage:
    python manage.py gl_journal_export --period 2026-08
    python manage.py gl_journal_export --period 2026-08 --output /tmp/bundle.json

The bundle.json is the canonical format for all accounting handoffs.
Feed it to the Journal Formatter (tools/journal_formatter.html) to
convert to QuickBooks, Xero, Sage, or generic CSV.
"""
import json
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Export GL journal entries for a period as bundle.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period', required=True,
            help='Accounting period (YYYY-MM), e.g. 2026-08',
        )
        parser.add_argument(
            '--output', default='',
            help='Output file path (default: <company>_<period>_bundle.json)',
        )

    def handle(self, *args, **options):
        import os
        from django.conf import settings as django_settings
        from apps.sync.services.gl_journal_bundle import build_gl_journal_bundle

        period = options['period']
        bundle = build_gl_journal_bundle(period)

        # Default output: data/bundles/journal/<period>_bundle.json
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
            output = os.path.join(bundle_dir, f'{period}_bundle.json')

        with open(output, 'w') as f:
            json.dump(bundle, f, indent=2, default=str)

        totals = bundle['totals']
        self.stdout.write(self.style.SUCCESS(
            f"Exported {totals['entry_count']} entries for {period}\n"
            f"  Source:  {bundle['source'].get('name', '?')} ({bundle['source'].get('uuid', '?')[:8]}...)\n"
            f"  Debits:  ${totals['total_debits']:,.2f}\n"
            f"  Credits: ${totals['total_credits']:,.2f}\n"
            f"  Balanced: {totals['balanced']}\n"
            f"  File:    {output}"
        ))
