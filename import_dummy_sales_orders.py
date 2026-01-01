#!/usr/bin/env python
"""
Script to import 5 dummy sales orders based on the sample_sales_order.json structure.
This script creates dummy sales orders with variations in items, quantities, and customer IDs.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from decimal import Decimal

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk.settings')  # Adjust if settings module name differs
import django
django.setup()

from apps.transactions.models import SalesOrder, SalesOrderLine

def load_sample_json():
    """Load the sample sales order JSON."""
    with open('sample_sales_order.json', 'r') as f:
        return json.load(f)

def generate_dummy_sales_order(base_data, index):
    """Generate a dummy sales order with variations."""
    # Deep copy the base data
    data = json.loads(json.dumps(base_data))

    # Modify fields for uniqueness
    data['id'] = None  # Let Django assign
    data['ida'] = f"dummy-so-{index}"
    data['uuid'] = str(uuid.uuid4())
    data['customer_id'] = 1000 + index
    data['dt_created'] = int(datetime.now().timestamp() * 1000)
    data['dt_modified'] = data['dt_created']
    data['version'] = 1

    # Modify metadata history
    data['metadata']['history']['created']['dt'] = data['dt_created']
    data['metadata']['history']['accessed']['dt'] = data['dt_created']
    data['metadata']['history']['modified']['dt'] = data['dt_created']

    # Modify lines
    for i, line in enumerate(data['lines']):
        line['id'] = None
        line['salesorder_id'] = None  # Will be set after creation
        line['ida'] = f"dummy-line-{index}-{i+1}"
        line['uuid'] = str(uuid.uuid4())
        line['dt_created'] = data['dt_created'] + i * 1000
        line['dt_modified'] = line['dt_created']
        line['version'] = 1

        # Modify metadata for line
        line['metadata']['history']['created']['dt'] = line['dt_created']
        line['metadata']['history']['accessed']['dt'] = line['dt_created']
        line['metadata']['history']['modified']['dt'] = line['dt_created']

        # Vary quantities and prices slightly
        multiplier = 1 + (index - 1) * 0.1  # 1.0, 1.1, 1.2, etc.
        line['quantity']['placed'] = int(line['quantity']['placed'] * multiplier)
        line['quantity']['remaining'] = line['quantity']['placed']
        line['price']['unit'] = round(Decimal(str(line['price']['unit'])) * Decimal(str(multiplier)), 2)
        line['price']['extended'] = round(Decimal(str(line['price']['unit'])) * Decimal(str(line['quantity']['placed'])), 2)
        line['cost']['unit'] = round(Decimal(str(line['cost']['unit'])) * Decimal(str(multiplier)), 2)
        line['cost']['extended'] = round(Decimal(str(line['cost']['unit'])) * Decimal(str(line['quantity']['placed'])), 2)

    # Recalculate totals
    subtotal = sum(Decimal(str(line['price']['extended'])) for line in data['lines'])
    cost_total = sum(Decimal(str(line['cost']['extended'])) for line in data['lines'])
    data['totals']['subtotal'] = float(subtotal)
    data['totals']['taxable'] = float(subtotal)
    data['totals']['total'] = float(subtotal)
    data['totals']['cost'] = float(cost_total)
    data['totals']['margin'] = float(subtotal - cost_total)
    if subtotal > 0:
        data['totals']['margin_pc'] = round(float((subtotal - cost_total) / subtotal * 100), 2)
    data['cost']['total'] = float(cost_total)
    data['cost']['line_sum_goods'] = float(cost_total)

    return data

def create_sales_order_from_data(data):
    """Create SalesOrder and SalesOrderLine instances from data dict."""
    # Extract lines data
    lines_data = data.pop('lines', [])

    # Create SalesOrder
    sales_order = SalesOrder(**data)
    sales_order.save()

    # Create lines
    for line_data in lines_data:
        line_data['salesorder_id'] = sales_order
        line = SalesOrderLine(**line_data)
        line.save()

    return sales_order

def main():
    """Main function to import 5 dummy sales orders."""
    print("Loading sample sales order JSON...")
    base_data = load_sample_json()

    print("Creating 5 dummy sales orders...")
    for i in range(1, 6):
        print(f"Creating dummy sales order {i}...")
        dummy_data = generate_dummy_sales_order(base_data, i)
        sales_order = create_sales_order_from_data(dummy_data)
        print(f"Created SalesOrder ID: {sales_order.id}, IDA: {sales_order.ida}")

    print("All dummy sales orders imported successfully!")

if __name__ == '__main__':
    main()