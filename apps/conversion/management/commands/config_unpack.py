"""
Management command — unpack fields from config.original to named config keys.

Users ask Alice: "show me what's in the original data for items"
Alice runs: python manage.py config_unpack list item

User says: "I need the barCode field"
Alice runs: python manage.py config_unpack promote item barCode --as bar_code

Alice learns a field is junk:
Alice runs: python manage.py config_unpack demote item bar_code

Usage:
  # List available fields in config.original
  python manage.py config_unpack list item
  python manage.py config_unpack list customer

  # Promote a field (unpack from config.original to config.{key})
  python manage.py config_unpack promote item barCode
  python manage.py config_unpack promote item barCode --as bar_code
  python manage.py config_unpack promote item barCode --dry-run

  # Promote multiple fields
  python manage.py config_unpack promote item barCode ean mfrItemNum

  # Demote a field (remove named key, value stays in original)
  python manage.py config_unpack demote item bar_code
"""

from django.core.management.base import BaseCommand

from apps.conversion.services.config_unpack import (
    list_original_fields,
    unpack_field,
    demote_field,
)


class Command(BaseCommand):
    help = "Unpack fields from config.original to named config keys"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='action')

        # list
        p_list = sub.add_parser('list', help='List available fields in config.original')
        p_list.add_argument('model', type=str, help='Model name: item, customer, vendor, order, etc.')
        p_list.add_argument('--sample', type=int, default=100, help='Number of records to sample')

        # promote
        p_promote = sub.add_parser('promote', help='Promote field(s) from config.original')
        p_promote.add_argument('model', type=str)
        p_promote.add_argument('fields', nargs='+', help='WC2 field name(s) in config.original')
        p_promote.add_argument('--as', dest='config_key', type=str, help='Target config key name (single field only)')
        p_promote.add_argument('--dry-run', action='store_true')

        # demote
        p_demote = sub.add_parser('demote', help='Remove a named config key (value stays in original)')
        p_demote.add_argument('model', type=str)
        p_demote.add_argument('key', type=str, help='Config key to remove')
        p_demote.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        action = options.get('action')
        if action == 'list':
            self._list(options['model'], options.get('sample', 100))
        elif action == 'promote':
            self._promote(options['model'], options['fields'],
                          options.get('config_key'), options.get('dry_run', False))
        elif action == 'demote':
            self._demote(options['model'], options['key'], options.get('dry_run', False))
        else:
            self.stderr.write("Usage: config_unpack {list|promote|demote} <model> ...")

    def _list(self, model, sample_size):
        fields = list_original_fields(model, sample_size=sample_size)
        if not fields:
            self.stdout.write("No config.original data found.")
            return

        self.stdout.write(f"\n{'Field':<30} {'Count':>6}  {'Type':<8}  {'Sample'}")
        self.stdout.write('─' * 90)
        for name, info in fields.items():
            marker = ' ✓' if info.get('already_extracted') else ''
            self.stdout.write(
                f"{name:<30} {info['count']:>6}  {info['type']:<8}  {info['sample']}{marker}"
            )
        self.stdout.write(f"\n✓ = already extracted to a named config key")

    def _promote(self, model, fields, config_key, dry_run):
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN"))

        if config_key and len(fields) > 1:
            self.stderr.write("--as can only be used with a single field")
            return

        for field in fields:
            key = config_key if config_key else field
            result = unpack_field(model, field, config_key=key, dry_run=dry_run)
            self.stdout.write(
                f"  {field} → config.{key}: "
                f"{result['updated']} updated, {result['skipped']} skipped, {result['empty']} empty"
            )

    def _demote(self, model, key, dry_run):
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN"))
        result = demote_field(model, key, dry_run=dry_run)
        self.stdout.write(f"  config.{key}: {result['removed']} removed")
