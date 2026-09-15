import django, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.products.models import Item
from apps.core.models import Pending

item = Item.objects.get(pk=239)
print(f"Item 239: {item.ida} - {item.name}")
print(f"Quantity: {item.quantity}")
print()
print("Pending for item 239:")
for p in Pending.objects.filter(item_id=239).order_by('-id')[:10]:
    print(f"  #{p.id} {p.pending_type} delta={p.delta} status={p.status}")
if not Pending.objects.filter(item_id=239).exists():
    print("  (none)")
