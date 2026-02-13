import json
from django.core.management.base import BaseCommand
from apps.products.models.bill_of_material import BillOfMaterial
from apps.products.models.item import Item

class Command(BaseCommand):
    help = 'Load BillOfMaterial records from JSON files'

    def add_arguments(self, parser):
        parser.add_argument('--bom', type=str, required=True, help='Path to bom_children.json')
        parser.add_argument('--parent', type=str, required=True, help='Path to bom_parent.json')

    def handle(self, *args, **options):
        bom_path = options['bom']
        parent_path = options['parent']

        with open(bom_path, 'r') as f:
            bom_records = json.load(f)
        with open(parent_path, 'r') as f:
            parent_records = json.load(f)

        # Build ItemNum to Item.id lookup
        itemnum_to_id = {}
        for item in Item.objects.all():
            itemnum_to_id[item.sku] = item.id  # Assuming SKU is ItemNum

        created = 0
        for record in bom_records:
            parent_itemnum = record['ItemNum']
            child_itemnum = record['ChildItem']
            parent_id = itemnum_to_id.get(parent_itemnum)
            child_id = itemnum_to_id.get(child_itemnum)
            if not parent_id or not child_id:
                self.stdout.write(self.style.WARNING(f"Missing ItemNum mapping: parent {parent_itemnum}, child {child_itemnum}"))
                continue
            bom_data = {
                'parent_id': parent_id,
                'child_id': child_id,
                'quantity': record.get('QtyInAssembly', 1),
                'parent_name': record.get('Description', ''),
                'change_reason': record.get('Comment', ''),
                'cost_snapshot': record.get('PlanCost', None),
            }
            try:
                BillOfMaterial.objects.create(**bom_data)
                created += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating BOM: {e}"))
        self.stdout.write(self.style.SUCCESS(f"Created {created} BillOfMaterial records."))
