import django, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.transactions.models import PurchaseLine, Purchase
from apps.core.constants.model_registry import get_model

# Simulate saving a new line
line_model = get_model('purchaseline')
fk_field_name = 'purchase'
obj_id = 41  # Purchase ID

# Create new line
line_data = {
    'item': {
        'item_id': 239,
        'ida_item': 'BBPV',
        'description': 'Test line'
    },
    'quantity': {
        'ordered': 9
    },
    'price': {
        'unit': 10,
        'extended': 90
    },
    'cost': {
        'unit': 0
    }
}

line_obj = line_model()
for field, value in line_data.items():
    if field in ('id', 'model_name'):
        continue
    if hasattr(line_obj, field):
        print(f'Setting {field} = {value}')
        setattr(line_obj, field, value)
    else:
        print(f'Field {field} not found on model')

# Set the FK
fk_field = line_model._meta.get_field(fk_field_name)
print(f'Setting FK {fk_field.attname} = {obj_id}')
setattr(line_obj, fk_field.attname, obj_id)

# Save
line_obj.save()
print(f'Saved line ID: {line_obj.id}')
