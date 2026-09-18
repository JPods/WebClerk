#!/usr/bin/env python
import os
import sys
import json
import django

# Add the project directory to the Python path
sys.path.insert(0, '/Users/williamjames/Documents/CommerceExpert/webClerk3')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

# Setup Django
django.setup()

from apps.transactions.models import Order

def serialize_order(order):
    """Serialize an Order instance to a dict matching the model structure."""
    data = {
        # From TransactionBaseModel
        'id': order.id,
        'status': order.status,
        'priority': order.priority,
        'price_level': order.price_level,
        'customer_id': order.customer_id,
        'manufacturer_id': order.manufacturer_id,
        'vendor_id': order.vendor_id,
        'parent_id': order.parent_id,
        'parent_type': order.parent_type,
        'cost': order.cost or {},
        'sell': order.sell or {},
        'totals': order.totals or {},
        'finance': order.finance or {},
        'flow': order.flow or {},
        'source': order.source or {},
        'action': order.action or {},
        # From BaseModel (assuming common fields)
        'dt_created': order.dt_created.isoformat() if order.dt_created else None,
        'dt_modified': order.dt_modified.isoformat() if order.dt_modified else None,
        'version': order.version,
        'is_active': order.is_active,
        'is_deleted': order.is_deleted,
        'is_archived': order.is_archived,
        'metadata': getattr(order, 'metadata', {}) or {},
        'refs': getattr(order, 'refs', {}) or {},
        'prefs': getattr(order, 'prefs', {}) or {},
        # Lines
        'lines': []
    }

    # Serialize lines
    for line in order.lines.all():
        line_data = {
            'id': line.id,
            # 'order_id': line.order_id_id,  # Legacy support removed for consistency
            'price_level': line.price_level,
            'status': line.status,
            'item': line.item or {},
            'quantity': line.quantity or {},
            'cost': line.cost or {},
            'tax': line.tax or {},
            'physical': line.physical or {},
            'price': line.price or {},
            # From BaseModel
            'dt_created': line.dt_created.isoformat() if line.dt_created else None,
            'dt_modified': line.dt_modified.isoformat() if line.dt_modified else None,
            'version': line.version,
            'is_active': line.is_active,
            'is_deleted': line.is_deleted,
            'is_archived': line.is_archived,
            'metadata': getattr(line, 'metadata', {}) or {},
            'refs': getattr(line, 'refs', {}) or {},
            'prefs': getattr(line, 'prefs', {}) or {},
        }
        data['lines'].append(line_data)

    return data

def main():
    try:
        order = Order.objects.get(pk=22)
        serialized = serialize_order(order)
        print(json.dumps(serialized, indent=2))
    except Order.DoesNotExist:
        print(json.dumps({"error": "Order with id 22 does not exist"}, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))

if __name__ == '__main__':
    main()