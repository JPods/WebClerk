"""
Seed status guard rules into schema_map Settings for transaction models.

Stores the allowed transitions matrix and pre-condition rules in each
transaction type's Setting record (purpose='wc:schema_map'). This makes
the rules visible in the DataBrowser and editable by admin without
code changes.

The service (status_guard.py) reads these from code constants today.
When we need per-company customization, it will read from Settings instead.

Usage:
    ./bin/python manage.py seed_status_guards
    ./bin/python manage.py seed_status_guards --force   # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting
from apps.transactions.services.status_guard import TRANSITIONS, TERMINAL, JOURNALIZABLE_MODELS


# Pre-condition rules — human-readable, stored for documentation and future UI
PRECONDITIONS = {
    'released': [
        {'check': 'has_lines', 'message': 'Must have at least one line'},
    ],
    'canceled': [
        {'check': 'no_journal_entries', 'message': 'Cannot cancel with journalized GL entries'},
    ],
}

MODEL_PRECONDITIONS = {
    'proposal': {
        'released': [
            {'check': 'has_lines', 'message': 'Must have at least one line'},
            {'check': 'has_customer', 'message': 'Must have a customer assigned'},
        ],
    },
    'order': {
        'complete': [
            {'check': 'all_lines_shipped', 'message': 'All lines must be shipped'},
        ],
    },
}


TRANSACTION_MODELS = [
    'proposal', 'order', 'invoice', 'purchase',
    'workorder', 'requisition', 'payment',
]

TX_STATUSES = {
    'proposal': [
        {'value': 'planned', 'label': 'Planned'},
        {'value': 'released', 'label': 'Released'},
        {'value': 'sent', 'label': 'Sent'},
        {'value': 'accepted', 'label': 'Accepted'},
        {'value': 'rejected', 'label': 'Rejected'},
        {'value': 'converted', 'label': 'Converted'},
        {'value': 'in_progress', 'label': 'In Progress'},
        {'value': 'hold', 'label': 'Hold'},
        {'value': 'complete', 'label': 'Complete'},
        {'value': 'canceled', 'label': 'Canceled'},
    ],
    'payment': [
        {'value': 'planned', 'label': 'Planned'},
        {'value': 'released', 'label': 'Released'},
        {'value': 'complete', 'label': 'Complete'},
        {'value': 'canceled', 'label': 'Canceled'},
        {'value': 'voided', 'label': 'Voided'},
    ],
    '_default': [
        {'value': 'planned', 'label': 'Planned'},
        {'value': 'released', 'label': 'Released'},
        {'value': 'in_progress', 'label': 'In Progress'},
        {'value': 'hold', 'label': 'Hold'},
        {'value': 'complete', 'label': 'Complete'},
        {'value': 'canceled', 'label': 'Canceled'},
    ],
}


class Command(BaseCommand):
    help = 'Seed status guard rules into schema_map Settings for transaction models'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing status_transitions')

    def handle(self, *args, **options):
        force = options.get('force', False)
        updated = skipped = created_new = 0

        for model_key in TRANSACTION_MODELS:
            transitions = TRANSITIONS.get(model_key, {})
            statuses = TX_STATUSES.get(model_key, TX_STATUSES['_default'])

            # Merge preconditions: global + model-specific
            preconditions = {}
            for status_key, checks in PRECONDITIONS.items():
                preconditions[status_key] = list(checks)
            for status_key, checks in MODEL_PRECONDITIONS.get(model_key, {}).items():
                preconditions[status_key] = checks  # model-specific replaces global

            guard_config = {
                'status_transitions': transitions,
                'status_preconditions': preconditions,
                'statuses': statuses,
                'terminal_statuses': sorted(TERMINAL),
                'journalizable': model_key in JOURNALIZABLE_MODELS,
            }

            # Find existing schema_map Setting
            existing = Setting.objects.filter(
                parent_model=model_key, purpose='wc:schema_map', is_active=True,
            ).first()

            if existing:
                config = existing.config or {}
                if 'status_transitions' in config and not force:
                    skipped += 1
                    self.stdout.write(f'  {model_key}: already has status_transitions (use --force)')
                    continue
                config.update(guard_config)
                existing.config = config
                existing.save()
                updated += 1
                self.stdout.write(f'  {model_key}: updated schema_map with status guards')
            else:
                Setting.objects.create(
                    name=f'{model_key} schema and behaviors',
                    parent_model=model_key,
                    purpose='wc:schema_map',
                    scope='system',
                    config=guard_config,
                )
                created_new += 1
                self.stdout.write(f'  {model_key}: created schema_map with status guards')

        self.stdout.write(self.style.SUCCESS(
            f'Status guards: {updated} updated, {created_new} created, {skipped} skipped'
        ))
