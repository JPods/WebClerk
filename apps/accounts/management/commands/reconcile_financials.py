"""
Management command for nightly financial reconciliation.

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
            '--update-ytd',
            action='store_true',
            help='Also update YTD sales/purchases aggregates',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of orgs to process per batch (default: 100)',
        )

    def handle(self, *args, **options):
        from django.apps import apps as dj_apps
        from apps.accounts.services.ledger_balance import (
            reconcile_org,
            rebuild_org_ledgers,
            update_org_balances,
        )
        
        OrgBase = dj_apps.get_model('orgs', 'OrgBase')
        
        org_id = options.get('org_id')
        org_type = options.get('org_type')
        rebuild = options.get('rebuild')
        dry_run = options.get('dry_run')
        update_ytd = options.get('update_ytd')
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
                if dry_run:
                    # Just check without saving
                    result = self._check_org(org)
                elif rebuild:
                    result = rebuild_org_ledgers(org)
                    self.stdout.write(f'  Rebuilt {org.id}: {result}')
                    result = reconcile_org(org)
                else:
                    result = reconcile_org(org)
                
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
        
        # Update YTD if requested (batch operation)
        if update_ytd and not dry_run:
            self.stdout.write('Updating YTD aggregates...')
            self._update_ytd_sales(queryset)
        
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

    def _check_org(self, org):
        """Check an org's balances without making changes."""
        from django.apps import apps as dj_apps
        from django.db import models
        from decimal import Decimal
        
        Ledger = dj_apps.get_model('accounts', 'Ledger')
        Invoice = dj_apps.get_model('transactions', 'Invoice')
        Payment = dj_apps.get_model('transactions', 'Payment')
        
        org_id = str(org.id)
        
        # This is a simplified check - actual implementation may vary
        # based on how orgs are linked to ledgers
        ledger_sum = Decimal('0')
        invoice_sum = Decimal('0')
        payment_sum = Decimal('0')
        
        try:
            # Try to get ledger sum
            ledger_qs = Ledger.objects.filter(invoice_id__org_id=org_id)
            ledger_sum = ledger_qs.aggregate(total=models.Sum('value_available'))['total'] or Decimal('0')
        except Exception:
            pass
        
        try:
            # Get invoice balance sum
            invoice_qs = Invoice.objects.filter(org_id=org_id)
            # This depends on how balance_due is stored
            for inv in invoice_qs:
                total_data = getattr(inv, 'total', {}) or {}
                bal = total_data.get('balance_due', 0) if isinstance(total_data, dict) else 0
                invoice_sum += Decimal(str(bal))
        except Exception:
            pass
        
        try:
            # Get payment available sum
            payment_qs = Payment.objects.filter(org_id=org_id)
            payment_sum = payment_qs.aggregate(total=models.Sum('amount_available'))['total'] or Decimal('0')
        except Exception:
            pass
        
        expected = invoice_sum - payment_sum
        balanced = (ledger_sum == expected)
        
        return {
            'balanced': balanced,
            'ledger_sum': ledger_sum,
            'invoice_sum': invoice_sum,
            'payment_sum': payment_sum,
            'discrepancies': [] if balanced else [{
                'type': 'balance_mismatch',
                'deviation': float(ledger_sum - expected),
            }],
        }

    def _update_ytd_sales(self, org_queryset):
        """Update YTD sales/purchases for orgs (batch operation)."""
        from django.apps import apps as dj_apps
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        from datetime import date
        
        Invoice = dj_apps.get_model('transactions', 'Invoice')
        
        year_start = date(date.today().year, 1, 1)
        
        for org in org_queryset.iterator():
            try:
                # Calculate YTD sales from invoices
                ytd_total = Invoice.objects.filter(
                    org_id=org.id,
                    dt_created__gte=year_start,
                ).aggregate(
                    total=Coalesce(Sum('total__total'), Decimal('0'))
                )['total']
                
                # Update financial JSON
                financial = org.financial or {}
                org_type = getattr(org, 'org_type', 'customer')
                
                if org_type == 'customer':
                    customer = financial.get('customer', {})
                    sales = customer.get('sales', {})
                    sales['ytd'] = float(ytd_total)
                    customer['sales'] = sales
                    financial['customer'] = customer
                elif org_type == 'vendor':
                    vendor = financial.get('vendor', {})
                    purchases = vendor.get('purchases', {})
                    purchases['ytd'] = float(ytd_total)
                    vendor['purchases'] = purchases
                    financial['vendor'] = vendor
                
                org.financial = financial
                org.save(update_fields=['financial'])
                
            except Exception as e:
                logger.warning(f'Error updating YTD for {org.id}: {e}')
