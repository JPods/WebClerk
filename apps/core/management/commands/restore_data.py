"""
Restore all model data from JSON files in the backup directory.
Uses Django's loaddata with proper ordering for FK constraints.
"""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Restore all model data from /Users/williamjames/Documents/CommerceExpert/webclerk3_data"

    # Load order to satisfy foreign key constraints
    # Earlier items have no/fewer dependencies
    LOAD_ORDER = [
        # 1. Django core - skip these as they're auto-managed
        # 'contenttype.json',
        # 'permission.json',
        # 'group.json',
        
        # 2. Core reference data
        'currency.json',
        'exchangerate.json',
        'paymentterm.json',
        'paymentmethod.json',
        'warehouse.json',
        'tag.json',
        'setting.json',
        'template.json',
        
        # 3. Organizations (unified org model)
        'orgbase.json',
        # Legacy proxy models may not exist as separate files
        # 'customer.json',
        # 'vendor.json', 
        # 'manufacturer.json',
        # 'employee.json',
        # 'rep.json',
        
        # 4. Contacts and communication
        'contact.json',
        'address.json',
        'location.json',
        'phone.json',
        'email.json',
        'domain.json',
        'connection.json',
        
        # 5. Products
        'catalog.json',
        'item.json',
        'variant.json',
        'billofmaterial.json',
        'bundle.json',
        'catalogline.json',
        'itemxref.json',
        'orgitem.json',
        'service.json',
        
        # 6. Inventory
        'siteinventory.json',
        'inventorylayer.json',
        'inventorymovement.json',
        'inventoryreservation.json',
        'inventorycheck.json',
        'inventorycheckline.json',
        'inventorymetricsnapshot.json',
        'pendinginventoryadjustment.json',
        'inventoryadjustmentprocessorrun.json',
        'serial.json',
        'seriallog.json',
        
        # 7. Documents
        'document.json',
        
        # 8. Transactions - headers first
        'project.json',
        'proposal.json',
        'order.json',
        'invoice.json',
        'purchase.json',
        'purchasereceipt.json',
        'requisition.json',
        'workorder.json',
        'deliveryvisit.json',
        'payment.json',
        
        # 9. Transaction lines
        'proposalline.json',
        'orderline.json',
        'invoiceline.json',
        'purchaseline.json',
        'requisitionline.json',
        'workorderline.json',
        'deliveryline.json',
        'paymentapplication.json',
        
        # 10. Cross-references and actions
        'linkage.json',
        'linkageindex.json',
        'action.json',
        'questionanswer.json',
        'pending.json',
        'itemusage.json',
        
        # 11. Exchange/FX
        'exchangetransaction.json',
        
        # 12. Audit/logs (optional - can be large)
        # 'logentry.json',
        # 'softdeleteledger.json',
        # 'session.json',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without actually loading'
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='Continue loading even if individual files fail'
        )
        parser.add_argument(
            '--include-logs',
            action='store_true',
            help='Include log/audit tables (logentry, softdeleteledger, session)'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Load only a specific file (e.g., "item.json")'
        )

    def handle(self, *args, **options):
        source_dir = "/Users/williamjames/Documents/CommerceExpert/webclerk3_data"
        dry_run = options['dry_run']
        skip_errors = options['skip_errors']
        include_logs = options['include_logs']
        single_file = options.get('file')

        if not os.path.exists(source_dir):
            self.stderr.write(f"Backup directory not found: {source_dir}")
            return

        # Build file list
        if single_file:
            files_to_load = [single_file]
        else:
            files_to_load = list(self.LOAD_ORDER)
            
            if include_logs:
                files_to_load.extend([
                    'logentry.json',
                    'softdeleteledger.json', 
                    'session.json',
                ])

        loaded = 0
        skipped = 0
        failed = 0

        for filename in files_to_load:
            filepath = os.path.join(source_dir, filename)
            
            if not os.path.exists(filepath):
                self.stdout.write(f"  Skipping {filename} (not found)")
                skipped += 1
                continue

            # Check if file has content (not just "[]")
            try:
                with open(filepath, 'r') as f:
                    content = f.read().strip()
                    if content in ('[]', ''):
                        self.stdout.write(f"  Skipping {filename} (empty)")
                        skipped += 1
                        continue
            except Exception as e:
                self.stderr.write(f"  Error reading {filename}: {e}")
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  Would load: {filename}")
                loaded += 1
                continue

            try:
                self.stdout.write(f"  Loading {filename}...")
                call_command('loaddata', filepath, verbosity=0)
                self.stdout.write(self.style.SUCCESS(f"    ✓ Loaded {filename}"))
                loaded += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"    ✗ Failed to load {filename}: {e}"))
                failed += 1
                if not skip_errors:
                    self.stderr.write("Stopping due to error. Use --skip-errors to continue.")
                    break

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(f"Dry run complete: {loaded} files would be loaded, {skipped} skipped")
        else:
            self.stdout.write(
                f"Restore complete: {loaded} loaded, {skipped} skipped, {failed} failed"
            )
        
        if failed > 0:
            self.stdout.write(
                self.style.WARNING(
                    "Some files failed to load. Check errors above and consider loading manually."
                )
            )
