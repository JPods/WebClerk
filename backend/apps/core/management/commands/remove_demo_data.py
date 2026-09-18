"""
remove_demo_data — Remove all demo data tagged with refs.source="demo-baseline".

Usage:
    python manage.py remove_demo_data                     # remove demo data
    python manage.py remove_demo_data --dry-run            # show what would be deleted
    python manage.py remove_demo_data --source custom-tag  # remove by custom source tag

Settings are NEVER removed — they are system infrastructure.
Only data records (contacts, orgs, items, transactions, etc.) are deleted.

Uses raw SQL to bypass post_save/post_delete signals that trigger
inventory pending, Alice LLM calls, and other side effects.
Deletion order respects foreign key dependencies (children first).
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.core.services.demo_bundle import demo_tables_children_first


# Demo-data tables come from apps/core/services/demo_bundle.py (one source of truth).
# Records are tagged refs.source=<tag> (uuid-remap loader) or refs.demo_source=<tag>
# (preserve-ids loader, which keeps refs.source lineage intact on transaction lines).
TAG_MATCH = "(refs->>'source' = %s OR refs->>'demo_source' = %s)"

# Tables referencing demo records via FK (not directly tagged).
# Delete these by FK reference before deleting their parents.
# Order matters: delete deepest dependents first.
FK_CLEANUP = [
    # Invoice dependents
    ('ledger', 'invoice_id', 'invoices'),
    # Org dependents (ledger also refs orgs)
    ('ledger', 'org_id', 'orgs_orgbase'),
    ('erosion', 'org_id', 'orgs_orgbase'),
    # Contact dependents
    ('emails', 'contact_id', 'contacts'),
    ('phones', 'contact_id', 'contacts'),
    ('domains', 'contact_id', 'contacts'),
    ('locations', 'contact_id', 'contacts'),
    ('touches', 'contact_id', 'contacts'),
    ('statement_lines', 'contact_id', 'contacts'),
    ('alice_observations', 'contact_id', 'contacts'),
    ('alice_coaching_log', 'contact_id', 'contacts'),
    ('erosion', 'contact_id', 'contacts'),
    # Item dependents
    ('products_itemxref', 'item_id', 'products_item'),
    ('products_inventorylayer', 'item_id', 'products_item'),
    ('products_siteinventory', 'item_id', 'products_item'),
    ('products_inventorymovement', 'item_id', 'products_item'),
    ('products_inventoryreservation', 'item_id', 'products_item'),
    ('products_serial', 'item_id', 'products_item'),
    ('products_catalogline', 'item_id', 'products_item'),
    ('products_itemusage', 'item_id', 'products_item'),
    ('products_service', 'item_id', 'products_item'),
    ('products_variant', 'item_id', 'products_item'),
    ('products_specification', 'item_id', 'products_item'),
]


class Command(BaseCommand):
    help = 'Remove all demo data tagged with refs.source="demo-baseline"'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be deleted without deleting')
        parser.add_argument('--source', type=str, default='demo-baseline',
                            help='Value of refs.source to match (default: demo-baseline)')
        parser.add_argument('--json', action='store_true',
                            help='Output results as JSON')

    def handle(self, *args, **options):
        source = options['source']
        dry_run = options['dry_run']
        results = {}
        total = 0
        cursor = connection.cursor()

        def table_exists(name):
            cursor.execute("SELECT to_regclass(%s)", [name])
            return cursor.fetchone()[0] is not None

        with transaction.atomic():
            # First, clean up FK-referenced records that aren't directly tagged.
            for child_table, fk_col, parent_table in FK_CLEANUP:
                if not (table_exists(child_table) and table_exists(parent_table)):
                    continue
                where = f"{fk_col} IN (SELECT id FROM {parent_table} WHERE {TAG_MATCH})"
                cursor.execute(f"SELECT COUNT(*) FROM {child_table} WHERE {where}", [source, source])
                count = cursor.fetchone()[0]
                if not dry_run and count > 0:
                    cursor.execute(f"DELETE FROM {child_table} WHERE {where}", [source, source])
                if count > 0:
                    action = "would delete" if dry_run else "deleted"
                    self.stdout.write(f"  {child_table}: {action} {count} (FK cleanup)")
                    total += count

            # Then delete directly tagged records, children first
            for table in demo_tables_children_first():
                if not table_exists(table):
                    continue
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {TAG_MATCH}", [source, source])
                count = cursor.fetchone()[0]
                if not dry_run and count > 0:
                    cursor.execute(f"DELETE FROM {table} WHERE {TAG_MATCH}", [source, source])
                results[table] = count
                total += count
                if count > 0:
                    action = "would delete" if dry_run else "deleted"
                    self.stdout.write(f"  {table}: {action} {count}")

        if options.get('json'):
            import json
            self.stdout.write(json.dumps({
                'action': 'dry_run' if dry_run else 'deleted',
                'source': source,
                'counts': results,
                'total': total,
            }, indent=2))
        else:
            action = "Would delete" if dry_run else "Deleted"
            style = self.style.WARNING if dry_run else self.style.SUCCESS
            self.stdout.write(style(
                f"\n{action} {total} demo records (source={source})"
            ))
            self.stdout.write("\nSettings were NOT touched (they are system infrastructure).")
