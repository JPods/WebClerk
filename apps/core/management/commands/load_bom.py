"""
Load Bill of Material records from bom_children.json.

JSON format (cleaned):
  { parent_id, parent_sku, child_id, child_sku, quantity, child_description, cost_snapshot }

BOM model FK mapping:
  - parent_item_id  (db_column='parent_id')  = parent_id  (the assembly)
  - child_item_id   (db_column='child_id')   = child_id   (the component)
"""
import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.products.models import Item, BillOfMaterial

LOG_FILE = "/Users/williamjames/Documents/CommerceExpert/webClerk3/load_bom.log"


class Command(BaseCommand):
    help = "Load BOM data from bom_children.json (pre-resolved IDs)"

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

        # Validate that referenced Item IDs exist
        all_ids = set()
        for rec in data:
            if rec.get('parent_id'):
                all_ids.add(rec['parent_id'])
            if rec.get('child_id'):
                all_ids.add(rec['child_id'])
        existing_ids = set(Item.objects.filter(id__in=all_ids).values_list('id', flat=True))
        missing = all_ids - existing_ids
        if missing:
            self.log(f"  WARNING: Item IDs not found in DB: {missing}", 'warning')

        if clear and not dry_run:
            deleted, _ = BillOfMaterial.objects.all().delete()
            if deleted:
                self.log(f"  Cleared {deleted} existing BOM records")

        created = 0
        updated = 0
        errors = 0

        for record in data:
            parent_id = record.get('parent_id')
            child_id = record.get('child_id')
            parent_sku = record.get('parent_sku', '')
            child_sku = record.get('child_sku', '')
            qty = record.get('quantity', 1)
            description = record.get('child_description', '')
            cost = record.get('cost_snapshot')

            if not parent_id or not child_id:
                errors += 1
                self.log(f"  SKIP missing ID: parent_sku={parent_sku} child_sku={child_sku}", 'warning')
                continue

            if parent_id not in existing_ids or child_id not in existing_ids:
                errors += 1
                self.log(f"  SKIP bad ID: parent={parent_id} child={child_id}", 'warning')
                continue

            if dry_run:
                self.log(f"  Would create: {parent_sku}({parent_id}) -> {child_sku}({child_id}) x{qty}")
                created += 1
                continue

            try:
                with transaction.atomic():
                    bom, was_created = BillOfMaterial.objects.update_or_create(
                        parent_item_id=parent_id,
                        child_item_id=child_id,
                        defaults={
                            'quantity': qty,
                            'child_description': description,
                            'cost_snapshot': cost,
                        }
                    )
                    if was_created:
                        created += 1
                        self.log(f"  + {parent_sku} -> {child_sku} x{qty}")
                    else:
                        updated += 1
                        self.log(f"  ~ {parent_sku} -> {child_sku} x{qty} (updated)")
            except Exception as e:
                errors += 1
                self.log(f"  Error {parent_sku}->{child_sku}: {str(e)[:120]}", 'warning')

        # Summary
        self.log("")
        self.log("═" * 65)
        if dry_run:
            self.log(f"  DRY RUN: Would create {created} BOM records")
        else:
            self.log(f"  COMPLETE: Created {created}, Updated {updated}, Errors {errors}", 'success')

        duration = (datetime.now() - start_time).total_seconds()
        self.log(f"  Duration: {duration:.1f}s")
        self.log("═" * 65)
