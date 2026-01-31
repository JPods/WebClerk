#!/usr/bin/env python
"""
Inventory Testing Tool for Item 240

Tracks item.quantity fields:
  - on_hand:    Physical inventory on hand
  - allocated:  Reserved/committed for orders
  - available:  on_hand - allocated
  - on_so:      On Sales Order (pending orders)
  - on_po:      On Purchase Order (incoming)
  - on_p:       On Proposal (quotes)
  - on_r:       On Receipt (informational - tracks qty received)
  - on_in:      On Invoice (informational - tracks qty invoiced)
  - on_wo:      On Work Order (manufacturing)

INVENTORY FLOW:
  1. Create Order/Purchase/Proposal → Creates Pending record
  2. Run 'process_pending' → Pending records update item.quantity buckets
  3. Confirm/Invoice → Further updates to quantities

Usage:
    python tools/inventory_tester.py baseline            # Capture baseline
    python tools/inventory_tester.py status              # Show current status
    python tools/inventory_tester.py create order 5      # Create order with qty 5
    python tools/inventory_tester.py create purchase 10  # Create purchase with qty 10
    python tools/inventory_tester.py create proposal 3   # Create proposal with qty 3
    python tools/inventory_tester.py create invoice 3    # Create invoice with qty 3
    python tools/inventory_tester.py create workorder 3  # Create workorder with qty 3
    python tools/inventory_tester.py create receipt 3    # Create receipt with qty 3 (receives goods)
    python tools/inventory_tester.py process_pending     # Process pending → update item quantities
    python tools/inventory_tester.py log "Test note"     # Add log entry with snapshot
    python tools/inventory_tester.py history             # Show all logged events
    python tools/inventory_tester.py pending             # Show pending records for item
    python tools/inventory_tester.py reset               # Clear today's log files

Log files are saved per day:
    logs/inventory_tests/item_240_YYYY-MM-DD.json
    logs/inventory_tests/item_240_YYYY-MM-DD.log
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from decimal import Decimal

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

import django
django.setup()

from django.db import transaction

# Item to track
ITEM_ID = 240
LOG_DIR = PROJECT_ROOT / 'logs' / 'inventory_tests'

# All quantity keys we track from item.quantity JSON field
QUANTITY_KEYS = ['on_hand', 'allocated', 'available', 'on_so', 'on_po', 'on_p', 'on_r', 'on_in', 'on_wo']


def get_daily_log_paths():
    """Get log file paths for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        'json': LOG_DIR / f"item_{ITEM_ID}_{today}.json",
        'text': LOG_DIR / f"item_{ITEM_ID}_{today}.log",
    }


