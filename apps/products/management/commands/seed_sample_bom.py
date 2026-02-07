"""
Management command to seed sample BOM data for testing.

Clears existing BillOfMaterial records and inserts baseball equipment kit test data.
"""
from __future__ import annotations

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Item
from apps.products.models.bill_of_material import BillOfMaterial


# BOM parent items with BomHasChild=True
BOM_PARENTS = [
    {"sku": "BB110", "description": "Little League Baseballs, Box of 10 dozen", "bom_has_parent": True},
    {"sku": "BB401", "description": "WS Baseball Starter Inventory", "bom_has_parent": False},
    {"sku": "bb401_2", "description": "WS Baseball Starter Inventory", "bom_has_parent": False},
    {"sku": "BB404", "description": "WS Baseball Starter Inventory", "bom_has_parent": False},
]

# Child items needed for BOM relationships
BOM_CHILD_ITEMS = [
    {"sku": "BB1", "description": "All-Star BB1 Bat Carry Bag/Rack"},
    {"sku": "BB100", "description": "Fielders Glove-Wilson, G. Brut"},
    {"sku": "BB101", "description": "Little League Bat"},
    {"sku": "BB102", "description": "Batting Glove, Saranac, this-that"},
    {"sku": "BB103", "description": "Batting Glove-Wilson"},
    {"sku": "BB105", "description": "Little League Baseballs"},
    {"sku": "BB405", "description": "WS Baseball Starter Inventory"},
]

# BOM children relationships from bom_children.json
BOM_CHILDREN = [
    {"parent": "BB404", "child": "BB102", "qty": 2, "plan_cost": "4.9684", "description": "Batting Glove, Saranac, this-that"},
    {"parent": "BB404", "child": "BB101", "qty": 1, "plan_cost": "8.1349", "description": "Little League Bat"},
    {"parent": "BB404", "child": "BB103", "qty": 1, "plan_cost": "6.24", "description": "Batting Glove-Wilson"},
    {"parent": "BB404", "child": "BB110", "qty": 1, "plan_cost": "40", "description": "Little League Baseballs, Box of 10 dozen"},
    {"parent": "BB110", "child": "BB105", "qty": 10, "plan_cost": "3.2701", "description": "Little League Baseballs"},
    {"parent": "BB401", "child": "BB1", "qty": 5, "plan_cost": "0", "description": "All-Star BB1 Bat Carry Bag/Rack"},
    {"parent": "BB401", "child": "BB105", "qty": 7, "plan_cost": "3.2701", "description": "Little League Baseballs"},
    {"parent": "BB401", "child": "BB103", "qty": 10, "plan_cost": "2.22", "description": "Batting Glove-Wilson"},
    {"parent": "BB401", "child": "BB102", "qty": 1, "plan_cost": "4.9628", "description": "Batting Glove, Saranac, this-that"},
    {"parent": "BB401", "child": "BB101", "qty": 11, "plan_cost": "7.7796", "description": "Little League Bat"},
    {"parent": "BB401", "child": "BB100", "qty": 1, "plan_cost": "10", "description": "Fielders Glove-Wilson, G. Brut"},
    {"parent": "BB401", "child": "BB110", "qty": 1, "plan_cost": "40", "description": "Little League Baseballs, Box of 10 dozen"},
    {"parent": "BB401", "child": "BB405", "qty": 6, "plan_cost": "345.6", "description": "WS Baseball Starter Inventory"},
    {"parent": "bb401_2", "child": "BB1", "qty": 5, "plan_cost": "0", "description": "All-Star BB1 Bat Carry Bag/Rack"},
    {"parent": "bb401_2", "child": "BB105", "qty": 7, "plan_cost": "3.2701", "description": "Little League Baseballs"},
    {"parent": "bb401_2", "child": "BB103", "qty": 10, "plan_cost": "2.22", "description": "Batting Glove-Wilson"},
    {"parent": "bb401_2", "child": "BB102", "qty": 1, "plan_cost": "4.9628", "description": "Batting Glove, Saranac, this-that"},
    {"parent": "bb401_2", "child": "BB101", "qty": 11, "plan_cost": "7.7796", "description": "Little League Bat"},
    {"parent": "bb401_2", "child": "BB100", "qty": 1, "plan_cost": "10", "description": "Fielders Glove-Wilson, G. Brut"},
    {"parent": "bb401_2", "child": "BB110", "qty": 1, "plan_cost": "40", "description": "Little League Baseballs, Box of 10 dozen"},
]


class Command(BaseCommand):
    help = "Clear existing BOM data and seed sample baseball equipment kit test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        with transaction.atomic():
            # 1. Delete existing BOM data
            existing_count = BillOfMaterial.objects.count()
            if not dry_run:
                BillOfMaterial.objects.all().delete()
            self.stdout.write(f"Deleted {existing_count} existing BOM records")

            # 2. Create/ensure parent and child items exist
            all_items = BOM_PARENTS + BOM_CHILD_ITEMS
            items_created = 0
            for item_data in all_items:
                item, created = Item.objects.get_or_create(
                    sku=item_data["sku"],
                    defaults={"description": item_data["description"], "name": item_data["description"]},
                )
                if created:
                    items_created += 1
                    if not dry_run:
                        self.stdout.write(f"  Created item: {item.sku}")

            self.stdout.write(f"Ensured {len(all_items)} items exist ({items_created} created)")

            # 3. Build item lookup
            item_lookup = {item.sku.lower(): item for item in Item.objects.filter(
                sku__in=[i["sku"] for i in all_items]
            )}

            # 4. Create BOM relationships
            bom_created = 0
            for bom_data in BOM_CHILDREN:
                parent_item = item_lookup.get(bom_data["parent"].lower())
                child_item = item_lookup.get(bom_data["child"].lower())

                if not parent_item:
                    self.stdout.write(self.style.WARNING(f"  Parent not found: {bom_data['parent']}"))
                    continue
                if not child_item:
                    self.stdout.write(self.style.WARNING(f"  Child not found: {bom_data['child']}"))
                    continue

                if not dry_run:
                    BillOfMaterial.objects.create(
                        item_id=parent_item,
                        component_id=child_item,
                        quantity=Decimal(str(bom_data["qty"])),
                        cost_snapshot=Decimal(bom_data["plan_cost"]),
                        description=bom_data["description"],
                        sequence=bom_created,
                    )
                bom_created += 1
                self.stdout.write(f"  BOM: {bom_data['parent']} -> {bom_data['child']} x {bom_data['qty']}")

            self.stdout.write(self.style.SUCCESS(f"\nCreated {bom_created} BOM relationships"))

            # 5. Summary
            self.stdout.write("\n--- BOM Structure ---")
            for parent in ["BB401", "bb401_2", "BB404", "BB110"]:
                children = [b for b in BOM_CHILDREN if b["parent"] == parent]
                if children:
                    self.stdout.write(f"\n{parent}:")
                    for c in children:
                        self.stdout.write(f"  └── {c['child']} x {c['qty']} ({c['description'][:30]}...)")

            if dry_run:
                self.stdout.write(self.style.WARNING("\nDRY RUN complete - rolling back"))
                raise transaction.TransactionManagement("Dry run rollback")
