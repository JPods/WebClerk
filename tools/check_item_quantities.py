"""
Check item quantities before/after proposal creation.

Run with: python manage.py shell < tools/check_item_quantities.py
"""

from apps.products.models import Item

print("\n" + "="*70)
print("  ITEM QUANTITY CHECK - Items 248, 249, 250")
print("="*70)

for item_id in [248, 249, 250]:
    try:
        item = Item.objects.get(pk=item_id)
        print(f"\nItem #{item_id} ({item.ida}):")
        print(f"  Name: {item.name}")
        qty = item.quantity_display
        for k, v in qty.items():
            print(f"    {k}: {v}")
    except Item.DoesNotExist:
        print(f"\nItem #{item_id}: NOT FOUND")

print("\n" + "="*70)
