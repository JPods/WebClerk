"""
Flight Simulator: Inventory — Interactive training for inventory flows.

Shows how quantities, pending records, and GL entries change at each
stage of a transaction lifecycle. The user walks through:

  1. Starting inventory (item with on_hand=100)
  2. Add Proposal for 15 units → on_p changes, NO GL
  3. Convert 9 to Order → on_p decreases, on_so increases, pending created, NO GL
  4. Create Invoice for 4 → on_so decreases, on_hand decreases, GL: AR/Revenue/COGS/Inventory + Tax + Commission
  5. Create Purchase for 14 → on_po increases, NO GL
  6. Receive 11 from Purchase → on_po decreases, on_hand increases, GL: Inventory/AP
  7. Partial payment on invoice → GL: Cash/AR (partial amount)
  8. Discount on remaining → GL: Discount/AR
  9. Write-off small balance → GL: Bad Debt/AR

Tax rate: 5% (easy mental math)
Commission: 5% of revenue
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps


def _now_ms():
    return int(time.time() * 1000)


# Default GL accounts
DEFAULTS = {
    'ar': 'ASSET-AR-000',
    'cash': 'ASSET-CASH-000',
    'revenue': 'REV-SALES-000',
    'cogs': 'COGS-PRODUCTS-000',
    'inventory': 'ASSET-INVENTORY-000',
    'ap': 'LIAB-ACCTSPAY-000',
    'tax_payable': 'LIAB-SALESTAX-000',
    'commission_exp': 'EXP-COMMISSIONS-000',
    'commission_pay': 'LIAB-COMMPAY-000',
    'discount': 'EXP-DISCOUNTS-000',
    'bad_debt': 'EXP-BADDEBT-000',
    'scrap': 'EXP-SCRAP-000',
}

TAX_RATE = Decimal('0.05')       # 5%
COMMISSION_RATE = Decimal('0.05')  # 5%


def reset_flight_simulator(item_ida: str) -> Dict[str, Any]:
    """Reset an item and all its training data to clean state.

    Called when the user clicks a simulation card (fresh start).
    Deletes all training transactions, lines, and pending records
    for this item, then resets quantity to on_hand=100, everything else 0.
    """
    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')
    Proposal = dj_apps.get_model('transactions', 'Proposal')
    Order = dj_apps.get_model('transactions', 'Order')
    Invoice = dj_apps.get_model('transactions', 'Invoice')

    try:
        item = Item.objects.get(ida=item_ida)
    except Item.DoesNotExist:
        return {'error': f'Item with ida={item_ida} not found'}

    item_id = item.pk

    # Delete all pending records for this item
    p_del = Pending.objects.filter(record_id=str(item_id)).delete()

    # Collect parent header IDs from lines, then delete lines and orphaned headers
    line_configs = [
        ('transactions', 'ProposalLine', 'proposal_id', 'transactions', 'Proposal'),
        ('transactions', 'OrderLine', 'order_id', 'transactions', 'Order'),
        ('transactions', 'InvoiceLine', 'invoice_id', 'transactions', 'Invoice'),
        ('transactions', 'PurchaseLine', 'purchase_id', 'transactions', 'Purchase'),
        ('transactions', 'WorkOrderLine', 'workorder_id', 'transactions', 'WorkOrder'),
    ]
    lines_deleted = 0
    headers_deleted = 0
    for line_app, line_model, fk_field, header_app, header_model in line_configs:
        try:
            LineModel = dj_apps.get_model(line_app, line_model)
            lines_qs = LineModel.objects.filter(item_fk_id=item_id)
            # Collect parent IDs before deleting
            parent_ids = set(lines_qs.values_list(fk_field, flat=True))
            count, _ = lines_qs.delete()
            lines_deleted += count
            # Delete parent headers that now have zero lines
            if parent_ids:
                HeaderModel = dj_apps.get_model(header_app, header_model)
                for pid in parent_ids:
                    remaining = LineModel.objects.filter(**{fk_field: pid}).count()
                    if remaining == 0:
                        HeaderModel.objects.filter(pk=pid).delete()
                        headers_deleted += 1
        except LookupError:
            pass

    # Reset item quantity
    item.quantity = {
        'on_p': 0, 'on_po': 0, 'on_so': 0, 'on_wo': 0,
        'on_hand': 100, 'allocated': 0, 'available': 100,
    }
    item.save(update_fields=['quantity'])

    return {
        'success': True,
        'item_id': item_id,
        'item_ida': item_ida,
        'quantity': item.quantity,
        'pending_deleted': p_del[1].get('core.Pending', 0) if isinstance(p_del[1], dict) else 0,
        'lines_deleted': lines_deleted,
        'headers_deleted': headers_deleted,
    }


def get_flight_transactions(item_id: int) -> Dict[str, Any]:
    """Build the transaction display — three rows per event.

    Row pattern:
      1. item          — starting state (or state after previous event)
      2. transaction   — the line that was saved (cause)
      3. pending       — the pending record created by the line (mechanism)
      4. item          — item.quantity after pending applied (effect)

    The first row is always the initial item state (before any events).
    Running totals are reconstructed by walking pending deltas forward.
    """
    COLUMNS = ['on_hand', 'on_so', 'on_po', 'on_p', 'on_wo', 'available']

    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return {'error': f'Item {item_id} not found'}

    quantity = item.quantity if isinstance(item.quantity, dict) else {}
    current_state = {col: _dec(quantity.get(col, 0)) for col in COLUMNS}
    item_dict = {
        'id': item.pk,
        'ida': item.ida,
        'name': str(item),
        'quantity': current_state,
    }

    # ── Gather transaction lines ─────────────────────────────────────
    tx_lines = []
    line_models = [
        ('transactions', 'ProposalLine', 'proposal'),
        ('transactions', 'OrderLine', 'order'),
        ('transactions', 'InvoiceLine', 'invoice'),
        ('transactions', 'PurchaseLine', 'purchase'),
        ('transactions', 'WorkOrderLine', 'workorder'),
    ]
    for app, model_name, parent_model in line_models:
        try:
            LineModel = dj_apps.get_model(app, model_name)
        except LookupError:
            continue
        for line in LineModel.objects.filter(
            item_fk_id=item_id, is_active=True, is_deleted=False
        ).select_related(parent_model).order_by('dt_created'):
            qty = _line_active_qty(line)
            parent_obj = getattr(line, parent_model, None)
            parent_ida = getattr(parent_obj, 'ida', '') if parent_obj else ''
            parent_id = getattr(line, f'{parent_model}_id', None)
            tx_lines.append({
                'type': f'{parent_model}_line',
                'label': f'{parent_model.title()} #{parent_ida}',
                'model': parent_model,
                'record_id': parent_id,
                'line_id': line.pk,
                'qty': qty,
                'dt': getattr(line, 'dt_created', 0) or 0,
            })

    # ── Gather pending records ───────────────────────────────────────
    pending_list = []
    for p in Pending.objects.filter(
        model_name='item', record_id=str(item_id),
    ).order_by('dt_created'):
        data = p.changes if isinstance(p.changes, dict) else {}
        deltas = {}
        for col in COLUMNS:
            v = float(data.get(col, 0) or 0)
            if v != 0:
                deltas[col] = v
        pending_list.append({
            'type': 'pending',
            'purpose': p.purpose or '',
            'name': p.name or '',
            'deltas': deltas,
            'processed': p.is_processed(),
            'line_id': data.get('line_id'),
            'dt': getattr(p, 'dt_created', 0) or 0,
        })

    # ── Pair lines with their pending records ────────────────────────
    # Sort both by dt_created, then interleave: line → pending → state
    tx_lines.sort(key=lambda x: x['dt'])
    pending_list.sort(key=lambda x: x['dt'])

    # ── Compute initial state by reverse-walking ─────────────────────
    # Start from current item.quantity, subtract all pending deltas
    # to get back to the state before any transactions.
    initial = dict(current_state)
    for p in pending_list:
        if p['processed']:
            for col, delta in p['deltas'].items():
                initial[col] = initial.get(col, 0) - delta
    # Recompute available
    initial['available'] = initial.get('on_hand', 0)

    # ── Build rows ───────────────────────────────────────────────────
    rows: List[Dict[str, Any]] = []
    running = dict(initial)

    # Row 1: initial item state
    rows.append({
        'type': 'item',
        'label': f'{item_dict["ida"]}',
        'values': {col: int(running[col]) for col in COLUMNS},
    })

    # Merge lines and pending by timestamp
    all_events = []
    for tx in tx_lines:
        all_events.append(('line', tx))
    for p in pending_list:
        all_events.append(('pending', p))
    all_events.sort(key=lambda x: (x[1]['dt'], 0 if x[0] == 'line' else 1))

    for kind, event in all_events:
        if kind == 'line':
            # Transaction line row (cause)
            rows.append({
                'type': event['type'],
                'label': event['label'],
                'model': event['model'],
                'record_id': event.get('record_id'),
                'values': {'qty': event['qty']},
            })
        elif kind == 'pending':
            # Pending row (mechanism) — show deltas
            display_deltas = {}
            for col, v in event['deltas'].items():
                display_deltas[col] = f'+{int(v)}' if v > 0 else f'{int(v)}'
            rows.append({
                'type': 'pending',
                'label': event['name'] or event['purpose'],
                'values': display_deltas,
                'processed': event['processed'],
            })
            # Item state row (effect) — running totals after this pending
            if event['processed']:
                for col, delta in event['deltas'].items():
                    running[col] = running.get(col, 0) + delta
                running['available'] = running.get('on_hand', 0)
            rows.append({
                'type': 'item',
                'label': item_dict['ida'],
                'values': {col: int(running[col]) for col in COLUMNS},
            })

    return {
        'columns': COLUMNS,
        'rows': rows,
        'item': item_dict,
        'row_count': len(rows),
    }


def get_item_by_ida(ida: str) -> Dict[str, Any]:
    """Look up an item by ida and return its flight state."""
    Item = dj_apps.get_model('products', 'Item')
    try:
        item = Item.objects.get(ida=ida)
    except Item.DoesNotExist:
        return {'error': f'Item with ida={ida} not found'}
    return get_item_flight_state(item.pk)


def get_item_flight_state(item_id: int) -> Dict[str, Any]:
    """Return the complete flight state for an item — all lines, pending, GL impact.

    This is the real-time view. The flight simulator UI calls this after
    each user action to show what changed.
    """
    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return {'error': f'Item {item_id} not found'}

    quantity = item.quantity if isinstance(item.quantity, dict) else {}
    cost_data = item.cost if isinstance(item.cost, dict) else {}
    gls = item.gls if isinstance(getattr(item, 'gls', None), dict) else {}
    price_data = item.price if isinstance(item.price, dict) else {}

    item_dict = {
        'id': item.pk,
        'ida': item.ida,
        'name': str(item),
        'quantity': {
            'on_hand': _dec(quantity.get('on_hand', 0)),
            'on_so': _dec(quantity.get('on_so', 0)),
            'on_po': _dec(quantity.get('on_po', 0)),
            'on_p': _dec(quantity.get('on_p', 0)),
            'on_wo': _dec(quantity.get('on_wo', 0)),
            'allocated': _dec(quantity.get('allocated', 0)),
            'available': _dec(quantity.get('available', 0)),
            'on_reciept': _dec(quantity.get('on_reciept', 0)),
            'on_in': _dec(quantity.get('on_in', 0)),
        },
        'cost': {
            'standard': _dec(cost_data.get('standard', 0)),
            'last': _dec(cost_data.get('last', 0)),
            'avg': _dec(cost_data.get('average', cost_data.get('avg', 0))),
        },
        'price': {
            'base': _dec(price_data.get('base', 0)),
        },
        'gls': {
            'revenue': gls.get('revenue') or DEFAULTS['revenue'],
            'cogs': gls.get('cogs') or DEFAULTS['cogs'],
            'inventory': gls.get('inventory') or DEFAULTS['inventory'],
            'purchase': gls.get('purchase') or DEFAULTS['ap'],
        },
    }

    # Gather all transaction lines for this item
    lines = []
    lines.extend(_get_proposal_lines(item_id, item_dict))
    lines.extend(_get_order_lines(item_id, item_dict))
    lines.extend(_get_invoice_lines(item_id, item_dict))
    lines.extend(_get_purchase_lines(item_id, item_dict))
    lines.extend(_get_workorder_lines(item_id, item_dict))

    # Sort by dt_created
    lines.sort(key=lambda x: x.get('dt_created') or 0)

    # Gather pending records
    pending = _get_pending_records(item_id)

    return {
        'item': item_dict,
        'lines': lines,
        'pending': pending,
        'tax_rate': float(TAX_RATE),
        'commission_rate': float(COMMISSION_RATE),
        'gl_accounts': DEFAULTS,
        'dt_generated': _now_ms(),
    }


def get_flight_scenario() -> Dict[str, Any]:
    """Return the scripted training scenario with expected values at each step.

    This is the "lesson plan" — what the user should do and what they
    should see at each step. The UI walks through these steps.
    """
    unit_price = Decimal('10.00')
    unit_cost = Decimal('6.00')

    steps = [
        {
            'step': 1,
            'title': 'Starting Inventory',
            'instruction': 'Select an item with on_hand = 100, price = $10.00, cost = $6.00',
            'action': None,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 0, 'on_po': 0, 'on_p': 0,
                'allocated': 0, 'available': 100,
            },
            'expected_gl': [],
            'explanation': 'No transactions yet. All 100 units are available.',
        },
        {
            'step': 2,
            'title': 'Create Proposal for 15 units',
            'instruction': 'Create a Proposal with 1 line: 15 units of this item at $10.00',
            'action': 'create_proposal_line',
            'qty': 15,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 0, 'on_po': 0, 'on_p': 15,
                'allocated': 0, 'available': 100,
            },
            'expected_gl': [],
            'explanation': 'Proposal reserves 15 units (on_p=15). No GL impact — a proposal is just a quote. Available stays 100 because proposals don\'t allocate.',
        },
        {
            'step': 3,
            'title': 'Convert 9 units to Order',
            'instruction': 'Create an Order from the Proposal for 9 of the 15 units',
            'action': 'create_order_from_proposal',
            'qty': 9,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 9, 'on_po': 0, 'on_p': 6,
                'allocated': 9, 'available': 91,
            },
            'expected_pending': [
                {'purpose': 'on_so', 'delta': '+9'},
                {'purpose': 'on_p', 'delta': '-9'},
            ],
            'expected_gl': [],
            'explanation': 'Order commits 9 units (on_so=9). Proposal drops to 6 remaining. Available drops to 91 (100 - 9 allocated). Pending records track the movement. Still NO GL impact — an order is a commitment, not a financial event.',
        },
        {
            'step': 4,
            'title': 'Create Invoice for 4 units',
            'instruction': 'Create an Invoice from the Order for 4 of the 9 units',
            'action': 'create_invoice_from_order',
            'qty': 4,
            'expected_quantity': {
                'on_hand': 96, 'on_so': 5, 'on_po': 0, 'on_p': 6,
                'allocated': 5, 'available': 91,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '-4'},
                {'purpose': 'on_so', 'delta': '-4'},
            ],
            'expected_gl': [
                {'account': 'ASSET-AR-000', 'side': 'debit', 'amount': 42.00,
                 'purpose': 'Accounts Receivable (4 × $10.00 + 5% tax = $42.00)'},
                {'account': 'REV-SALES-000', 'side': 'credit', 'amount': 40.00,
                 'purpose': 'Revenue (4 × $10.00)'},
                {'account': 'LIAB-SALESTAX-000', 'side': 'credit', 'amount': 2.00,
                 'purpose': 'Sales Tax Payable (5% × $40.00)'},
                {'account': 'COGS-PRODUCTS-000', 'side': 'debit', 'amount': 24.00,
                 'purpose': 'Cost of Goods Sold (4 × $6.00)'},
                {'account': 'ASSET-INVENTORY-000', 'side': 'credit', 'amount': 24.00,
                 'purpose': 'Inventory reduction (4 units leave the shelf)'},
                {'account': 'EXP-COMMISSIONS-000', 'side': 'debit', 'amount': 2.00,
                 'purpose': 'Commission Expense (5% × $40.00 revenue)'},
                {'account': 'LIAB-COMMPAY-000', 'side': 'credit', 'amount': 2.00,
                 'purpose': 'Commission Payable (owed to rep)'},
            ],
            'explanation': (
                'THIS is the financial event. Inventory leaves the shelf (on_hand 100→96). '
                'Order backlog drops (on_so 9→5). GL records the sale:\n'
                '• AR debit $42.00 (what customer owes: $40 + $2 tax)\n'
                '• Revenue credit $40.00 (what we earned)\n'
                '• Tax payable credit $2.00 (owed to government)\n'
                '• COGS debit $24.00 (cost of what we sold)\n'
                '• Inventory credit $24.00 (asset leaves the books)\n'
                '• Commission expense $2.00 / payable $2.00 (owed to rep)'
            ),
        },
        {
            'step': 5,
            'title': 'Create Purchase for 14 units',
            'instruction': 'Create a Purchase Order for 14 units at $6.00 cost',
            'action': 'create_purchase',
            'qty': 14,
            'expected_quantity': {
                'on_hand': 96, 'on_so': 5, 'on_po': 14, 'on_p': 6,
                'allocated': 5, 'available': 91,
            },
            'expected_pending': [
                {'purpose': 'on_po', 'delta': '+14'},
            ],
            'expected_gl': [],
            'explanation': 'PO commits to buy 14 units (on_po=14). No GL impact — a PO is a commitment to a vendor, not a financial event. The money hasn\'t moved yet.',
        },
        {
            'step': 6,
            'title': 'Receive 11 of 14 from Purchase',
            'instruction': 'Receive 11 units against the PO (partial receipt)',
            'action': 'receive_purchase',
            'qty': 11,
            'expected_quantity': {
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_p': 6,
                'allocated': 5, 'available': 102,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '+11'},
                {'purpose': 'on_po', 'delta': '-11'},
            ],
            'expected_gl': [
                {'account': 'ASSET-INVENTORY-000', 'side': 'debit', 'amount': 66.00,
                 'purpose': 'Inventory increase (11 × $6.00 — goods on the shelf)'},
                {'account': 'LIAB-ACCTSPAY-000', 'side': 'credit', 'amount': 66.00,
                 'purpose': 'Accounts Payable (we owe the vendor)'},
            ],
            'explanation': (
                'Goods arrive. Inventory increases (on_hand 96→107). PO backlog drops (on_po 14→3). '
                'GL records the receipt:\n'
                '• Inventory debit $66.00 (asset on the shelf)\n'
                '• AP credit $66.00 (we owe the vendor)\n'
                'Note: 3 units still on order (on_po=3).'
            ),
        },
        {
            'step': 7,
            'title': 'Partial Payment — $30.00 of $42.00 invoice',
            'instruction': 'Record a $30.00 payment against the $42.00 invoice',
            'action': 'partial_payment',
            'amount': 30.00,
            'expected_gl': [
                {'account': 'ASSET-CASH-000', 'side': 'debit', 'amount': 30.00,
                 'purpose': 'Cash received'},
                {'account': 'ASSET-AR-000', 'side': 'credit', 'amount': 30.00,
                 'purpose': 'AR reduced (customer owes $12.00 remaining)'},
            ],
            'explanation': (
                'Customer pays $30 of the $42 owed. No inventory change — this is purely financial.\n'
                '• Cash debit $30.00 (money in the bank)\n'
                '• AR credit $30.00 (reduce what they owe)\n'
                'Remaining balance: $42.00 - $30.00 = $12.00'
            ),
        },
        {
            'step': 8,
            'title': 'Discount — $10.00 off remaining balance',
            'instruction': 'Apply a $10.00 discount to the remaining $12.00 balance',
            'action': 'discount',
            'amount': 10.00,
            'expected_gl': [
                {'account': 'EXP-DISCOUNTS-000', 'side': 'debit', 'amount': 10.00,
                 'purpose': 'Discount given (expense — reduces margin)'},
                {'account': 'ASSET-AR-000', 'side': 'credit', 'amount': 10.00,
                 'purpose': 'AR reduced (customer now owes $2.00)'},
            ],
            'explanation': (
                'We give the customer a $10 discount. No inventory change.\n'
                '• Discount expense debit $10.00 (cost of the discount)\n'
                '• AR credit $10.00 (reduce what they owe)\n'
                'Remaining balance: $12.00 - $10.00 = $2.00\n'
                'Note: This hits the Discount Expense account, NOT Revenue. '
                'Revenue stays at $40 — the discount is tracked separately so you can see margin erosion.'
            ),
        },
        {
            'step': 9,
            'title': 'Write-off — dismiss $2.00 remaining balance',
            'instruction': 'Write off the remaining $2.00 as uncollectable',
            'action': 'write_off',
            'amount': 2.00,
            'exit_point': {
                'name': 'Invoice Settled',
                'summary': 'The invoice is fully settled: $30 cash + $10 discount + $2 write-off = $42. You can stop here or continue to see returns, aging, and orphan cleanup.',
            },
            'expected_gl': [
                {'account': 'EXP-BADDEBT-000', 'side': 'debit', 'amount': 2.00,
                 'purpose': 'Bad Debt expense (cost of uncollectable)'},
                {'account': 'ASSET-AR-000', 'side': 'credit', 'amount': 2.00,
                 'purpose': 'AR zeroed out (invoice fully settled)'},
            ],
            'explanation': (
                'The $2.00 remaining isn\'t worth chasing. Write it off.\n'
                '• Bad Debt debit $2.00 (expense — money we\'ll never collect)\n'
                '• AR credit $2.00 (balance now $0)\n'
                'The invoice is now fully settled: $30 cash + $10 discount + $2 write-off = $42.'
            ),
        },
        # ── Reverse Flow ─────────────────────────────────────────────
        {
            'step': 10,
            'title': 'Return 1 unit',
            'instruction': 'Customer returns 1 of the 4 invoiced units. Create a Credit Memo.',
            'action': 'create_return',
            'qty': 1,
            'section': 'Reverse Flow',
            'expected_quantity': {
                'on_hand': 108, 'on_so': 5, 'on_po': 3, 'on_p': 6,
                'allocated': 5, 'available': 103,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '+1'},
            ],
            'expected_gl': [
                {'account': 'REV-SALES-000', 'side': 'debit', 'amount': 10.00,
                 'purpose': 'Revenue reversal (1 × $10.00)'},
                {'account': 'LIAB-SALESTAX-000', 'side': 'debit', 'amount': 0.50,
                 'purpose': 'Sales tax reversal (5% × $10.00)'},
                {'account': 'ASSET-AR-000', 'side': 'credit', 'amount': 10.50,
                 'purpose': 'Credit memo — customer is owed $10.50'},
                {'account': 'ASSET-INVENTORY-000', 'side': 'debit', 'amount': 6.00,
                 'purpose': 'Inventory restored (1 × $6.00 — item back on shelf)'},
                {'account': 'COGS-PRODUCTS-000', 'side': 'credit', 'amount': 6.00,
                 'purpose': 'COGS reversal (cost of returned unit)'},
            ],
            'explanation': (
                'Customer sends 1 unit back. Everything reverses:\n'
                '• Revenue debit $10.00 (we un-earn the sale)\n'
                '• Tax debit $0.50 (we un-collect the tax)\n'
                '• AR credit $10.50 (we now owe the customer a credit)\n'
                '• Inventory debit $6.00 (unit back on the shelf)\n'
                '• COGS credit $6.00 (cost reversal)\n'
                'On_hand goes from 107→108. The unit is physically back.'
            ),
        },
        {
            'step': 11,
            'title': 'Scrap returned item',
            'instruction': 'The returned unit is damaged. Create an inventory adjustment to scrap it.',
            'action': 'scrap_adjustment',
            'qty': 1,
            'section': 'Reverse Flow',
            'expected_quantity': {
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_p': 6,
                'allocated': 5, 'available': 102,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '-1'},
            ],
            'expected_gl': [
                {'account': 'EXP-SCRAP-000', 'side': 'debit', 'amount': 6.00,
                 'purpose': 'Scrap/loss expense (damaged goods — cost of 1 unit)'},
                {'account': 'ASSET-INVENTORY-000', 'side': 'credit', 'amount': 6.00,
                 'purpose': 'Inventory reduction (scrapped unit leaves the books)'},
            ],
            'explanation': (
                'The returned item is damaged beyond resale. Scrap it.\n'
                '• Scrap expense debit $6.00 (loss on the damaged unit)\n'
                '• Inventory credit $6.00 (remove from asset)\n'
                'On_hand goes from 108→107. The unit is gone.\n'
                'This is a real cost — we got the item back but can\'t sell it. '
                'Alice tracks scrap rates by vendor and category.'
            ),
        },
        {
            'step': 12,
            'title': 'Refund customer',
            'instruction': 'Issue a refund payment of $10.50 against the credit memo.',
            'action': 'refund_payment',
            'amount': 10.50,
            'section': 'Reverse Flow',
            'exit_point': {
                'name': 'Returns Complete',
                'summary': 'Return processed, item scrapped, customer refunded. You can stop here or continue to see aging and orphan cleanup.',
            },
            'expected_gl': [
                {'account': 'ASSET-AR-000', 'side': 'debit', 'amount': 10.50,
                 'purpose': 'Clear credit memo balance'},
                {'account': 'ASSET-CASH-000', 'side': 'credit', 'amount': 10.50,
                 'purpose': 'Cash outflow — refund to customer'},
            ],
            'explanation': (
                'Pay the customer what we owe from the credit memo.\n'
                '• AR debit $10.50 (clear the credit balance)\n'
                '• Cash credit $10.50 (money leaves the bank)\n'
                'The return cycle is now complete: item returned, scrapped, customer refunded.'
            ),
        },
        # ── Aging ─────────────────────────────────────────────────────
        {
            'step': 13,
            'title': 'Pay vendor — $66.00 AP',
            'instruction': 'Pay the $66.00 owed to the vendor for the 11 received units.',
            'action': 'vendor_payment',
            'amount': 66.00,
            'section': 'Settlement',
            'expected_gl': [
                {'account': 'LIAB-ACCTSPAY-000', 'side': 'debit', 'amount': 66.00,
                 'purpose': 'AP cleared — vendor paid'},
                {'account': 'ASSET-CASH-000', 'side': 'credit', 'amount': 66.00,
                 'purpose': 'Cash outflow to vendor'},
            ],
            'explanation': (
                'We owe the vendor $66 from step 6 (11 units × $6.00). Pay it.\n'
                '• AP debit $66.00 (we no longer owe the vendor)\n'
                '• Cash credit $66.00 (money leaves the bank)\n'
                'AP is now zero. All vendor obligations settled.'
            ),
        },
        # ── Cleanup ───────────────────────────────────────────────────
        {
            'step': 14,
            'title': 'Cancel remaining proposal (6 units)',
            'instruction': 'Cancel the 6 units still sitting on the original proposal.',
            'action': 'cancel_proposal_remainder',
            'qty': 6,
            'section': 'Cleanup',
            'expected_quantity': {
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_p': 0,
                'allocated': 5, 'available': 102,
            },
            'expected_pending': [
                {'purpose': 'on_p', 'delta': '-6'},
            ],
            'expected_gl': [],
            'explanation': (
                'The remaining 6 proposal units are stale — cancel them.\n'
                'On_p drops from 6→0. No GL impact (proposals never had financial weight).\n'
                'This is housekeeping — orphan proposals clutter reports and confuse users.'
            ),
        },
        {
            'step': 15,
            'title': 'Close remaining SO (5) and PO (3)',
            'instruction': 'Close the 5 remaining order units and 3 remaining PO units.',
            'action': 'close_orphans',
            'section': 'Cleanup',
            'exit_point': {
                'name': 'Clean Books',
                'summary': 'All orphans cleared. Books are clean: on_hand=107, available=107, no open commitments.',
            },
            'expected_quantity': {
                'on_hand': 107, 'on_so': 0, 'on_po': 0, 'on_p': 0,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_so', 'delta': '-5'},
                {'purpose': 'on_po', 'delta': '-3'},
            ],
            'expected_gl': [],
            'explanation': (
                'Close the remaining open commitments:\n'
                '• SO: 5 units cancelled (on_so 5→0)\n'
                '• PO: 3 units cancelled (on_po 3→0)\n'
                'No GL — these were commitments, not financial events.\n'
                'Available goes from 102→107. All inventory is free.\n\n'
                'The books are clean. Every transaction from proposal to cleanup '
                'is accounted for. No orphans, no dangling commitments.'
            ),
        },
    ]

    # Summary: what happened across the full lifecycle
    invoice_summary = {
        'invoice_total': 42.00,
        'breakdown': [
            {'source': 'Revenue', 'amount': 40.00},
            {'source': 'Sales Tax', 'amount': 2.00},
        ],
        'settlement': [
            {'method': 'Cash received', 'amount': 30.00},
            {'method': 'Discount given', 'amount': 10.00},
            {'method': 'Written off', 'amount': 2.00},
        ],
        'settlement_total': 42.00,
        'margin_analysis': {
            'revenue': 30.00,       # $40 original - $10 return reversal
            'cogs': 18.00,          # $24 original - $6 return reversal
            'gross_margin': 12.00,
            'commission': 2.00,
            'discount': 10.00,
            'bad_debt': 2.00,
            'scrap': 6.00,
            'refund_cash': 10.50,
            'net_margin': -8.50,
            'margin_pct': -28.3,    # -$8.50 / $30 net revenue
            'note': (
                'Started at 40% gross margin on 4 units ($16/$40). After return, scrap, '
                'commission, discount, write-off, and refund: -28.3% net. The return + scrap '
                'turned a thin profit into a loss. This is why Alice tracks erosion at every stage.'
            ),
        },
        'cash_position': {
            'cash_in': 30.00,       # customer payment
            'cash_out': 76.50,      # vendor $66 + refund $10.50
            'net_cash': -46.50,
            'note': 'We collected $30 and paid out $76.50. Net cash is negative because we bought 11 units but only kept revenue on 3.',
        },
    }

    return {
        'steps': steps,
        'invoice_summary': invoice_summary,
        'config': {
            'unit_price': 10.00,
            'unit_cost': 6.00,
            'tax_rate': float(TAX_RATE),
            'commission_rate': float(COMMISSION_RATE),
            'starting_on_hand': 100,
        },
        'gl_accounts': DEFAULTS,
    }


def get_payment_flight_scenario() -> Dict[str, Any]:
    """Payment Lifecycle flight scenario.

    Walks through the full payment flow that WC2 handled via Make_Payment,
    PaymentCreate, ApplyPayments, and Ledger_PaySave:

      1. Create Order for 10 units at $10 = $100
      2. Invoice 6 of the 10 = $63 (with 5% tax)
      3. Accept payment of $80 (tendered $100 cash, change $20)
      4. Apply $50 of the $80 to the $63 invoice
      5. Journal the payment (post GL entries)
      6. Check ledger — available $30, invoice balance $13
      7. Apply remaining $13 to close the invoice
      8. Remaining $17 available — unapplied on account

    Key fields demonstrated: amount, available, tendered, change.
    Key behaviors: available decrements on apply, ledger tracks available not amount.
    """
    unit_price = Decimal('10.00')
    unit_cost = Decimal('6.00')

    steps = [
        {
            'step': 1,
            'title': 'Create Order — 10 units × $10.00',
            'instruction': 'Create an Order with 10 units of the training item at $10.00 each. Total = $100.00.',
            'action': 'create_order',
            'qty': 10,
            'expected_payment': None,
            'expected_gl': [],
            'explanation': (
                'No financial event yet. The order is a commitment — 10 units reserved (on_so=10). '
                'No payment fields involved. No GL impact.'
            ),
        },
        {
            'step': 2,
            'title': 'Invoice 6 of 10 — partial shipment',
            'instruction': 'Create an Invoice from the Order for 6 of the 10 units. Invoice total = $63.00 (6 × $10 + 5% tax).',
            'action': 'create_invoice_from_order',
            'qty': 6,
            'expected_invoice': {
                'subtotal': 60.00,
                'tax': 3.00,
                'total': 63.00,
                'balance_due': 63.00,
            },
            'expected_gl': [
                {'account': 'ASSET-AR-000', 'side': 'debit', 'amount': 63.00,
                 'purpose': 'AR — customer owes $63'},
                {'account': 'REV-SALES-000', 'side': 'credit', 'amount': 60.00,
                 'purpose': 'Revenue — 6 × $10'},
                {'account': 'LIAB-SALESTAX-000', 'side': 'credit', 'amount': 3.00,
                 'purpose': 'Sales Tax — 5% × $60'},
                {'account': 'COGS-PRODUCTS-000', 'side': 'debit', 'amount': 36.00,
                 'purpose': 'COGS — 6 × $6'},
                {'account': 'ASSET-INVENTORY-000', 'side': 'credit', 'amount': 36.00,
                 'purpose': 'Inventory reduction'},
            ],
            'explanation': (
                'THIS is the financial event. 6 units ship. Invoice created for $63.\n'
                'GL records the sale. AR = $63. Revenue = $60. Tax = $3.\n'
                'The remaining 4 units stay on the order (on_so=4).'
            ),
        },
        {
            'step': 3,
            'title': 'Accept Payment — $80 (tendered $100 cash)',
            'instruction': (
                'Create a Payment record:\n'
                '• amount = $80.00 (what they\'re paying)\n'
                '• tendered = $100.00 (what they handed over)\n'
                '• change = $20.00 (auto-computed)\n'
                '• available = $80.00 (auto-set = amount on creation)\n\n'
                'Do NOT apply it to the invoice yet. This is just accepting the money.'
            ),
            'action': 'create_payment',
            'amount': 80.00,
            'tendered': 100.00,
            'expected_payment': {
                'amount': 80.00,
                'available': 80.00,
                'tendered': 100.00,
                'change': 20.00,
                'status': 'completed',
            },
            'expected_gl': [
                {'account': 'ASSET-CASH-000', 'side': 'debit', 'amount': 80.00,
                 'purpose': 'Cash received (amount, not tendered)'},
                {'account': 'ASSET-AR-000', 'side': 'credit', 'amount': 80.00,
                 'purpose': 'AR reduced by payment amount'},
            ],
            'explanation': (
                'Customer hands over $100 cash for an $80 payment. Change = $20.\n\n'
                'Key fields on Payment record:\n'
                '• amount = $80 — the real payment amount\n'
                '• tendered = $100 — what the customer physically gave\n'
                '• change = $20 — computed: tendered - amount\n'
                '• available = $80 — starts equal to amount, decrements as applied\n\n'
                'WC2 equivalent: [Payment]amount, [Payment]amountAvailable, '
                '[Payment]tendered, [Payment]change\n\n'
                'The payment exists but is NOT yet applied to the invoice. '
                'The customer has $80 on account.'
            ),
        },
        {
            'step': 4,
            'title': 'Apply $50 to Invoice',
            'instruction': (
                'Apply $50 of the $80 payment to the $63 invoice.\n\n'
                'After this step:\n'
                '• Payment.available drops from $80 → $30\n'
                '• Invoice balance drops from $63 → $13\n'
                '• Ledger value_available updates to -$30 (tracks unapplied)\n'
                '• PendingPaymentApplication record created'
            ),
            'action': 'apply_payment_to_invoice',
            'amount': 50.00,
            'expected_payment': {
                'amount': 80.00,
                'available': 30.00,
                'tendered': 100.00,
                'change': 20.00,
            },
            'expected_invoice': {
                'total': 63.00,
                'received': 50.00,
                'balance_due': 13.00,
                'status': 'partially_paid',
            },
            'expected_gl': [],
            'explanation': (
                'Partial application. We take $50 of the $80 and apply it to the $63 invoice.\n\n'
                'What changes:\n'
                '• Payment.available: $80 → $30 (decremented by apply amount)\n'
                '• Invoice.totals.received: $0 → $50\n'
                '• Invoice.totals.balance: $63 → $13\n'
                '• Invoice status: "sent" → "partially_paid"\n'
                '• Ledger value_available: -$80 → -$30 (on next payment save)\n\n'
                'What does NOT change:\n'
                '• Payment.amount stays $80 (immutable — the original payment)\n'
                '• Payment.tendered stays $100\n'
                '• Payment.change stays $20\n\n'
                'WC2: This is the ApplyPayments dialog. The user picks invoices '
                'and allocates payment dollars across them. amountAvailable tracked '
                'how much was left to allocate.'
            ),
        },
        {
            'step': 5,
            'title': 'Journal the Payment',
            'instruction': (
                'Post the payment to the GL (user-initiated action).\n\n'
                'This creates GlJournal records from the staged metadata.gl_accounts.\n'
                'The payment is now locked — can only be reversed, not edited.'
            ),
            'action': 'post_gl',
            'expected_gl': [
                {'account': 'ASSET-CASH-000', 'side': 'debit', 'amount': 80.00,
                 'purpose': 'Cash receipt — full payment amount'},
                {'account': 'ASSET-AR-000', 'side': 'credit', 'amount': 80.00,
                 'purpose': 'AR reduction — full payment amount'},
            ],
            'explanation': (
                'GL journals are created. The payment is now part of the permanent record.\n\n'
                'Note: GL posts the FULL payment amount ($80), not the applied amount ($50). '
                'The journal captures the cash event. The application captures the allocation. '
                'These are two different things:\n'
                '• Cash event: "Customer gave us $80" → GL\n'
                '• Allocation: "We applied $50 to Invoice #X" → PaymentApplication\n\n'
                'The ledger tracks available ($30) for aging and credit calculations. '
                'The GL tracks the full amount for financial statements.'
            ),
        },
        {
            'step': 6,
            'title': 'Check the Ledger',
            'instruction': (
                'Verify the ledger state for this customer:\n\n'
                '• Invoice ledger: value_original = +$63, value_available = +$13\n'
                '• Payment ledger: value_original = -$80, value_available = -$30\n'
                '• Net ledger = $13 - $30 = -$17 (customer has $17 credit)\n\n'
                'Org financial should show:\n'
                '• balance_due = -$17 (net of invoice + payment ledgers)\n'
                '• available_payments = $30 (unapplied payment on account)'
            ),
            'action': 'check_ledger',
            'expected_ledger': {
                'invoice_value_original': 63.00,
                'invoice_value_available': 13.00,
                'payment_value_original': -80.00,
                'payment_value_available': -30.00,
                'net': -17.00,
            },
            'explanation': (
                'The ledger is the single source of truth for AR aging.\n\n'
                'WC2 equivalent: Ledger_TallyBal computed:\n'
                '• balanceDue from SUM(unAppliedValue) across all ledger records\n'
                '• balanceAvailablePayments from SUM(amountAvailable) on Payment\n'
                '• totalExposure = balanceDue + openOrders\n\n'
                'WC3 does the same in update_org_balances():\n'
                '• Reads all Ledger records for org → aging buckets\n'
                '• Reads Payment.available WHERE > 0 → available_payments\n'
                '• total_exposure = balance_due + open_orders - available_payments'
            ),
        },
        {
            'step': 7,
            'title': 'Apply remaining $13 — close the invoice',
            'instruction': (
                'Apply $13 more of the payment to the invoice.\n\n'
                'After this step:\n'
                '• Payment.available: $30 → $17\n'
                '• Invoice balance: $13 → $0\n'
                '• Invoice status: "partially_paid" → "paid"\n'
                '• $17 remains unapplied on account'
            ),
            'action': 'apply_payment_to_invoice',
            'amount': 13.00,
            'expected_payment': {
                'amount': 80.00,
                'available': 17.00,
            },
            'expected_invoice': {
                'total': 63.00,
                'received': 63.00,
                'balance_due': 0.00,
                'status': 'paid',
            },
            'explanation': (
                'Invoice is fully paid. The $17 remaining on the payment is unapplied.\n\n'
                'This is common in commerce: customer overpays, or pays a round number. '
                'The excess stays on account as available_payments. It can be:\n'
                '• Applied to the next invoice\n'
                '• Refunded\n'
                '• Left on account as a credit\n\n'
                'WC2 tracked this with balanceAvailablePayments on Customer. '
                'WC3 tracks it with Payment.available and org.financial.available_payments.'
            ),
        },
        {
            'step': 8,
            'title': 'Summary — the payment lifecycle',
            'instruction': 'Review what happened across all 7 steps.',
            'action': None,
            'exit_point': {
                'name': 'Payment Lifecycle Complete',
                'summary': (
                    'Order $100 → Invoice $63 (partial) → Payment $80 (tendered $100, change $20) '
                    '→ Apply $50 → Journal → Apply $13 → Invoice paid, $17 on account.'
                ),
            },
            'explanation': (
                'The four payment fields and their roles:\n\n'
                '| Field     | Created | After apply $50 | After apply $13 |\n'
                '|-----------|---------|-----------------|------------------|\n'
                '| amount    | $80     | $80             | $80              |\n'
                '| available | $80     | $30             | $17              |\n'
                '| tendered  | $100    | $100            | $100             |\n'
                '| change    | $20     | $20             | $20              |\n\n'
                'amount and tendered are immutable (what happened). '
                'available is the working field (what\'s left to allocate). '
                'change is computed (tendered - amount).\n\n'
                'The ledger tracks available, not amount. This is how WC2 worked '
                '(aLdgValue = -amountAvailable) and now WC3 matches.'
            ),
        },
    ]

    return {
        'steps': steps,
        'config': {
            'unit_price': 10.00,
            'unit_cost': 6.00,
            'tax_rate': float(TAX_RATE),
            'starting_on_hand': 100,
        },
        'gl_accounts': DEFAULTS,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dec(val) -> float:
    """Safely convert a value to float."""
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _get_proposal_lines(item_id: int, item_dict: dict) -> list:
    """Get all proposal lines for this item."""
    try:
        ProposalLine = dj_apps.get_model('transactions', 'ProposalLine')
    except LookupError:
        return []

    lines = []
    for pl in ProposalLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
        qty = _line_qty(pl)
        price = _line_price(pl)
        lines.append({
            'type': 'proposal_line',
            'id': pl.pk,
            'parent_id': pl.proposal_id,
            'parent_ida': getattr(pl.proposal, 'ida', '') if hasattr(pl, 'proposal') else '',
            'parent_model': 'proposal',
            'quantity': qty,
            'price': price,
            'status': getattr(pl, 'status', ''),
            'dt_created': getattr(pl, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Proposal — no GL impact (quote only)',
                'entries': [],
            },
        })
    return lines


def _get_order_lines(item_id: int, item_dict: dict) -> list:
    try:
        OrderLine = dj_apps.get_model('transactions', 'OrderLine')
    except LookupError:
        return []

    lines = []
    for ol in OrderLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
        qty = _line_qty(ol)
        price = _line_price(ol)
        lines.append({
            'type': 'order_line',
            'id': ol.pk,
            'parent_id': ol.order_id,
            'parent_ida': getattr(ol.order, 'ida', '') if hasattr(ol, 'order') else '',
            'parent_model': 'order',
            'quantity': qty,
            'price': price,
            'status': getattr(ol, 'status', ''),
            'dt_created': getattr(ol, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Order — no GL impact (commitment only)',
                'entries': [],
            },
        })
    return lines


def _get_invoice_lines(item_id: int, item_dict: dict) -> list:
    try:
        InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')
    except LookupError:
        return []

    unit_cost = Decimal(str(item_dict['cost']['standard'] or item_dict['cost']['avg'] or 0))
    gl = item_dict['gls']

    lines = []
    for il in InvoiceLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
        qty = _line_qty(il)
        price = _line_price(il)
        active_qty = Decimal(str(qty.get('active', qty.get('staged', 0)) or 0))
        extended = Decimal(str(price.get('extended', 0) or 0))

        if extended == 0 and active_qty > 0:
            unit_price = Decimal(str(price.get('unit', price.get('base', 0)) or 0))
            extended = unit_price * active_qty

        tax_amount = (extended * TAX_RATE).quantize(Decimal('0.01'))
        ar_total = extended + tax_amount
        cogs_amount = unit_cost * active_qty
        commission_amount = (extended * COMMISSION_RATE).quantize(Decimal('0.01'))

        entries = []
        if extended > 0:
            entries = [
                {'account': DEFAULTS['ar'], 'side': 'debit',
                 'amount': float(ar_total), 'purpose': f'AR ({active_qty} × price + {float(TAX_RATE)*100}% tax)'},
                {'account': gl['revenue'], 'side': 'credit',
                 'amount': float(extended), 'purpose': f'Revenue ({active_qty} × unit price)'},
                {'account': DEFAULTS['tax_payable'], 'side': 'credit',
                 'amount': float(tax_amount), 'purpose': f'Sales Tax ({float(TAX_RATE)*100}% × ${float(extended)})'},
            ]
            if cogs_amount > 0:
                entries.extend([
                    {'account': gl['cogs'], 'side': 'debit',
                     'amount': float(cogs_amount), 'purpose': f'COGS ({active_qty} × ${float(unit_cost)})'},
                    {'account': gl['inventory'], 'side': 'credit',
                     'amount': float(cogs_amount), 'purpose': 'Inventory reduction'},
                ])
            if commission_amount > 0:
                entries.extend([
                    {'account': DEFAULTS['commission_exp'], 'side': 'debit',
                     'amount': float(commission_amount), 'purpose': f'Commission ({float(COMMISSION_RATE)*100}% × ${float(extended)})'},
                    {'account': DEFAULTS['commission_pay'], 'side': 'credit',
                     'amount': float(commission_amount), 'purpose': 'Commission payable to rep'},
                ])

        lines.append({
            'type': 'invoice_line',
            'id': il.pk,
            'parent_id': il.invoice_id,
            'parent_ida': getattr(il.invoice, 'ida', '') if hasattr(il, 'invoice') else '',
            'parent_model': 'invoice',
            'quantity': qty,
            'price': price,
            'status': getattr(il, 'status', ''),
            'dt_created': getattr(il, 'dt_created', None),
            'gl_impact': {
                'has_impact': extended > 0,
                'reason': 'Invoice — AR/Revenue/Tax/COGS/Inventory/Commission' if extended > 0 else 'Invoice — $0 line, no GL',
                'entries': entries,
            },
        })
    return lines


def _get_purchase_lines(item_id: int, item_dict: dict) -> list:
    try:
        PurchaseLine = dj_apps.get_model('transactions', 'PurchaseLine')
    except LookupError:
        return []

    gl = item_dict['gls']
    lines = []
    for pl in PurchaseLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
        qty = _line_qty(pl)
        cost = getattr(pl, 'cost', None) or getattr(pl, 'price', None) or {}
        if isinstance(cost, dict):
            cost_dict = cost
        else:
            cost_dict = {}
        extended = Decimal(str(cost_dict.get('extended', 0) or 0))

        # PO line has no GL until received
        lines.append({
            'type': 'purchase_line',
            'id': pl.pk,
            'parent_id': pl.purchase_id,
            'parent_ida': getattr(pl.purchase, 'ida', '') if hasattr(pl, 'purchase') else '',
            'parent_model': 'purchase',
            'quantity': qty,
            'price': cost_dict,
            'status': getattr(pl, 'status', ''),
            'dt_created': getattr(pl, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Purchase Order — no GL impact until goods are received',
                'entries': [],
                'on_receipt': [
                    {'account': gl['inventory'], 'side': 'debit',
                     'amount': float(extended), 'purpose': 'Inventory increase (when received)'},
                    {'account': DEFAULTS['ap'], 'side': 'credit',
                     'amount': float(extended), 'purpose': 'AP (owed to vendor, when received)'},
                ] if extended > 0 else [],
            },
        })
    return lines


def _get_workorder_lines(item_id: int, item_dict: dict) -> list:
    try:
        WorkOrderLine = dj_apps.get_model('transactions', 'WorkOrderLine')
    except LookupError:
        return []

    lines = []
    for wl in WorkOrderLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
        qty = _line_qty(wl)
        lines.append({
            'type': 'workorder_line',
            'id': wl.pk,
            'parent_id': wl.workorder_id if hasattr(wl, 'workorder_id') else None,
            'parent_ida': '',
            'parent_model': 'workorder',
            'quantity': qty,
            'price': {},
            'status': getattr(wl, 'status', ''),
            'dt_created': getattr(wl, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Work Order — GL impact on completion (BOM build)',
                'entries': [],
            },
        })
    return lines


def _get_pending_records(item_id: int) -> list:
    Pending = dj_apps.get_model('core', 'Pending')
    records = []
    for p in Pending.objects.filter(
        record_id=str(item_id),
    ).order_by('-dt_created')[:50]:
        records.append({
            'id': p.pk,
            'model_name': p.model_name or '',
            'purpose': p.purpose if hasattr(p, 'purpose') else (p.name or ''),
            'changes': p.changes if isinstance(p.changes, list) else [],
            'is_processed': p.is_processed(),
            'dt_created': getattr(p, 'dt_created', None),
            'dt_processed': p.dt_processed,
        })
    return records


def _line_active_qty(line) -> float:
    """Extract the active quantity from a line as a float."""
    qty = getattr(line, 'quantity', None)
    if isinstance(qty, dict):
        return float(qty.get('active', qty.get('staged', 0)) or 0)
    if isinstance(qty, (int, float)):
        return float(qty)
    return 0.0


def _line_qty(line) -> dict:
    """Extract quantity dict from a line, handling both dict and scalar."""
    qty = getattr(line, 'quantity', None)
    if isinstance(qty, dict):
        return qty
    if isinstance(qty, (int, float)):
        return {'active': float(qty), 'staged': float(qty)}
    return {}


def _line_price(line) -> dict:
    """Extract price dict from a line."""
    price = getattr(line, 'price', None)
    if isinstance(price, dict):
        return price
    return {}
