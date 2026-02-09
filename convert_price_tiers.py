#!/usr/bin/env python
"""
Temporary script to convert Item price.tiers to flat fields.
Run once then delete this file.

Usage: python convert_price_tiers.py
"""
import json
import os
import sys

sys.path.insert(0, '/Users/williamjames/Documents/CommerceExpert/webClerk3')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

import django
django.setup()

from django.conf import settings
import psycopg2

# Get DB config from Django settings
db = settings.DATABASES['default']
DB_CONFIG = {
    "host": db['HOST'],
    "port": db['PORT'],
    "dbname": db['NAME'],
    "user": db['USER'],
    "password": db['PASSWORD'],
}

TIER_MAP = {"B": "wholesale", "C": "distributor", "D": "sample"}


def convert_price_tiers_to_flat(price: dict) -> dict:
    """Remove tiers, add flat price fields based on base price, ordered."""
    base = price.get("base")
    
    # Build result in exact order: base, msrp, wholesale, distributor, sample, history, currency, qty_breaks
    result = {}
    result["base"] = base
    result["msrp"] = base if base is not None else price.get("msrp")
    result["wholesale"] = round(base * 0.85, 2) if base is not None else price.get("wholesale")
    result["distributor"] = round(base * 0.80, 2) if base is not None else price.get("distributor")
    result["sample"] = round(base * 0.70, 2) if base is not None else price.get("sample")
    result["history"] = price.get("history", [])
    result["currency"] = price.get("currency", "USD")
    result["qty_breaks"] = price.get("qty_breaks", [])
    
    return result


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Get items that have wholesale (already converted) to reorder
    cur.execute("""
        SELECT id, price FROM products_item 
        WHERE price -> 'wholesale' IS NOT NULL
    """)
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} items to reorder")
    
    updated = 0
    for item_id, price in rows:
        if isinstance(price, dict):
            new_price = convert_price_tiers_to_flat(price)
            cur.execute(
                "UPDATE products_item SET price = %s WHERE id = %s",
                [json.dumps(new_price), item_id]
            )
            updated += 1
            print(f"Item {item_id}: wholesale={new_price.get('wholesale')}, distributor={new_price.get('distributor')}, sample={new_price.get('sample')}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\nDone. Updated {updated} items.")


if __name__ == "__main__":
    main()
