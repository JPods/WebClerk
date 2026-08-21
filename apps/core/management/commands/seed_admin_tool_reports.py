"""
seed_admin_tool_reports — Create Report records for admin utility tools.

Each Report maps to a management command. The frontend runs them via
the run_admin_tool action on /wcapi/manage/.

Usage:
    python manage.py seed_admin_tool_reports
    python manage.py seed_admin_tool_reports --force   # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.core.models.report import Report


ADMIN_TOOLS = [
    {
        'ida': 'admin-tool-audit-field-behaviors',
        'name': 'Audit Field Behaviors',
        'description': 'Review computed field behaviors across all models. Flags misdetections, stale overrides, missing types.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 10,
        'config': {
            'command': 'audit_field_behaviors',
            'default_args': ['--json'],
            'parameters': [
                {'name': 'model', 'type': 'text', 'label': 'Model (blank=all)', 'required': False},
                {'name': 'detail', 'type': 'boolean', 'label': 'Show detail', 'default': False},
            ],
        },
        'explanation': (
            'Runs field_behaviors service against every model in MODEL_REGISTRY. '
            'Compares computed behaviors (from Django field metadata) with stored overrides '
            'in wc:model Settings. Flags: UNTYPED, BAD_LOOKUP, ORPHAN_OVR, EMPTY_OPTS, '
            'OVERRIDE, PHONE_NAME. Use Cmd+Shift+click on field labels to fix flagged fields.'
        ),
    },
    {
        'ida': 'admin-tool-audit-select-lists',
        'name': 'Audit Select Lists',
        'description': 'Export and review all select lists organized by model, field, and source.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 20,
        'config': {
            'command': 'audit_select_lists',
            'default_args': ['--json'],
            'parameters': [
                {'name': 'model', 'type': 'text', 'label': 'Model (blank=all)', 'required': False},
                {'name': 'detail', 'type': 'boolean', 'label': 'Show options', 'default': False},
            ],
        },
        'explanation': (
            'Shows every select-type field across all models: where options come from '
            '(hardcoded in service, Setting override, or config.select_lists), how many options, '
            'and the actual values. Flags: EMPTY (no options), DRIFT (same field name has '
            'different options on different models), ORPHAN (select_lists entry for non-select field).'
        ),
    },
    {
        'ida': 'admin-tool-seed-model-definitions',
        'name': 'Seed Model Definitions',
        'description': 'Regenerate wc:model Setting records for all models. Use --force to overwrite.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 30,
        'config': {
            'command': 'seed_model_definitions',
            'default_args': [],
            'parameters': [
                {'name': 'model', 'type': 'text', 'label': 'Model (blank=all)', 'required': False},
                {'name': 'force', 'type': 'boolean', 'label': 'Overwrite existing', 'default': False},
                {'name': 'dry-run', 'type': 'boolean', 'label': 'Dry run (report only)', 'default': False},
            ],
        },
        'explanation': (
            'Creates or updates the consolidated wc:model Setting record for each model. '
            'Each record contains schema, access roles, behaviors, field groups, layouts, '
            'select lists, formatting, and defaults. Without --force, skips existing records.'
        ),
    },
    {
        'ida': 'admin-tool-seed-company-settings',
        'name': 'Seed Company Settings',
        'description': 'Create or update the company profile Setting with default structure.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 40,
        'config': {
            'command': 'seed_company_settings',
            'default_args': [],
            'parameters': [],
        },
        'explanation': (
            'Creates the company-profile Setting (purpose=wc:company_profile) with address, '
            'ship-to address, logos, print defaults, receivables settings, and accounting config. '
            'Merges new keys without overwriting existing values.'
        ),
    },
    {
        'ida': 'admin-tool-load-demo-data',
        'name': 'Load Demo Data',
        'description': 'Import demo contacts, items, and transactions for training. '
                       'All records tagged for clean removal.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 50,
        'config': {
            'command': 'load_demo_data',
            'default_args': [],
            'parameters': [
                {'name': 'input', 'type': 'text', 'label': 'Bundle file path', 'default': 'demo-bundle.json', 'required': False},
                {'name': 'data-only', 'type': 'boolean', 'label': 'Data only (skip settings)', 'default': False},
                {'name': 'settings-only', 'type': 'boolean', 'label': 'Settings only (skip data)', 'default': False},
            ],
        },
        'explanation': (
            'Loads a demo bundle (Settings + sample data) from a JSON file. '
            'All non-Setting records are tagged refs.source="demo-baseline" so they '
            'can be cleanly removed later. Settings are merged (add missing, never replace existing).'
        ),
    },
    {
        'ida': 'admin-tool-remove-demo-data',
        'name': 'Remove Demo Data',
        'description': 'Delete all demo records (refs.source="demo-baseline"). Settings are preserved.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 60,
        'config': {
            'command': 'remove_demo_data',
            'default_args': ['--json'],
            'parameters': [
                {'name': 'source', 'type': 'text', 'label': 'Source tag', 'default': 'demo-baseline', 'required': False},
            ],
        },
        'explanation': (
            'Removes all data records where refs.source matches the given tag (default: demo-baseline). '
            'Deletes in dependency order (GL → payments → lines → transactions → items → contacts). '
            'Settings are NEVER removed — they are system infrastructure.'
        ),
    },
    {
        'ida': 'admin-tool-seed-demo',
        'name': 'Seed Demo Data',
        'description': 'Create demo contacts, items, orgs, and BOM. Foundation for seed_demo_transactions.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 70,
        'config': {
            'command': 'seed_demo',
            'default_args': [],
            'parameters': [
                {'name': 'force', 'type': 'boolean', 'label': 'Delete and re-seed', 'default': False},
            ],
        },
        'explanation': (
            'Creates 12 items (bats, balls, gloves, bags, training, kit with BOM), '
            '5 customers, 1 vendor, and 7 contacts. All tagged refs.source="demo-baseline". '
            'Run seed_demo_transactions after this to create full transaction cycles.'
        ),
    },
    {
        'ida': 'admin-tool-seed-demo-transactions',
        'name': 'Seed Demo Transactions',
        'description': 'Create 3 complete transaction cycles: proposal → order → invoice → payment → GL.',
        'model_name': 'setting',
        'category': 'utility',
        'output_type': 'json',
        'role_required': 'admin',
        'sort_order': 80,
        'config': {
            'command': 'seed_demo_transactions',
            'default_args': [],
            'parameters': [
                {'name': 'force', 'type': 'boolean', 'label': 'Delete and re-seed', 'default': False},
            ],
        },
        'explanation': (
            'Creates 3 transaction cycles using items and contacts from seed_demo: '
            'Riverside Sports (fully paid), Metro Baseball Academy (split payment), '
            'Eastside Little League (single payment). Each cycle: proposal → order → '
            'invoice → payment → GL journal entries. All tagged refs.source="demo-baseline".'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed Report records for admin utility tools'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing')

    def handle(self, *args, **options):
        force = options.get('force', False)
        created = updated = skipped = 0

        for tool in ADMIN_TOOLS:
            existing = Report.objects.filter(ida=tool['ida']).first()

            if existing and not force:
                skipped += 1
                continue

            if existing:
                for key, val in tool.items():
                    if key != 'ida':
                        setattr(existing, key, val)
                existing.save()
                updated += 1
            else:
                Report.objects.create(**tool)
                created += 1

            self.stdout.write(f"  {tool['ida']}: {tool['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nAdmin tools: {created} created, {updated} updated, {skipped} skipped"
        ))