def safe_float(value):
    """Safely convert value to float."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_item_snapshot():
    """Get current inventory state for item."""
    from apps.products.models.item import Item
    
    try:
        item = Item.objects.get(pk=ITEM_ID)
    except Item.DoesNotExist:
        return {"error": f"Item {ITEM_ID} not found"}
    
    # Item uses a JSON 'quantity' field - extract all tracked values
    qty_data = getattr(item, 'quantity', {}) or {}
    
    snapshot = {
        "item_id": ITEM_ID,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Add all quantity keys
    for key in QUANTITY_KEYS:
        snapshot[f"qty_{key}"] = safe_float(qty_data.get(key, 0))
    
    # Include raw quantity JSON for reference
    snapshot["quantity_raw"] = qty_data
    
    return snapshot


def get_pending_records_for_item():
    """Get ALL pending inventory records for item (including processed)."""
    from apps.core.models.pending import Pending
    
    # Get pending records related to our item - both active and processed
    pendings = Pending.objects.filter(
        model_name='item',
        record_id=str(ITEM_ID),
    ).order_by('-dt_created')[:20]  # Last 20
    
    results = []
    for p in pendings:
        data = getattr(p, 'data', {}) or {}
        qty = data.get('quantity', 0) or data.get('on_so', 0) or data.get('on_po', 0) or 0
        
        results.append({
            "id": p.pk,
            "model_name": getattr(p, 'model_name', None),
            "record_id": getattr(p, 'record_id', None),
            "purpose": getattr(p, 'purpose', None),
            "is_active": getattr(p, 'is_active', None),
            "dt_processed": getattr(p, 'dt_processed', None),
            "quantity": safe_float(qty),
            "data": data,
            "created_at": str(getattr(p, 'dt_created', '')),
        })
    return results


def get_unprocessed_pending_count():
    """Get count of unprocessed pending records for item."""
    from apps.core.models.pending import Pending
    
    return Pending.objects.filter(
        model_name='item',
        record_id=str(ITEM_ID),
        dt_processed=0,
    ).count()


def get_unprocessed_pending_summary():
    """Get summary of unprocessed pending records by purpose."""
    from apps.core.models.pending import Pending
    from django.db.models import Count
    
    # Get counts grouped by purpose
    summary = Pending.objects.filter(
        model_name='item',
        record_id=str(ITEM_ID),
        dt_processed=0,
    ).values('purpose').annotate(count=Count('id')).order_by('purpose')
    
    result = {
        'total': 0,
        'by_purpose': {},
        'records': [],
    }
    
    for row in summary:
        result['by_purpose'][row['purpose']] = row['count']
        result['total'] += row['count']
    
    # Also get the actual pending record details
    pendings = Pending.objects.filter(
        model_name='item',
        record_id=str(ITEM_ID),
        dt_processed=0,
    ).order_by('-dt_created')[:10]
    
    for p in pendings:
        data = getattr(p, 'data', {}) or {}
        result['records'].append({
            'id': p.pk,
            'purpose': getattr(p, 'purpose', None),
            'data': data,
            'created': str(getattr(p, 'dt_created', '')),
        })
    
    return result


def get_transaction_counts():
    """Get count of transactions containing this item."""
    from apps.transactions.models import OrderLine, PurchaseLine, InvoiceLine, ProposalLine
    
    counts = {}
    
    # Check OrderLine
    try:
        counts['order_lines'] = OrderLine.objects.filter(item__id_num=ITEM_ID).count()
    except Exception:
        counts['order_lines'] = 0
    
    # Check PurchaseLine
    try:
        counts['purchase_lines'] = PurchaseLine.objects.filter(item__id_num=ITEM_ID).count()
    except Exception:
        counts['purchase_lines'] = 0
    
    # Check InvoiceLine
    try:
        counts['invoice_lines'] = InvoiceLine.objects.filter(item__id_num=ITEM_ID).count()
    except Exception:
        counts['invoice_lines'] = 0
    
    # Check ProposalLine
    try:
        counts['proposal_lines'] = ProposalLine.objects.filter(item__id_num=ITEM_ID).count()
    except Exception:
        counts['proposal_lines'] = 0
    
    return counts


def get_transaction_details():
    """Get detailed transaction lines for this item."""
    from apps.transactions.models import OrderLine, PurchaseLine, InvoiceLine, ProposalLine
    
    details = []
    
    # Order Lines
    try:
        for line in OrderLine.objects.filter(item__id_num=ITEM_ID).select_related('order'):
            qty_data = getattr(line, 'quantity', {}) or {}
            details.append({
                "type": "order_line",
                "line_id": line.pk,
                "header_id": line.order_id if hasattr(line, 'order_id') else None,
                "status": getattr(line, 'status', None),
                "quantity": qty_data.get('ordered', 0),
                "quantity_raw": qty_data,
            })
    except Exception as e:
        details.append({"type": "order_line", "error": str(e)})
    
    # Purchase Lines
    try:
        for line in PurchaseLine.objects.filter(item__id_num=ITEM_ID).select_related('purchase'):
            qty_data = getattr(line, 'quantity', {}) or {}
            details.append({
                "type": "purchase_line",
                "line_id": line.pk,
                "header_id": line.purchase_id if hasattr(line, 'purchase_id') else None,
                "status": getattr(line, 'status', None),
                "quantity": qty_data.get('ordered', 0),
                "quantity_raw": qty_data,
            })
    except Exception as e:
        details.append({"type": "purchase_line", "error": str(e)})
    
    # Invoice Lines
    try:
        for line in InvoiceLine.objects.filter(item__id_num=ITEM_ID).select_related('invoice_id'):
            qty_data = getattr(line, 'quantity', {}) or {}
            details.append({
                "type": "invoice_line",
                "line_id": line.pk,
                "header_id": line.invoice_id_id if hasattr(line, 'invoice_id_id') else None,
                "status": getattr(line, 'status', None),
                "quantity": qty_data.get('invoiced', 0),
                "quantity_raw": qty_data,
            })
    except Exception as e:
        details.append({"type": "invoice_line", "error": str(e)})
    
    # Proposal Lines
    try:
        for line in ProposalLine.objects.filter(item__id_num=ITEM_ID).select_related('proposal_id'):
            qty_data = getattr(line, 'quantity', {}) or {}
            details.append({
                "type": "proposal_line",
                "line_id": line.pk,
                "header_id": line.proposal_id_id if hasattr(line, 'proposal_id_id') else None,
                "status": getattr(line, 'status', None),
                "quantity": qty_data.get('quoted', 0),
                "quantity_raw": qty_data,
            })
    except Exception as e:
        details.append({"type": "proposal_line", "error": str(e)})
    
    return details


def load_log():
    """Load existing JSON log file for today."""
    paths = get_daily_log_paths()
    if paths['json'].exists():
        with open(paths['json'], 'r') as f:
            return json.load(f)
    return {"item_id": ITEM_ID, "date": datetime.now().strftime("%Y-%m-%d"), "events": []}


def save_log(log_data):
    """Save JSON log file for today."""
    paths = get_daily_log_paths()
    paths['json'].parent.mkdir(parents=True, exist_ok=True)
    with open(paths['json'], 'w') as f:
        json.dump(log_data, f, indent=2, default=str)


def append_text_log(message: str):
    """Append to human-readable text log file for today."""
    paths = get_daily_log_paths()
    paths['text'].parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(paths['text'], 'a') as f:
        f.write(f"[{timestamp}] {message}\n")


def add_log_entry(event_type: str, description: str, transaction_info: dict = None, pending_info: dict = None):
    """Add a log entry with current snapshot."""
    log = load_log()
    
    snapshot = get_item_snapshot()
    pendings = get_pending_records_for_item()
    unprocessed_summary = get_unprocessed_pending_summary()
    tx_counts = get_transaction_counts()
    tx_details = get_transaction_details()
    
    # Calculate delta from last entry for all quantity keys
    delta = None
    if log["events"]:
        last = log["events"][-1]["snapshot"]
        delta = {}
        for key in QUANTITY_KEYS:
            delta[f"qty_{key}"] = snapshot.get(f"qty_{key}", 0) - last.get(f"qty_{key}", 0)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "description": description,
        "transaction": transaction_info,
        "pending_created": pending_info,
        "snapshot": snapshot,
        "pending_records": pendings,
        "unprocessed_pending": unprocessed_summary,  # Detailed breakdown
        "transaction_counts": tx_counts,
        "transaction_details": tx_details,
        "delta": delta,
    }
    
    log["events"].append(entry)
    save_log(log)
    
    # Build text log message
    text_msg = f"{event_type}: {description}"
    if transaction_info:
        text_msg += f" | {transaction_info.get('type')} #{transaction_info.get('id')}"
    if pending_info:
        text_msg += f" | PENDING_CREATED #{pending_info.get('id')} purpose={pending_info.get('purpose')}"
    
    # Always include item quantities
    text_msg += f" | on_hand={snapshot.get('qty_on_hand', 0)}, on_so={snapshot.get('qty_on_so', 0)}, on_po={snapshot.get('qty_on_po', 0)}"
    
    # Always include unprocessed pending summary
    text_msg += f" | UNAPPLIED_PENDING={unprocessed_summary['total']}"
    if unprocessed_summary['by_purpose']:
        purposes = [f"{k}:{v}" for k, v in unprocessed_summary['by_purpose'].items()]
        text_msg += f" ({', '.join(purposes)})"
    
    # Include delta if there are changes
    if delta:
        changes = [f"{k}={v:+.1f}" for k, v in delta.items() if v != 0]
        if changes:
            text_msg += f" | DELTA: {', '.join(changes)}"
    
    append_text_log(text_msg)
    
    return entry


def print_status():
    """Print current inventory status."""
    snapshot = get_item_snapshot()
    pendings = get_pending_records_for_item()
    unprocessed = get_unprocessed_pending_summary()
    tx_counts = get_transaction_counts()
    
    print(f"\n{'='*70}")
    print(f"INVENTORY STATUS - Item {ITEM_ID}")
    print(f"{'='*70}")
    print(f"Timestamp: {snapshot['timestamp']}")
    
    print(f"\n  Item Quantity Fields:")
    print(f"  {'Field':<15} {'Value':>12}  Description")
    print(f"  {'-'*15} {'-'*12}  {'-'*30}")
    print(f"  {'on_hand':<15} {snapshot.get('qty_on_hand', 0):>12.2f}  Physical inventory")
    print(f"  {'allocated':<15} {snapshot.get('qty_allocated', 0):>12.2f}  Reserved/committed")
    print(f"  {'available':<15} {snapshot.get('qty_available', 0):>12.2f}  on_hand - allocated")
    print(f"  {'on_so':<15} {snapshot.get('qty_on_so', 0):>12.2f}  On Sales Orders")
    print(f"  {'on_po':<15} {snapshot.get('qty_on_po', 0):>12.2f}  On Purchase Orders")
    print(f"  {'on_p':<15} {snapshot.get('qty_on_p', 0):>12.2f}  On Proposals")
    print(f"  {'on_r':<15} {snapshot.get('qty_on_r', 0):>12.2f}  On Receipts (informational)")
    print(f"  {'on_in':<15} {snapshot.get('qty_on_in', 0):>12.2f}  On Invoices (informational)")
    print(f"  {'on_wo':<15} {snapshot.get('qty_on_wo', 0):>12.2f}  On Work Orders")
    
    print(f"\n  Transaction Counts:")
    for k, v in tx_counts.items():
        print(f"    {k}: {v}")
    
    # Highlight unapplied pending records
    print(f"\n  *** UNAPPLIED PENDING RECORDS: {unprocessed['total']} ***")
    if unprocessed['by_purpose']:
        print(f"      By Purpose:")
        for purpose, count in unprocessed['by_purpose'].items():
            print(f"        {purpose}: {count}")
        if unprocessed['records']:
            print(f"      Recent Records:")
            for r in unprocessed['records'][:3]:
                print(f"        #{r['id']} {r['purpose']} | data={r['data']}")
    else:
        print(f"      (all pending records have been processed)")
    
    print(f"\n  All Pending Records (total: {len(pendings)}):")
    if pendings:
        for p in pendings[:5]:  # Show last 5
            processed = "✓" if p['dt_processed'] else "○"
            print(f"    [{processed}] #{p['id']} {p['purpose']} | data={p.get('data', {})}")
    else:
        print("    (none)")
    
    print(f"\n  Log Files (today: {datetime.now().strftime('%Y-%m-%d')}):")
    paths = get_daily_log_paths()
    print(f"    JSON: {paths['json']}")
    print(f"    Text: {paths['text']}")
    
    print(f"{'='*70}\n")


def print_history():
    """Print event history."""
    log = load_log()
    
    print(f"\n{'='*70}")
    print(f"INVENTORY EVENT LOG - Item {ITEM_ID}")
    print(f"{'='*70}")
    
    if not log["events"]:
        print("No events logged yet.")
        return
    
    for i, event in enumerate(log["events"], 1):
        print(f"\n[{i}] {event['timestamp']}")
        print(f"    Event: {event['event_type']}")
        print(f"    Description: {event['description']}")
        
        if event.get('transaction'):
            tx = event['transaction']
            print(f"    Transaction: {tx.get('type')} #{tx.get('id')}, line #{tx.get('line_id')}, qty={tx.get('quantity')}")
        
        if event.get('pending_created'):
            pc = event['pending_created']
            print(f"    Pending Created: #{pc.get('id')} purpose={pc.get('purpose')} data={pc.get('data')}")
        
        snap = event['snapshot']
        print(f"    Quantities: on_hand={snap.get('qty_on_hand', 0):.1f}, on_so={snap.get('qty_on_so', 0):.1f}, on_po={snap.get('qty_on_po', 0):.1f}, on_p={snap.get('qty_on_p', 0):.1f}")
        print(f"                allocated={snap.get('qty_allocated', 0):.1f}, available={snap.get('qty_available', 0):.1f}, on_in={snap.get('qty_on_in', 0):.1f}")
        
        # Show unapplied pending summary
        unproc = event.get('unprocessed_pending', {})
        if isinstance(unproc, dict):
            total = unproc.get('total', 0)
            by_purpose = unproc.get('by_purpose', {})
            purposes_str = ', '.join([f"{k}:{v}" for k, v in by_purpose.items()]) if by_purpose else ''
            print(f"    Unapplied Pending: {total} {f'({purposes_str})' if purposes_str else ''}")
        else:
            # Backwards compatibility
            print(f"    Unapplied Pending: {event.get('unprocessed_pending_count', 0)}")
        
        if event.get('delta'):
            d = event['delta']
            changes = [f"{k.replace('qty_', '')}={v:+.1f}" for k, v in d.items() if v != 0]
            if changes:
                print(f"    Delta: {', '.join(changes)}")
            else:
                print(f"    Delta: (no changes)")
    
    print(f"\n{'='*70}")
    print(f"Log Files (today: {datetime.now().strftime('%Y-%m-%d')}):")
    paths = get_daily_log_paths()
    print(f"  JSON: {paths['json']}")
    print(f"  Text: {paths['text']}")
    print(f"{'='*70}\n")


def print_pending():
    """Print detailed pending records."""
    pendings = get_pending_records_for_item()
    unprocessed = get_unprocessed_pending_count()
    tx_details = get_transaction_details()
    
    print(f"\n{'='*70}")
    print(f"PENDING & TRANSACTION DETAILS - Item {ITEM_ID}")
    print(f"{'='*70}")
    
    print(f"\n  Pending Records for Item {ITEM_ID} (unprocessed: {unprocessed}, total: {len(pendings)}):")
    if pendings:
        for p in pendings:
            processed = "✓ PROCESSED" if p['dt_processed'] else "○ UNPROCESSED"
            print(f"    ID: {p['id']} [{processed}]")
            print(f"      Purpose: {p['purpose']}")
            print(f"      Data: {p.get('data', {})}")
            print(f"      Created: {p['created_at']}")
            print()
    else:
        print("    (none)")
    
    print(f"\n  Transaction Lines for Item {ITEM_ID}:")
    if tx_details:
        for t in tx_details:
            if 'error' in t:
                print(f"    {t['type']}: ERROR - {t['error']}")
            else:
                print(f"    {t['type']} #{t['line_id']} (header #{t['header_id']}): status={t['status']}, qty={t['quantity']}")
    else:
        print("    (none)")
    
    print(f"{'='*70}\n")


def get_latest_pending_for_item():
    """Get the most recently created pending record for item."""
    from apps.core.models.pending import Pending
    
    pending = Pending.objects.filter(
        model_name='item',
        record_id=str(ITEM_ID),
    ).order_by('-dt_created').first()
    
    if pending:
        return {
            "id": pending.pk,
            "purpose": getattr(pending, 'purpose', None),
            "data": getattr(pending, 'data', {}),
            "dt_processed": getattr(pending, 'dt_processed', None),
        }
    return None


def create_order(quantity: float):
    """Create an Order with item 240 using LineItemService."""
    from apps.transactions.models import Order
    from apps.transactions.services.line_item_service import LineItemService
    
    with transaction.atomic():
        order = Order.objects.create(status='draft')
        
        # Use LineItemService to properly create pending records for inventory tracking
        service = LineItemService(create_pending=True)
        line = service.add_item_to_transaction(
            transaction=order,
            item_id=ITEM_ID,
            quantity=quantity,
        )
    
    # Get the pending record that was just created
    pending_info = get_latest_pending_for_item()
    
    entry = add_log_entry(
        event_type="ORDER_CREATED",
        description=f"Created Order #{order.pk} with {quantity} units of item {ITEM_ID}",
        transaction_info={"type": "order", "id": order.pk, "line_id": line.pk, "quantity": quantity},
        pending_info=pending_info,
    )
    
    print(f"\n✓ Created Order #{order.pk} with Line #{line.pk}")
    print(f"  Quantity: {quantity}")
    if pending_info:
        print(f"  Pending Record Created: #{pending_info['id']} purpose={pending_info['purpose']}")
    print(f"  NOTE: Run 'process_pending' to update item.quantity.on_so")
    print_status()
    
    return order, line


def create_purchase(quantity: float, unit_cost: float = 10.0):
    """Create a Purchase with item 240 using LineItemService."""
    from apps.transactions.models import Purchase
    from apps.transactions.services.line_item_service import LineItemService
    
    with transaction.atomic():
        purchase = Purchase.objects.create(status='draft')
        
        # Use LineItemService to properly create pending records for inventory tracking
        service = LineItemService(create_pending=True)
        line = service.add_item_to_transaction(
            transaction=purchase,
            item_id=ITEM_ID,
            quantity=quantity,
            unit_cost=unit_cost,
        )
    
    # Get the pending record that was just created
    pending_info = get_latest_pending_for_item()
    
    entry = add_log_entry(
        event_type="PURCHASE_CREATED",
        description=f"Created Purchase #{purchase.pk} with {quantity} units of item {ITEM_ID}",
        transaction_info={"type": "purchase", "id": purchase.pk, "line_id": line.pk, "quantity": quantity},
        pending_info=pending_info,
    )
    
    print(f"\n✓ Created Purchase #{purchase.pk} with Line #{line.pk}")
    print(f"  Quantity: {quantity}, Unit Cost: {unit_cost}")
    if pending_info:
        print(f"  Pending Record Created: #{pending_info['id']} purpose={pending_info['purpose']}")
    print(f"  NOTE: Run 'process_pending' to update item.quantity.on_po")
    print_status()
    
    return purchase, line


def create_proposal(quantity: float):
    """Create a Proposal with item 240 using LineItemService."""
    from apps.transactions.models import Proposal
    from apps.transactions.services.line_item_service import LineItemService
    
    with transaction.atomic():
        proposal = Proposal.objects.create(status='draft')
        
        # Use LineItemService to properly create pending records for inventory tracking
        service = LineItemService(create_pending=True)
        line = service.add_item_to_transaction(
            transaction=proposal,
            item_id=ITEM_ID,
            quantity=quantity,
        )
    
    # Get the pending record that was just created
    pending_info = get_latest_pending_for_item()
    
    entry = add_log_entry(
        event_type="PROPOSAL_CREATED",
        description=f"Created Proposal #{proposal.pk} with {quantity} units of item {ITEM_ID}",
        transaction_info={"type": "proposal", "id": proposal.pk, "line_id": line.pk, "quantity": quantity},
        pending_info=pending_info,
    )
    
    print(f"\n✓ Created Proposal #{proposal.pk} with Line #{line.pk}")
    print(f"  Quantity: {quantity}")
    if pending_info:
        print(f"  Pending Record Created: #{pending_info['id']} purpose={pending_info['purpose']}")
    print(f"  NOTE: Run 'process_pending' to update item.quantity.on_p")
    print_status()
    
    return proposal, line


def create_invoice(quantity: float):
    """Create an Invoice with item 240 using LineItemService."""
    from apps.transactions.models import Invoice
    from apps.transactions.services.line_item_service import LineItemService
    
    with transaction.atomic():
        invoice = Invoice.objects.create(status='draft')
        
        # Use LineItemService to properly create pending records for inventory tracking
        service = LineItemService(create_pending=True)
        line = service.add_item_to_transaction(
            transaction=invoice,
            item_id=ITEM_ID,
            quantity=quantity,
        )
    
    # Get the pending record that was just created
    pending_info = get_latest_pending_for_item()
    
    entry = add_log_entry(
        event_type="INVOICE_CREATED",
        description=f"Created Invoice #{invoice.pk} with {quantity} units of item {ITEM_ID}",
        transaction_info={"type": "invoice", "id": invoice.pk, "line_id": line.pk, "quantity": quantity},
        pending_info=pending_info,
    )
    
    print(f"\n✓ Created Invoice #{invoice.pk} with Line #{line.pk}")
    print(f"  Quantity: {quantity}")
    if pending_info:
        print(f"  Pending Record Created: #{pending_info['id']} purpose={pending_info['purpose']}")
    print(f"  NOTE: Run 'process_pending' to update item.quantity.on_in")
    print_status()
    
    return invoice, line


def create_workorder(quantity: float):
    """Create a WorkOrder with item 240 using LineItemService."""
    from apps.transactions.models import WorkOrder
    from apps.transactions.services.line_item_service import LineItemService
    
    with transaction.atomic():
        workorder = WorkOrder.objects.create(status='draft')
        
        # Use LineItemService to properly create pending records for inventory tracking
        service = LineItemService(create_pending=True)
        line = service.add_item_to_transaction(
            transaction=workorder,
            item_id=ITEM_ID,
            quantity=quantity,
        )
    
    # Get the pending record that was just created
    pending_info = get_latest_pending_for_item()
    
    entry = add_log_entry(
        event_type="WORKORDER_CREATED",
        description=f"Created WorkOrder #{workorder.pk} with {quantity} units of item {ITEM_ID}",
        transaction_info={"type": "workorder", "id": workorder.pk, "line_id": line.pk, "quantity": quantity},
        pending_info=pending_info,
    )
    
    print(f"\n✓ Created WorkOrder #{workorder.pk} with Line #{line.pk}")
    print(f"  Quantity: {quantity}")
    if pending_info:
        print(f"  Pending Record Created: #{pending_info['id']} purpose={pending_info['purpose']}")
    print(f"  NOTE: Run 'process_pending' to update item.quantity.on_wo")
    print_status()
    
    return workorder, line


def create_receipt(quantity: float):
    """Create a Receipt with item 240 using LineItemService.
    
    Note: Receipts increase on_hand and track the informational on_r field.
    Unlike the receive_purchase_order flow (which receives against a PO),
    this creates a standalone receipt for testing the on_r pending flow.
    """
    from apps.transactions.models.receipt import Receipt
    from apps.transactions.services.line_item_service import LineItemService
    
    with transaction.atomic():
        receipt = Receipt.objects.create()
        
        # Use LineItemService to properly create pending records for inventory tracking
        service = LineItemService(create_pending=True)
        # Receipt doesn't have a standard line model, so we'll create a pending record directly
        # This simulates a receipt that would increase on_hand via the pending processor
        from apps.core.models.pending import Pending
        from django.utils import timezone
        
        pending = Pending.objects.create(
            model_name='item',
            record_id=str(ITEM_ID),
            purpose='receipt_line_add',
            name=f"Receipt line add for item {ITEM_ID}",
            data={
                'item_id': ITEM_ID,
                'quantity': float(quantity),
                'on_r': float(quantity),  # Informational - tracks received qty
                # Note: Receipts INCREASE on_hand (opposite of invoices)
                'source_type': 'receipt',
                'source_id': receipt.pk,
            }
        )
    
    # Get the pending record that was just created
    pending_info = {
        "id": pending.pk,
        "purpose": pending.purpose,
        "data": pending.data,
        "dt_processed": None,
    }
    
    entry = add_log_entry(
        event_type="RECEIPT_CREATED",
        description=f"Created Receipt #{receipt.pk} with {quantity} units of item {ITEM_ID}",
        transaction_info={"type": "receipt", "id": receipt.pk, "quantity": quantity},
        pending_info=pending_info,
    )
    
    print(f"\n✓ Created Receipt #{receipt.pk}")
    print(f"  Quantity: {quantity}")
    if pending_info:
        print(f"  Pending Record Created: #{pending_info['id']} purpose={pending_info['purpose']}")
    print(f"  NOTE: Run 'process_pending' to update item.quantity.on_r and on_hand")
    print_status()
    
    return receipt, pending


def process_pending():
    """Process pending inventory records for item 240."""
    from apps.transactions.services.pending_inventory_processor import process_pending_for_item
    
    # Get pending records BEFORE processing
    unprocessed_before = get_unprocessed_pending_summary()
    
    # Log before state
    add_log_entry(
        event_type="PROCESS_PENDING_START",
        description=f"Starting pending processing: {unprocessed_before['total']} unprocessed records for item {ITEM_ID}"
    )
    
    # Process
    summary = process_pending_for_item(item_id=ITEM_ID, dry_run=False)
    
    # Get pending records AFTER processing
    unprocessed_after = get_unprocessed_pending_summary()
    
    # Log after state with delta
    entry = add_log_entry(
        event_type="PROCESS_PENDING_COMPLETE",
        description=f"Processed {summary.get('processed', 0)} pending records. Remaining unapplied: {unprocessed_after['total']}",
        transaction_info={
            "summary": summary,
            "unprocessed_before": unprocessed_before,
            "unprocessed_after": unprocessed_after,
        }
    )
    
    print(f"\n✓ Processed pending inventory records")
    print(f"  Before: {unprocessed_before['total']} unapplied")
    if unprocessed_before['by_purpose']:
        print(f"          ({', '.join([f'{k}:{v}' for k, v in unprocessed_before['by_purpose'].items()])})")
    print(f"  After:  {unprocessed_after['total']} unapplied")
    if unprocessed_after['by_purpose']:
        print(f"          ({', '.join([f'{k}:{v}' for k, v in unprocessed_after['by_purpose'].items()])})")
    print(f"  Summary:")
    print(f"    Found: {summary.get('total_found', 0)}")
    print(f"    Processed: {summary.get('processed', 0)}")
    print(f"    Skipped (locked): {summary.get('skipped_locked', 0)}")
    print(f"    Skipped (missing item): {summary.get('skipped_missing_item', 0)}")
    print(f"    Errors: {summary.get('errors', 0)}")
    print_status()
    
    return summary


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'baseline':
        entry = add_log_entry(
            event_type="BASELINE",
            description="Initial baseline capture"
        )
        print("✓ Baseline captured and logged")
        print_status()
    
    elif command == 'status':
        print_status()
    
    elif command == 'history':
        print_history()
    
    elif command == 'pending':
        print_pending()
    
    elif command == 'process_pending':
        process_pending()
    
    elif command == 'reset':
        paths = get_daily_log_paths()
        if paths['json'].exists():
            paths['json'].unlink()
            print(f"✓ Removed {paths['json']}")
        if paths['text'].exists():
            paths['text'].unlink()
            print(f"✓ Removed {paths['text']}")
        print("✓ Today's log files cleared")
    
    elif command == 'log':
        note = sys.argv[2] if len(sys.argv) > 2 else "Manual log entry"
        entry = add_log_entry(
            event_type="MANUAL",
            description=note
        )
        print(f"✓ Log entry added: {note}")
        print_status()
    
    elif command == 'create':
        if len(sys.argv) < 4:
            print("Usage: create <order|purchase|proposal|invoice|workorder> <quantity>")
            return
        
        tx_type = sys.argv[2].lower()
        quantity = float(sys.argv[3])
        
        if tx_type == 'order':
            create_order(quantity)
        elif tx_type == 'purchase':
            create_purchase(quantity)
        elif tx_type == 'proposal':
            create_proposal(quantity)
        elif tx_type == 'invoice':
            create_invoice(quantity)
        elif tx_type in ('workorder', 'wo'):
            create_workorder(quantity)
        elif tx_type == 'receipt':
            create_receipt(quantity)
        else:
            print(f"Unknown transaction type: {tx_type}")
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == '__main__':
    main()
