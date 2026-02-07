"""
Management command to fix null values in totals JSON field for all transaction models.
Converts None values to 0 for numeric fields.

Usage:
    python manage.py fix_totals_nulls
    python manage.py fix_totals_nulls --dry-run
"""
import json
from django.core.management.base import BaseCommand
from apps.transactions.models import (
    Order, Invoice, Purchase, Proposal, WorkOrder
)


class Command(BaseCommand):
    help = 'Fix null values in totals JSON field - convert None to 0'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Only models that have the totals field
        models_to_fix = [Order, Invoice, Purchase, Proposal, WorkOrder]
        
        total_fixed = 0
        
        for model in models_to_fix:
            model_name = model.__name__
            self.stdout.write(f"\nProcessing {model_name}...")
            
            fixed_count = 0
            for obj in model.objects.all():
                totals = obj.totals
                
                # Handle string JSON
                if isinstance(totals, str):
                    try:
                        totals = json.loads(totals)
                    except (json.JSONDecodeError, TypeError):
                        totals = {}
                
                if not isinstance(totals, dict):
                    totals = {}
                
                # Check if any values need fixing
                needs_fix = False
                for key in ['subtotal', 'discount', 'taxable', 'tax', 'shipping', 
                           'other', 'total', 'cost', 'margin', 'margin_pc', 
                           'received', 'balance']:
                    if key in totals and totals[key] is None:
                        totals[key] = 0
                        needs_fix = True
                    elif key not in totals:
                        totals[key] = 0
                        needs_fix = True
                
                if needs_fix:
                    fixed_count += 1
                    if not dry_run:
                        obj.totals = totals
                        obj.save(update_fields=['totals'])
                    else:
                        self.stdout.write(f"  Would fix {model_name} id={obj.id}")
            
            total_fixed += fixed_count
            if fixed_count:
                action = "Would fix" if dry_run else "Fixed"
                self.stdout.write(self.style.SUCCESS(f"  {action} {fixed_count} {model_name} records"))
            else:
                self.stdout.write(f"  No changes needed for {model_name}")
        
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would fix {total_fixed} total records"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Fixed {total_fixed} total records"))
