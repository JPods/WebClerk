"""
seed_freshstart — Build a complete fresh WC3 database from scratch.

Usage:
    python manage.py seed_freshstart

Runs all seed commands in order to populate a new database with
system configuration data: settings, reports, GL accounts, terms,
DataBrowser layouts, RBAC, search presets, and Alice coaching.

After running, the database is ready for a new company to start
entering their own contacts, items, and transactions.

Prerequisites: migrations must be applied first (manage.py migrate).
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


SEED_SEQUENCE = [
    # Foundation — must run first
    ('seed_field_access',       {}),
    ('seed_company_settings',   {}),
    ('seed_rbac_roles',         {}),

    # Data — GL and terms
    ('seed_gl_accounts',        {}),
    ('seed_terms',              {}),

    # UI — reports, DataBrowser, search, layouts, select lists
    ('seed_reports',            {}),
    ('seed_databrowser',        {}),
    ('seed_column_widths',      {}),
    ('seed_search_presets',     {}),
    ('seed_alice_layouts',      {}),
    ('seed_select_lists',       {}),

    # QA templates
    ('seed_qa_templates',       {}),

    # Connections — agent channels, deploy targets
    ('seed_connections',        {}),

    # Operational
    ('seed_coaching',           {}),
    ('seed_wchq_settings',     {}),
    ('seed_collaborate_settings', {}),

    # Model schema definitions
    ('seed_all_schema_maps',    {}),
    ('seed_serial_settings',    {}),  # serial-specific actions/behaviors on top of base schema
    ('seed_status_guards',      {}),  # transaction status transitions + journalized locks
    ('seed_receivables_layouts', {}),  # aged receivables report + customer statement print layouts

    # GL defaults into items/orgs/payment methods
    ('seed_gl_defaults',        {}),

    # Documents — system docs, report templates, print layouts
    ('seed_wc3_commerce_docs',  {}),
    ('seed_wc3_operations_docs', {}),
    ('seed_wc3_system_docs',    {}),
    ('seed_report_templates',   {}),
    ('seed_template_reports',   {}),
    ('seed_print_layouts',      {}),

    # DBSR explanations + health manifest (must run after all other seeds)
    ('seed_dbsr_explanations',  {}),
    ('seed_dbsr_document',      {}),
]


class Command(BaseCommand):
    help = 'Seed a fresh WC3 database with all system configuration data'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Pass --force to each seed command that supports it')

    def handle(self, *args, **options):
        force = options.get('force', False)
        self.stdout.write(self.style.MIGRATE_HEADING('seed_freshstart — seeding all system data'))

        for cmd_name, kwargs in SEED_SEQUENCE:
            self.stdout.write(f'\n  Running {cmd_name}...')
            try:
                cmd_kwargs = dict(kwargs)
                if force:
                    cmd_kwargs['force'] = True
                call_command(cmd_name, **cmd_kwargs, stdout=self.stdout)
            except TypeError:
                # Command doesn't accept --force
                call_command(cmd_name, **kwargs, stdout=self.stdout)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  {cmd_name} failed: {e}'))

        self.stdout.write(self.style.SUCCESS('\nseed_freshstart complete'))
