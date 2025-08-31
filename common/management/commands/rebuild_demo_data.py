"""Unified developer convenience command to rebuild demo data.

Workflow encapsulated:
 1. (Optional) Export current data snapshot (pre-reset) for backup.
 2. Flush or confirm empty DB state (does not drop migrations).
 3. Run core seed / setup commands in opinionated order.
 4. Optionally export a fresh canonical snapshot (post seeds) via demo_data_import_export.

Usage examples:
  python manage.py rebuild_demo_data --export-before --export-after
  python manage.py rebuild_demo_data --no-export --projects 5 --project-tasks-min 2 --project-tasks-max 5
  python manage.py rebuild_demo_data --skip-docs --skip-links

Flags allow selective skipping. This avoids manually invoking multiple seed commands.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections
from django.utils import timezone


class Command(BaseCommand):
    help = "Rebuild demo data by running seed commands and optional export/import snapshots."

    def add_arguments(self, parser):  # pragma: no cover - CLI plumbing
        parser.add_argument('--export-before', action='store_true', help='Export snapshot before rebuild (if data present).')
        parser.add_argument('--export-after', action='store_true', help='Export snapshot after rebuild seeds.')
        parser.add_argument('--no-export', action='store_true', help='Disable any export steps (overrides export-before/after).')
        parser.add_argument('--flush', action='store_true', help='Flush DB (Django flush) before seeding instead of assuming empty.')
        parser.add_argument('--projects', type=int, default=5, help='Projects to seed (passed to seed_projects).')
        parser.add_argument('--project-tasks-min', type=int, default=2, help='Min tasks per project.')
        parser.add_argument('--project-tasks-max', type=int, default=6, help='Max tasks per project.')
        parser.add_argument('--project-link-orders', type=int, default=3, help='Orders to attempt linking per project.')
        parser.add_argument('--simulate-profit', action='store_true', help='Simulate profit on seeded projects.')
        parser.add_argument('--skip-orgs', action='store_true', help='Skip seeding orgs.')
        parser.add_argument('--skip-transactions', action='store_true', help='Skip seeding base transactions.')
        parser.add_argument('--skip-projects', action='store_true', help='Skip seeding projects.')
        parser.add_argument('--skip-links', action='store_true', help='Skip creating project associations.')
        parser.add_argument('--skip-docs', action='store_true', help='Skip seeding documents.')
        parser.add_argument('--randomize-links', action='store_true', help='Randomize selection for project links.')

    def handle(self, *args, **opts):  # pragma: no cover - orchestration
        export_disabled = opts['no_export']
        export_before = opts['export_before'] and not export_disabled
        export_after = opts['export_after'] and not export_disabled

        # 1. Optional pre-export
        if export_before:
            self.stdout.write(self.style.MIGRATE_HEADING('Exporting pre-rebuild snapshot...'))
            self._safe_call('demo_data_import_export', 'export')

        # 2. Optional flush
        if opts['flush']:
            self.stdout.write(self.style.WARNING('Flushing database (Django flush)...'))
            self._safe_call('flush', interactive=False)

        # 3. Seeds (ordered)
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding baseline data...'))
        if not opts['skip_orgs']:
            self._safe_call('seed_orgs')
        if not opts['skip_transactions']:
            # Provide a small default volume; command may have its own defaults
            self._safe_call('seed_transactions')
        if not opts['skip_projects']:
            proj_kwargs = {
                'projects': int(opts['projects']),
                'tasks_min': int(opts['project_tasks_min']),
                'tasks_max': int(opts['project_tasks_max']),
            }
            if opts['project_link_orders']:
                proj_kwargs['link_orders'] = int(opts['project_link_orders'])
            # Boolean flags: call_command accepts presence only
            if opts['simulate_profit']:
                self._safe_call('seed_projects', simulate_profit=True, **proj_kwargs)
            else:
                self._safe_call('seed_projects', **proj_kwargs)
        if not opts['skip_links']:
            link_kwargs = {
                'per_project': 2,
                'models': 'order,proposal',
            }
            if opts['randomize_links']:
                self._safe_call('seed_project_links', randomize=True, **link_kwargs)
            else:
                self._safe_call('seed_project_links', **link_kwargs)
        if not opts['skip_docs']:
            self._safe_call('seed_documents')

        # 4. Optional post-export
        if export_after:
            self.stdout.write(self.style.MIGRATE_HEADING('Exporting post-rebuild snapshot...'))
            self._safe_call('demo_data_import_export', 'export')

        self.stdout.write(self.style.SUCCESS('Rebuild demo data completed.'))

    # ---- helpers ---------------------------------------------------------
    def _safe_call(self, command_name, *cargs, **kwargs):
        try:
            call_command(command_name, *cargs, **kwargs)
        except Exception as exc:  # pragma: no cover
            self.stdout.write(self.style.ERROR(f"Command {command_name} failed: {exc}"))
            raise
