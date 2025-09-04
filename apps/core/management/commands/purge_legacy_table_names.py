"""Purge stale Setting rows referencing legacy singular / deprecated table names.

Dev-only utility: safely delete inactive or obsolete view_edit Settings that
use table_name values we no longer support after pluralization refactor.

Default behavior (no flags): dry-run summary only.

Examples:
  python manage.py purge_legacy_table_names               # dry run
  python manage.py purge_legacy_table_names --apply       # actually delete
  python manage.py purge_legacy_table_names --apply --purpose view_edit

Exit codes: 0 on success, >0 on unexpected error.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models.setting import Setting

LEGACY_NAMES = {
    # line tables (pre-plural)
    'sales_order_line', 'purchase_order_line', 'workorder_line', 'work_order_line',
    # header tables (pre-plural / generic)
    'sales_order', 'order', 'orders',
    'purchase_order', 'purchase', 'purchases',
    'workorder', 'work_order', 'workorders',
}


class Command(BaseCommand):
    help = "Remove stale Setting rows using legacy singular table_name identifiers (dry-run by default)."

    def add_arguments(self, parser):  # pragma: no cover (arg parsing)
        parser.add_argument('--apply', action='store_true', help='Execute deletions instead of dry-run summary.')
        parser.add_argument('--purpose', type=str, default=None, help='Optional Setting.purpose filter (e.g. view_edit).')

    def handle(self, *args, **opts):
        apply = opts['apply']
        purpose = opts.get('purpose')
        qs = Setting.objects.filter(table_name__in=LEGACY_NAMES)
        if purpose:
            qs = qs.filter(purpose=purpose)

        total = qs.count()
        if not total:
            self.stdout.write(self.style.SUCCESS('No legacy table_name Setting rows found.'))
            return

        # Collect a lightweight preview (avoid loading large JSON fully if not needed)
        preview = list(qs.values('id', 'table_name', 'purpose', 'role', 'is_active')[:50])
        self.stdout.write(self.style.WARNING(
            f"Found {total} legacy Setting row(s) referencing deprecated table names."
        ))
        for row in preview:
            self.stdout.write(f" - id={row['id']} table={row['table_name']} purpose={row['purpose']} role={row['role']} active={row['is_active']}")
        if total > 50:
            self.stdout.write(f" ... ({total - 50} more not shown) ...")

        if not apply:
            self.stdout.write(self.style.NOTICE('Dry-run complete. Re-run with --apply to delete.'))
            return

        with transaction.atomic():
            deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} legacy Setting row(s).'))
