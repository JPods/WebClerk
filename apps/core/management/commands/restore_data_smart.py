"""
Restore model data from JSON files, ignoring unknown fields.
This handles schema mismatches between backup and current models.
Uses direct ORM operations instead of loaddata to filter unknown fields.
"""
import os
import json
import time
import signal
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction, connection

# Configure logging
LOG_FILE = "/Users/williamjames/Documents/CommerceExpert/webClerk3/restore_data.log"

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out")


class Command(BaseCommand):
    help = "Restore data from JSON backup, ignoring schema mismatches"
    
    # Timeout per record in seconds (if one record takes > this, skip table)
    RECORD_TIMEOUT = 60
    # Timeout for entire table in seconds (3 mins - skip slow tables)
    TABLE_TIMEOUT = 180

    # Load order for FK constraints
    LOAD_ORDER = [
        # Model: (app_label, model_name, json_filename)
        ('accounts', 'Currency', 'currency.json'),
        ('accounts', 'ExchangeRate', 'exchangerate.json'),
        ('core', 'PaymentTerm', 'paymentterm.json'),
        ('core', 'PaymentMethod', 'paymentmethod.json'),
        ('products', 'Warehouse', 'warehouse.json'),
        # ('core', 'Setting', 'setting.json'),  # Skipped - validation issues
        ('core', 'Template', 'template.json'),
        
        # Organizations
        ('orgs', 'OrgBase', 'orgbase.json'),
        
        # Contacts and communication
        ('core', 'Contact', 'contact.json'),
        ('core', 'Action', 'action.json'),
        ('communications', 'Address', 'address.json'),
        ('communications', 'Phone', 'phone.json'),
        ('communications', 'Email', 'email.json'),
        ('communications', 'Domain', 'domain.json'),
        
        # Products
        ('products', 'Catalog', 'catalog.json'),
        ('products', 'Item', 'item.json'),
        ('products', 'BillOfMaterial', 'billofmaterial.json'),
        
        # Documents
        ('docs', 'Document', 'document.json'),
        
        # Transactions - headers
        ('transactions', 'Project', 'project.json'),
        ('transactions', 'Proposal', 'proposal.json'),
        ('transactions', 'Invoice', 'invoice.json'),
        ('transactions', 'Requisition', 'requisition.json'),
        ('transactions', 'WorkOrder', 'workorder.json'),
        ('accounts', 'Payment', 'payment.json'),
        
        # Transaction lines
        ('transactions', 'ProposalLine', 'proposalline.json'),
        ('transactions', 'InvoiceLine', 'invoiceline.json'),
        ('transactions', 'RequisitionLine', 'requisitionline.json'),
        ('transactions', 'WorkOrderLine', 'workorderline.json'),
        ('accounts', 'PaymentApplication', 'paymentapplication.json'),
        
        # Cross-references
        ('core', 'Pending', 'pending.json'),
        ('accounts', 'ExchangeTransaction', 'exchangetransaction.json'),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without loading'
        )
        parser.add_argument(
            '--clear',
            action='store_true', 
            help='Clear existing data before loading (per table)'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Load only a specific file'
        )

    # Field name mappings: old_name -> new_name
    FIELD_MAPPINGS = {
        'dt_end': 'dt_deadline',
        'dt_due': 'dt_deadline',
        'due_by': 'deadline_by',
    }

    def get_model_field_info(self, model):
        """Get valid field names and FK field info for a model."""
        valid_fields = set()
        fk_fields = {}  # field_name -> related model
        
        for f in model._meta.get_fields():
            if hasattr(f, 'column'):
                valid_fields.add(f.name)
                # Track FK fields
                if hasattr(f, 'related_model') and f.related_model:
                    fk_fields[f.name] = f.related_model
            elif f.name == 'id':
                valid_fields.add(f.name)
        
        return valid_fields, fk_fields

    def filter_and_transform(self, data, valid_fields, fk_fields):
        """Filter dict to valid fields and transform FK references."""
        result = {}
        for k, v in data.items():
            # Apply field name mappings
            mapped_key = self.FIELD_MAPPINGS.get(k, k)
            
            if mapped_key in valid_fields:
                result[mapped_key] = v
            # Handle _id suffix for FK fields (old format used field_id)
            elif k.endswith('_id'):
                base = k[:-3]  # Remove _id suffix
                mapped_base = self.FIELD_MAPPINGS.get(base, base)
                if mapped_base in valid_fields and mapped_base in fk_fields:
                    result[mapped_base + '_id'] = v  # Keep as _id for ORM
        return result

    def setup_logging(self):
        """Setup logging to file and console."""
        self.logger = logging.getLogger('restore_data')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # File handler
        fh = logging.FileHandler(LOG_FILE, mode='w')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        
        return self.logger

    def log(self, message, level='info'):
        """Log to file and stdout."""
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
        
        source_dir = "/Users/williamjames/Documents/CommerceExpert/webclerk3_data"
        dry_run = options['dry_run']
        clear = options['clear']
        single_file = options.get('file')
        
        start_time = datetime.now()
        self.log(f"═══════════════════════════════════════════════════════════════")
        self.log(f"  RESTORE DATA STARTED: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"  Source: {source_dir}")
        self.log(f"  Log file: {LOG_FILE}")
        self.log(f"═══════════════════════════════════════════════════════════════")

        if not os.path.exists(source_dir):
            self.stderr.write(f"Backup directory not found: {source_dir}")
            return

        loaded = 0
        skipped = 0
        failed = 0
        total_records = 0

        for app_label, model_name, filename in self.LOAD_ORDER:
            if single_file and filename != single_file:
                continue
            
            table_start = time.time()
            filepath = os.path.join(source_dir, filename)
            
            if not os.path.exists(filepath):
                self.log(f"  ⏭ Skipping {filename} (not found)")
                skipped += 1
                continue

            # Load JSON
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
            except Exception as e:
                self.log(f"  ✗ Error reading {filename}: {e}", 'error')
                skipped += 1
                continue

            if not data or (isinstance(data, list) and len(data) == 0):
                self.log(f"  ⏭ Skipping {filename} (empty)")
                skipped += 1
                continue

            # Get model
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                self.log(f"  ✗ Model {app_label}.{model_name} not found", 'error')
                failed += 1
                continue

            valid_fields, fk_fields = self.get_model_field_info(model)
            record_count = len(data)

            if dry_run:
                self.log(f"  Would load {record_count} records into {app_label}.{model_name}")
                loaded += 1
                total_records += record_count
                continue

            self.log(f"")
            self.log(f"  ┌─ {filename} → {app_label}.{model_name}")
            self.log(f"  │  Records to load: {record_count}")

            # Check if table already has records (skip unless --clear)
            existing_count = model.objects.count()
            if existing_count > 0 and not clear:
                self.log(f"  │  ⏭ Table has {existing_count} existing records - SKIPPING")
                self.log(f"  └─ Use --clear to replace existing data")
                skipped += 1
                continue

            created = 0
            updated = 0
            errors = 0
            error_msgs = []
            timed_out = False
            slow_records = 0

            # Clear if requested
            if clear:
                try:
                    clear_start = time.time()
                    deleted, _ = model.objects.all().delete()
                    clear_time = time.time() - clear_start
                    if deleted:
                        self.log(f"  │  Cleared {deleted} existing records ({clear_time:.1f}s)")
                    if clear_time > 30:
                        self.log(f"  │  ⚠ SLOW: Clear took {clear_time:.1f}s", 'warning')
                except Exception as e:
                    self.log(f"  │  ⚠ Could not clear: {str(e)[:80]}", 'warning')

            for idx, item in enumerate(data):
                # Check table timeout
                elapsed = time.time() - table_start
                if elapsed > self.TABLE_TIMEOUT:
                    self.log(f"  │  ⚠ TABLE TIMEOUT after {elapsed:.1f}s - processed {idx}/{record_count}", 'warning')
                    timed_out = True
                    break
                
                # Handle Django fixture format
                if 'fields' in item and 'pk' in item:
                    pk = item['pk']
                    fields = item['fields']
                else:
                    pk = item.get('id') or item.get('pk')
                    fields = {k: v for k, v in item.items() if k not in ('id', 'pk', 'model')}

                # Filter to valid fields only
                filtered = self.filter_and_transform(fields, valid_fields, fk_fields)

                record_start = time.time()
                try:
                    with transaction.atomic():
                        if pk:
                            obj, was_created = model.objects.update_or_create(
                                pk=pk,
                                defaults=filtered
                            )
                            if was_created:
                                created += 1
                            else:
                                updated += 1
                        else:
                            model.objects.create(**filtered)
                            created += 1
                    
                    record_time = time.time() - record_start
                    if record_time > 5:  # Log slow records
                        slow_records += 1
                        if slow_records <= 3:
                            self.log(f"  │  ⚠ Slow record pk={pk}: {record_time:.1f}s", 'warning')
                        if record_time > self.RECORD_TIMEOUT:
                            self.log(f"  │  ⚠ RECORD TIMEOUT ({record_time:.1f}s) - skipping rest of table", 'warning')
                            timed_out = True
                            break
                            
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        error_msgs.append(str(e)[:100])

            table_time = time.time() - table_start
            
            if timed_out:
                self.log(f"  │  ⚠ SKIPPED (timeout): Created: {created}, Updated: {updated}, Errors: {errors}", 'warning')
                self.log(f"  └─ Time: {table_time:.1f}s (TIMED OUT)")
                failed += 1
            elif errors > 0:
                self.log(f"  │  ⚠ Created: {created}, Updated: {updated}, Errors: {errors}", 'warning')
                for msg in error_msgs:
                    self.log(f"  │    {msg}", 'warning')
                self.log(f"  └─ Time: {table_time:.1f}s")
                loaded += 1
            else:
                self.log(f"  │  ✓ Created: {created}, Updated: {updated}", 'success')
                self.log(f"  └─ Time: {table_time:.1f}s")
                loaded += 1
            
            total_records += created + updated

            # Reset sequence for PostgreSQL
            if created > 0 and connection.vendor == 'postgresql':
                try:
                    table_name = model._meta.db_table
                    with connection.cursor() as cursor:
                        cursor.execute(f"""
                            SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 
                                   COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)
                        """)
                except:
                    pass  # Non-critical

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        self.log(f"")
        self.log(f"═══════════════════════════════════════════════════════════════")
        if dry_run:
            self.log(f"  DRY RUN: {loaded} files, ~{total_records} records would be loaded")
        else:
            self.log(f"  COMPLETE: {loaded} loaded, {skipped} skipped, {failed} failed")
            self.log(f"  Total records: {total_records}")
            self.log(f"  Duration: {duration:.1f}s")
        self.log(f"  Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"═══════════════════════════════════════════════════════════════")
