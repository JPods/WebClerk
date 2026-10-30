"""Bundle imports: list them, or load one again once its defects are resolved.

Every import is a Bundle row (apps/core/services/bundle_import.py); its file sits in
WORK_DIR/bundles/general/incoming/<pending|defects|completed>/.

Usage:
    python manage.py import_bundle                 # the imports, newest first
    python manage.py import_bundle --defects       # only those with defects
    python manage.py import_bundle --rerun 42      # load bundle 42 again
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'List bundle imports, or load one again after its defects are resolved'

    def add_arguments(self, parser):
        parser.add_argument('--rerun', type=int, help='Bundle id to load again')
        parser.add_argument('--defects', action='store_true', help='Only imports with defects')
        parser.add_argument('--limit', type=int, default=20)

    def handle(self, *args, **options):
        from apps.core.services import bundle_import
        from apps.sync.models.bundle import Bundle

        if options['rerun']:
            result = bundle_import.rerun(options['rerun'])
            defects = result.get('errors') or []
            style = self.style.WARNING if defects else self.style.SUCCESS
            self.stdout.write(style(f"Bundle #{options['rerun']}: {len(defects)} defect(s)"))
            for d in defects[:20]:
                self.stdout.write(f'  {d}')
            return

        rows = Bundle.objects.filter(purpose=bundle_import.PURPOSE).order_by('-id')
        if options['defects']:
            rows = rows.filter(status='defects')
        for b in rows[:options['limit']]:
            r = b.response or {}
            self.stdout.write(f"#{b.pk:<6} {b.model_name:<18} {b.status:<10} "
                              f"{len(r.get('defects') or []):>4} defect(s)  {r.get('source', '')}")
