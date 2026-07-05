"""
Create or update the singleton Setting record for layout_status.

Scans React2025 src/apps/ for per-model layout files (Detail.tsx, List.tsx,
Dialog.tsx, Panel.tsx) and populates the setting's .config with a tracking list.

Usage:
    python manage.py create_layout_status
    python manage.py create_layout_status --reset   # Replace existing data
    python manage.py create_layout_status --dry-run  # Preview without saving
"""
import os
import re
from collections import defaultdict
from django.core.management.base import BaseCommand
from apps.core.models import Setting


# Path to React2025 src/apps relative to webClerk3 manage.py
R25_APPS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '../../../../..', 'React2025', 'src', 'apps')
)

# Layout file suffixes we track (matched case-insensitively at end of filename)
LAYOUT_TYPES = ['Detail', 'List', 'Dialog', 'Panel']


def _scan_model_layouts(apps_dir: str) -> list[dict]:
    """Walk React2025 src/apps/ and discover per-model layout .tsx files.

    Returns a sorted list of dicts, one per unique (app, model) pair.
    """
    # Collect: { (app, model): {layout_type: [filenames]} }
    hits: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for root, _dirs, files in os.walk(apps_dir):
        for fname in files:
            if not fname.endswith('.tsx'):
                continue
            # Skip qqq_ prefixed files (deprecated/experimental)
            if fname.startswith('qqq_'):
                continue
            # Determine which layout type this file represents
            base = fname.removesuffix('.tsx')
            matched_type = None
            for lt in LAYOUT_TYPES:
                if base.endswith(lt):
                    matched_type = lt.lower()
                    break
            if not matched_type:
                continue

            # Extract app and model from path:
            # .../src/apps/{app}/models/{model}/pages/{File}.tsx
            rel = os.path.relpath(root, apps_dir)
            parts = rel.split(os.sep)
            # Expected: {app}/models/{model}/pages
            if len(parts) >= 4 and parts[1] == 'models' and parts[3] == 'pages':
                app = parts[0]
                model = parts[2]
                hits[(app, model)][matched_type].append(fname)

    # Build flat list sorted by app → model
    rows = []
    for (app, model) in sorted(hits.keys()):
        type_map = hits[(app, model)]
        row = {
            'app': app,
            'model': model,
            'detail_exists': bool(type_map.get('detail')),
            'list_exists': bool(type_map.get('list')),
            'dialog_exists': bool(type_map.get('dialog')),
            'panel_exists': bool(type_map.get('panel')),
            'detail_status': '',
            'list_status': '',
            'dialog_status': '',
            'panel_status': '',
            'assigned_to': '',
        }
        rows.append(row)
    return rows


class Command(BaseCommand):
    help = 'Create/update the layout_status singleton setting (purpose=admin)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Replace existing data even if the record already has content',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        dry_run = options.get('dry_run', False)

        if not os.path.isdir(R25_APPS_DIR):
            self.stderr.write(self.style.ERROR(
                f'React2025 apps dir not found: {R25_APPS_DIR}'
            ))
            return

        # Scan layout files
        layouts = _scan_model_layouts(R25_APPS_DIR)
        self.stdout.write(f'Discovered {len(layouts)} models with layout files\n')

        if dry_run:
            header = f"{'App':<20} {'Model':<25} {'Detail':<8} {'List':<8} {'Dialog':<8} {'Panel':<8}"
            self.stdout.write(header)
            self.stdout.write('-' * len(header))
            for row in layouts:
                self.stdout.write(
                    f"{row['app']:<20} {row['model']:<25} "
                    f"{'✓' if row['detail_exists'] else '–':<8} "
                    f"{'✓' if row['list_exists'] else '–':<8} "
                    f"{'✓' if row['dialog_exists'] else '–':<8} "
                    f"{'✓' if row['panel_exists'] else '–':<8}"
                )
            return

        # Look up or create the singleton
        setting, created = Setting.objects.get_or_create(
            name='layout_status',
            purpose='admin',
            defaults={'config': {'layouts': layouts}},
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created layout_status setting (id={setting.id}) with {len(layouts)} models'
            ))
        elif reset:
            setting.config = {'layouts': layouts}
            setting.save()
            self.stdout.write(self.style.SUCCESS(
                f'Reset layout_status setting (id={setting.id}) with {len(layouts)} models'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'layout_status setting already exists (id={setting.id}). '
                f'Use --reset to replace data.'
            ))
