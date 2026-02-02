#!/usr/bin/env python
"""
Monitor pending inventory records for item 259.
Tracks creation and application timing.

Run this BEFORE adding items in the frontend, then watch the output.
Usage: python monitor_pending.py
"""
import django
import os
import time
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

from apps.products.models import Item
from apps.core.models import Pending
from django.utils import timezone

ITEM_ID = 259
POLL_INTERVAL = 2  # seconds


def get_item_quantity():
    """Get current item quantity snapshot."""
    item = Item.objects.get(pk=ITEM_ID)
    return item.quantity or {}


def get_pending_records():
    """Get all pending records for item 259."""
    return Pending.objects.filter(
        model_name='item',
        record_id=str(ITEM_ID),
    ).order_by('-dt_created')


def format_pending(p):
    """Format a pending record for display."""
    data = p.data or {}
    return {
        'id': p.pk,
        'purpose': p.purpose,
        'type_id': data.get('type_id', '??'),
        'qty_on_so': data.get('on_so', 0),
        'qty_on_po': data.get('on_po', 0),
        'qty_on_p': data.get('on_p', 0),
        'qty_on_in': data.get('on_in', 0),
        'doc_id': data.get('doc_id', ''),
        'line_id': data.get('line_id', ''),
        'created_at': p.dt_created,
        'dt_processed': p.dt_processed,
        'is_processed': p.dt_processed and p.dt_processed > 0,
    }


def main():
    print('=' * 70)
    print(f'MONITORING PENDING RECORDS FOR ITEM {ITEM_ID}')
    print(f'Started at: {datetime.now().isoformat()}')
    print('=' * 70)
    
    # Initial state
    print('\n--- INITIAL ITEM QUANTITY ---')
    qty = get_item_quantity()
    for k, v in sorted(qty.items()):
        print(f'  {k}: {v}')
    
    # Get baseline pending count
    existing_pending = set(p.pk for p in get_pending_records())
    print(f'\n--- EXISTING PENDING RECORDS: {len(existing_pending)} ---')
    
    # Track new pending records and their timing
    seen_pending = {}  # {pk: {'created': time, 'processed': time}}
    
    print('\n--- WAITING FOR NEW PENDING RECORDS ---')
    print('(Add items to proposal, order, invoice, purchase in frontend...)')
    print('Press Ctrl+C to stop monitoring\n')
    
    try:
        while True:
            # Check for new pending records
            current_pending = get_pending_records()
            
            for p in current_pending:
                if p.pk not in existing_pending:
                    fp = format_pending(p)
                    
                    if p.pk not in seen_pending:
                        # New pending record discovered
                        seen_pending[p.pk] = {
                            'created_time': time.time(),
                            'processed_time': None,
                            'info': fp,
                        }
                        print(f'\n🆕 NEW PENDING #{p.pk}:')
                        print(f'   Purpose: {fp["purpose"]}')
                        print(f'   Type: {fp["type_id"]}')
                        print(f'   on_so: {fp["qty_on_so"]}, on_po: {fp["qty_on_po"]}, on_p: {fp["qty_on_p"]}, on_in: {fp["qty_on_in"]}')
                        print(f'   Doc: {fp["doc_id"]}, Line: {fp["line_id"]}')
                        print(f'   Created: {fp["created_at"]}')
                    
                    elif fp['is_processed'] and seen_pending[p.pk]['processed_time'] is None:
                        # Just got processed
                        seen_pending[p.pk]['processed_time'] = time.time()
                        elapsed = seen_pending[p.pk]['processed_time'] - seen_pending[p.pk]['created_time']
                        print(f'\n✅ PROCESSED #{p.pk}: {elapsed:.2f}s after creation')
            
            # Print current item quantity periodically
            qty = get_item_quantity()
            ts = datetime.now().strftime('%H:%M:%S')
            
            # Summarize current state
            new_count = len(seen_pending)
            processed_count = sum(1 for s in seen_pending.values() if s['processed_time'])
            
            print(f'\r[{ts}] Pending: {new_count} new ({processed_count} processed) | '
                  f'on_so={qty.get("on_so", 0)} on_po={qty.get("on_po", 0)} on_p={qty.get("on_p", 0)} '
                  f'on_hand={qty.get("on_hand", 0)}', end='', flush=True)
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print('\n\n--- MONITORING STOPPED ---')
    
    # Final summary
    print('\n' + '=' * 70)
    print('FINAL SUMMARY')
    print('=' * 70)
    
    print('\n--- FINAL ITEM QUANTITY ---')
    qty = get_item_quantity()
    for k, v in sorted(qty.items()):
        print(f'  {k}: {v}')
    
    print(f'\n--- PENDING RECORDS TRACKED: {len(seen_pending)} ---')
    for pk, info in sorted(seen_pending.items()):
        fp = info['info']
        status = '✅' if info['processed_time'] else '⏳'
        elapsed = ''
        if info['processed_time']:
            elapsed = f" ({info['processed_time'] - info['created_time']:.2f}s)"
        print(f'  {status} #{pk}: {fp["type_id"]} {fp["purpose"]}{elapsed}')


if __name__ == '__main__':
    main()
