import os
import sys
import django

sys.path.insert(0, '/Users/williamjames/Documents/CommerceExpert/webClerk3')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.transactions.models import PurchaseLine
from apps.products.models import Item

# Find purchase lines with item_id 231 in the JSON
print('Looking for PurchaseLines with item_id=231:')
for pl in PurchaseLine.objects.all().order_by('-id'):
    item_data = pl.item
    if isinstance(item_data, dict):
        item_id = item_data.get('item_id') or item_data.get('id')
        if item_id == 231:
            print(f'  PL#{pl.id}: purchase={pl.purchase_id}')
            print(f'    item: {item_data}')
            print(f'    quantity: {pl.quantity}')

print()
# Check Item 231 
item = Item.objects.filter(id=231).first()
if item:
    print(f'Item 231: {item.name}')
    for f in ['on_hand', 'on_order', 'available']:
        if hasattr(item, f):
            print(f'  {f}: {getattr(item, f)}')
