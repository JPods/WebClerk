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
}

TAX_RATE = Decimal('0.05')       # 5%
COMMISSION_RATE = Decimal('0.05')  # 5%


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
    ]

    # Summary: what happened to the $42 invoice
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
            'revenue': 40.00,
            'cogs': 24.00,
            'gross_margin': 16.00,
            'commission': 2.00,
            'discount': 10.00,
            'bad_debt': 2.00,
            'net_margin': 2.00,
            'margin_pct': 5.0,  # $2 / $40 = 5%
            'note': 'Started at 40% gross margin ($16/$40). After commission, discount, and write-off: 5% net. This is why Alice tracks erosion.',
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
