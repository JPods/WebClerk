"""
Load Bill of Material records from bom_children.json.
Maps ItemNum -> component_id (parent assembly), ChildItem -> item_id (component part).

BOM Line semantics:
  - item_id: The component/part item that IS USED in the assembly
  - component_id: The parent assembly that CONTAINS this component
"""
import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.products.models import Item, BillOfMaterial

LOG_FILE = "/Users/williamjames/Documents/CommerceExpert/webClerk3/load_bom.log"


class Command(BaseCommand):
    help = "Load BOM data from bom_children.json, matching items by sku"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without loading'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing BOM records before loading'
        )

    def setup_logging(self):
        self.logger = logging.getLogger('load_bom')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        fh = logging.FileHandler(LOG_FILE, mode='w')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        return self.logger

    def log(self, message, level='info'):
        if level == 'error':
            self.logger.error(message)
            self.stderr.write(self.style.ERROR(message))
        elif level == 'warning':
            self.logger.warning(message)
            self.stdout.write(self.style.WARNING(message))
        elif level == 'success':
            self.logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.logger.info(message)
            self.stdout.write(message)

    def handle(self, *args, **options):
        self.setup_logging()
        
        source_file = "/Users/williamjames/Documents/CommerceExpert/webClerk3/readmes/topics/inventory/bom_children.json"
        dry_run = options['dry_run']
        clear = options['clear']
        
        start_time = datetime.now()
        
        self.log("═" * 65)
        self.log(f"  LOAD BOM STARTED: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"  Source: {source_file}")
        self.log(f"  Log file: {LOG_FILE}")
        self.log("═" * 65)
        self.log("")
        
        # Load JSON
        try:
            with open(source_file, 'r') as f:
                data = json.load(f)
            self.log(f"  Loaded {len(data)} records from JSON")
        except Exception as e:
            self.log(f"  Error reading file: {e}", 'error')
            return
        
        # Build SKU -> Item lookup (case-insensitive)
        self.log("  Building item lookup by SKU...")
        items_by_sku = {}
        for item in Item.objects.all():
            if item.sku:
                items_by_sku[item.sku.upper()] = item
        self.log(f"  Found {len(items_by_sku)} items with SKUs")
        
        if clear and not dry_run:
            deleted, _ = BillOfMaterial.objects.all().delete()
            if deleted:
                self.log(f"  Cleared {deleted} existing BOM records")
        
        created = 0
        updated = 0
        errors = 0
        skipped_parent = []
        skipped_child = []
        
        for record in data:
            item_sku = record.get('ItemNum', '').upper()
            child_sku = record.get('ChildItem', '').upper()
            qty = record.get('QtyInAssembly', 1)
            description = record.get('Description', '')
            uuid_key = record.get('UUIDKey')
            unique_id = record.get('UniqueID')
            plan_cost = record.get('PlanCost', 0)
            plan_ext_cost = record.get('PlanExtCost', 0)
            
            # Lookup parent item
            parent_item = items_by_sku.get(item_sku)
            if not parent_item:
                if item_sku not in skipped_parent:
                    skipped_parent.append(item_sku)
                errors += 1
                continue
            
            # Lookup child/component item
            component_item = items_by_sku.get(child_sku)
            if not component_item:
                if child_sku not in skipped_child:
                    skipped_child.append(child_sku)
                errors += 1
                continue
            
            if dry_run:
                self.log(f"  Would create: {item_sku} -> {child_sku} x{qty}")
                created += 1
                continue
            
            try:
                with transaction.atomic():
                    bom, was_created = BillOfMaterial.objects.update_or_create(
                        item_id=component_item,  # The component/part item in this BOM line
                        component_id=parent_item,  # The parent assembly this line belongs to
                        defaults={
                            'quantity': qty,
                            'description': description,
                            'uuid': uuid_key,
                            'cost_snapshot': plan_cost  # Store plan_cost as decimal
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
            except Exception as e:
                errors += 1
                self.log(f"  Error {item_sku}->{child_sku}: {str(e)[:80]}", 'warning')
        
        # Summary
        self.log("")
        self.log("═" * 65)
        if skipped_parent:
            self.log(f"  Missing parent SKUs: {', '.join(skipped_parent[:10])}", 'warning')
        if skipped_child:
            self.log(f"  Missing child SKUs: {', '.join(skipped_child[:10])}", 'warning')
        
        if dry_run:
            self.log(f"  DRY RUN: Would create {created} BOM records")
        else:
            self.log(f"  COMPLETE: Created {created}, Updated {updated}, Errors {errors}", 'success')
        
        duration = (datetime.now() - start_time).total_seconds()
        self.log(f"  Duration: {duration:.1f}s")
        self.log("═" * 65)
