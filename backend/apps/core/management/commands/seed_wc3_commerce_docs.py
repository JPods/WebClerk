"""Seed Document records for WC3 Commerce documentation.

Transactions, payments, inventory, ledger, commissions, forecasting —
how WC3 handles the money and the goods.

Usage:
    python manage.py seed_wc3_commerce_docs
    python manage.py seed_wc3_commerce_docs --force  # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document
from ._seed_docs_utils import build_doc_defaults


WC3_COMMERCE_DOCS = [
    {
        'ida': 'WC3-COM-TRANSACTIONS',
        'name': 'Transaction Calculations',
        'description': 'Backend and frontend calculation logic — line totals, tax, discount, inventory effects',
        'git_path': 'readmes/08-transaction-calculations.md',
        'sequence': 300,
        'tags': ['wc3', 'commerce', 'transactions', 'calculations'],
        'qq_movie': 'qq_movie_here_2026-08-12: 4-min transaction lifecycle — create order, add lines, convert to invoice, apply payment',
    },
    {
        'ida': 'WC3-COM-TRANSACTION-SAVE',
        'name': 'Transaction Save Patterns',
        'description': 'How transactions save — header, lines, pending records, GL effects',
        'git_path': 'readmes/08-transaction-save.md',
        'sequence': 310,
        'tags': ['wc3', 'commerce', 'transactions', 'save'],
    },
    {
        'ida': 'WC3-COM-CALC-STATUS',
        'name': 'Transaction Calc Status',
        'description': 'Current state of calculations and inventory transfer — known issues and roadmap',
        'git_path': 'readmes/09-transaction-calc-status.md',
        'sequence': 320,
        'tags': ['wc3', 'commerce', 'transactions', 'status'],
    },
    {
        'ida': 'WC3-COM-LEDGER',
        'name': 'Ledger & Financial System',
        'description': 'GL posting and cash/payment balance management — the accounting backbone',
        'git_path': 'readmes/ledger-financial-system.md',
        'sequence': 330,
        'tags': ['wc3', 'commerce', 'ledger', 'gl', 'accounting'],
        'qq_movie': 'qq_movie_here_2026-08-12: 3-min GL posting walkthrough — invoice creates journal, payment settles, trial balance',
    },
    {
        'ida': 'WC3-COM-PAYMENTS',
        'name': 'Payment Application Design',
        'description': 'Payment processing — application, posting, reconciliation, Spreedly integration',
        'git_path': 'readmes/payment-application-design.md',
        'sequence': 340,
        'tags': ['wc3', 'commerce', 'payments', 'spreedly'],
        'qq_movie': 'qq_movie_here_2026-08-12: 2-min payment application — apply payment to invoice, partial payment, overpayment',
    },
    {
        'ida': 'WC3-COM-COMMISSIONS',
        'name': 'Commission Operations',
        'description': 'Commission processing — calculation, split, invoice, payout',
        'git_path': 'readmes/commission-operations.md',
        'sequence': 350,
        'tags': ['wc3', 'commerce', 'commissions', 'operations'],
    },
    {
        'ida': 'WC3-COM-INVENTORY',
        'name': 'Inventory Flow Testing',
        'description': 'Inventory quantity flow — on_hand, on_so, on_po, on_wo, available; test plan',
        'git_path': 'readmes/inventory_flow_testing.md',
        'sequence': 360,
        'tags': ['wc3', 'commerce', 'inventory', 'testing'],
        'qq_movie': 'qq_movie_here_2026-08-12: 3-min inventory buckets — order allocates, invoice ships, purchase receives, available updates',
    },
    {
        'ida': 'WC3-COM-ORGS-FINANCIAL',
        'name': 'Org Financial Structure',
        'description': 'Organization financial objects — AR/AP, credit limits, payment terms, aging',
        'git_path': 'readmes/orgs-financial-structure.md',
        'sequence': 370,
        'tags': ['wc3', 'commerce', 'orgs', 'financial'],
    },
    {
        'ida': 'WC3-COM-EROSION',
        'name': 'Erosion Tracking',
        'description': 'Captures value loss events across transaction stages — margin visibility',
        'git_path': 'readmes/erosion-tracking.md',
        'sequence': 380,
        'tags': ['wc3', 'commerce', 'erosion', 'margin'],
    },
    {
        'ida': 'WC3-COM-FORECASTING',
        'name': 'Forecasting',
        'description': 'Demand, supply, and cash flow forecasting — forward-looking commerce intelligence',
        'git_path': 'readmes/forecasting.md',
        'sequence': 390,
        'tags': ['wc3', 'commerce', 'forecasting', 'planning'],
    },
    {
        'ida': 'WC3-COM-INVENTORY-OBSERVER',
        'name': 'LLM Inventory Observer',
        'description': 'AI-driven inventory observation — Alice watches quantities and flags anomalies',
        'git_path': 'readmes/llm-inventory-observer.md',
        'sequence': 395,
        'tags': ['wc3', 'commerce', 'inventory', 'alice', 'llm'],
    },
    {
        'ida': 'WC3-COM-STATEMENTS',
        'name': 'Statement Harvester',
        'description': 'JSON-based statement processing — CSV to JSON to classified to promoted',
        'git_path': 'readmes/statement-harvester.md',
        'sequence': 398,
        'tags': ['wc3', 'commerce', 'statements', 'harvester'],
    },
]


class Command(BaseCommand):
    help = 'Seed Document records for WC3 Commerce documentation'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing records')

    def handle(self, *args, **options):
        force = options['force']
        created = updated = skipped = missing = 0

        for doc in WC3_COMMERCE_DOCS:
            existing = Document.objects.filter(ida=doc['ida']).first()
            if existing and not force:
                skipped += 1
                continue

            defaults = build_doc_defaults(doc, 'wc3-commerce')
            if not defaults['body']:
                missing += 1
                self.stdout.write(self.style.WARNING(f'  Missing: {doc["git_path"]}'))

            obj, was_created = Document.objects.update_or_create(
                ida=doc['ida'], defaults=defaults,
            )
            if was_created:
                created += 1
                self.stdout.write(f'  Created: {doc["ida"]}')
            else:
                updated += 1
                self.stdout.write(f'  Updated: {doc["ida"]}')

        self.stdout.write(self.style.SUCCESS(
            f'\nWC3 Commerce docs: {created} created, {updated} updated, {skipped} skipped'
            + (f', {missing} missing files' if missing else '')
        ))
