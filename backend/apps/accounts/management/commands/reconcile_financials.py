"""
Check each org's money against the journal (balance_checker.check_cash) and refresh its
balances. YTD lives in org.metrics (compute_org_metrics, via update_org_balances).

Usage:
    python manage.py reconcile_financials
    python manage.py reconcile_financials --org-id=<id>
    python manage.py reconcile_financials --rebuild
    python manage.py reconcile_financials --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reconcile financial data for orgs based on ledger records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id',
            type=str,
            help='Specific org ID to reconcile (otherwise all orgs)',
        )
        parser.add_argument(
            '--org-type',
            type=str,
            choices=['customer', 'vendor', 'manufacturer', 'rep', 'employee'],
            help='Filter orgs by type',
        )
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild all ledgers from source documents (WARNING: destructive)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Check for discrepancies without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of orgs to process per batch (default: 100)',
        )

    def handle(self, *args, **options):
        from django.apps import apps as dj_apps
        from apps.accounts.services.ledger_balance import rebuild_org_ledgers, update_org_balances
        from apps.core.services.balance_checker import check_cash
        
        OrgBase = dj_apps.get_model('orgs', 'OrgBase')
        
        org_id = options.get('org_id')
        org_type = options.get('org_type')
        rebuild = options.get('rebuild')
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        
        # Build queryset
        queryset = OrgBase.objects.all()
        
        if org_id:
            queryset = queryset.filter(id=org_id)
        
        if org_type:
            queryset = queryset.filter(org_type=org_type)
        
        total_count = queryset.count()
        self.stdout.write(f'Processing {total_count} org(s)...')
        
        if rebuild and not dry_run:
            self.stdout.write(self.style.WARNING(
                'WARNING: --rebuild will delete and recreate all ledger records!'
            ))
            confirm = input('Type "yes" to continue: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return
        
        # Track results
        results = {
            'processed': 0,
            'balanced': 0,
            'discrepancies': 0,
            'errors': 0,
            'discrepancy_details': [],
        }
        
        # Process in batches
        for i, org in enumerate(queryset.iterator(chunk_size=batch_size)):
            try:
                # The check is balance_checker's (one definition): stored numbers against the
                # journal, documents against their applications, ledger echoes against both.
                if rebuild and not dry_run:
                    self.stdout.write(f'  Rebuilt {org.id}: {rebuild_org_ledgers(org)}')
                findings, _ = check_cash(org_id=org.id)
                if not dry_run:
                    update_org_balances(org)
                result = {'balanced': not findings,
                          'discrepancies': [f['message'] for f in findings]}
                
                results['processed'] += 1
                
                if result.get('balanced'):
                    results['balanced'] += 1
                else:
                    results['discrepancies'] += 1
                    if result.get('discrepancies'):
                        results['discrepancy_details'].append({
                            'org_id': str(org.id),
                            'details': result['discrepancies'],
                        })
                
                # Progress update
                if (i + 1) % 50 == 0:
                    self.stdout.write(f'  Processed {i + 1}/{total_count}...')
                
            except Exception as e:
                results['errors'] += 1
                logger.exception(f'Error processing org {org.id}')
                self.stdout.write(self.style.ERROR(f'Error on {org.id}: {e}'))
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Reconciliation Complete ==='))
        self.stdout.write(f'Processed: {results["processed"]}')
        self.stdout.write(f'Balanced:  {results["balanced"]}')
        self.stdout.write(self.style.WARNING(f'Discrepancies: {results["discrepancies"]}'))
        self.stdout.write(self.style.ERROR(f'Errors: {results["errors"]}'))
        
        if results['discrepancy_details']:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Discrepancy Details:'))
            for item in results['discrepancy_details'][:20]:  # Limit output
                self.stdout.write(f'  {item["org_id"]}: {item["details"]}')
            if len(results['discrepancy_details']) > 20:
                self.stdout.write(f'  ... and {len(results["discrepancy_details"]) - 20} more')
