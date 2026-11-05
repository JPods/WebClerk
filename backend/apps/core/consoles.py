"""The consoles as shipped: each becomes a Setting, purpose 'wc:console' (seed_consoles).

Readme 100 (Bill and wc3, 2026-11-01): a console is configuration, not code — few records, each
a combination of models. The flight simulator reads its simulations and their steps from these
Settings; this module is the shipped default the seed writes, and the only place the scenario
text lives (it was in FlightSimConsole.tsx's SIMULATIONS and in two service modules the
console never called; readme 104, 105 — Bill, 2026-11-05: wire the steps in, not delete them).

A console: {sequence, kind, description, needs_item, first_model, steps[]}; a step:
{step, title, instruction, action, model?, explanation?, expected_*?, exit_point?}.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from apps.products.services.inventory.inventory_flight_sim import (
    COMMISSION_RATE, _gl_defaults, _money_breakdown, _pct, _r2, sim_rates)

PURPOSE = 'wc:console'

#: The simulations, in the order the console lists them. needs_item: the simulator tracks the
#: one item the user chooses; first_model: the record the right panel opens with.
CONSOLES: List[Dict[str, Any]] = [
    {'id': 'first-customer', 'label': '1. Your First Customer', 'needs_item': False, 'first_model': 'contact',
     'description': 'Create a Contact, Customer Org, and set credit limit — the foundation for all transactions'},
    {'id': 'first-item', 'label': '2. Your First Item', 'needs_item': True, 'first_model': 'item',
     'description': 'Create an Item with price ($10), cost ($6), GL accounts, and 100 units opening inventory'},
    {'id': 'first-sale', 'label': '3. Your First Sale', 'needs_item': True, 'first_model': 'quote',
     'description': 'Create a Quote for 15 units, convert 9 to an Order — watch on_qt and on_so change'},
    {'id': 'inventory', 'label': '4. Inventory Quantity Tracking', 'needs_item': True, 'first_model': 'quote',
     'description': 'Quote → Order → Invoice → Purchase → Receive — watch on_hand, on_so, on_po, pending, and GL change at each step'},
    {'id': 'cash', 'label': 'Cash Flow Tracking', 'needs_item': True, 'first_model': 'invoice',
     'description': 'Invoice → Cash → Discount → Write-off — watch cash, AR, and bank reconciliation'},
    {'id': 'cash-lifecycle', 'label': 'Cash Lifecycle', 'needs_item': True, 'first_model': 'order',
     'description': 'Order → partial Invoice → accept Cash → apply part to invoice → journal — watch amount, available, tendered, change, ledger, and GL'},
    {'id': 'gl-audit', 'label': 'GL Audit Trail', 'needs_item': True, 'first_model': 'invoice',
     'description': 'Every business event creates balanced journal entries — trace any balance to its source'},
    {'id': 'bom', 'label': 'Bill of Materials', 'needs_item': True, 'first_model': 'workorder',
     'description': 'BOM explosion, component availability, buildable quantity, cost rollup'},
    {'id': 'p2p', 'label': 'Purchase-to-Pay', 'needs_item': True, 'first_model': 'purchase',
     'description': 'Requisition → PO → Receive → Three-way match → Pay vendor'},
    {'id': 'commissions', 'label': 'Commission Tracking', 'needs_item': True, 'first_model': 'invoice',
     'description': 'Accrual at sale, split commissions, adjustments at cash, period-end reconciliation'},
    {'id': 'currency', 'label': 'Currency Variations', 'needs_item': True, 'first_model': 'invoice',
     'description': 'Multi-currency transactions, exchange rate gains/losses, period-end revaluation'},
    {'id': 'costing', 'label': 'Costing Methods', 'needs_item': True, 'first_model': 'purchase',
     'description': 'Same transactions, three different profit numbers — FIFO vs LIFO vs weighted average'},
    {'id': 'company-profile', 'label': 'Company Profile Setup', 'needs_item': False, 'first_model': 'setting',
     'description': 'Configure your company name, address, ship-to, logos, print defaults, receivables, and accounting — the foundation every document and report reads from'},
    {'id': 'admin-tools', 'label': 'Admin Tools & Field Behaviors', 'needs_item': False, 'first_model': '',
     'description': 'Run audit tools, review field behavior detection, Cmd+Shift+click to override — the incremental correction loop'},
]


# ── Sim 1: Your First Customer ──────────────────────────────────────────

def get_first_customer_scenario() -> Dict[str, Any]:
    """Your First Customer — Contact → Customer Org → Credit limit.

    The user creates a real contact and customer org. The flight sim
    watches the records appear and shows what each field means.
    """
    steps = [
        {
            'step': 1,
            'title': 'Create a Contact',
            'instruction': (
                'Open the right panel form (Contact). Fill in:\n'
                '• First name: Training\n'
                '• Last name: User\n'
                '• Email: training@example.com\n\n'
                'Save the record.'
            ),
            'action': 'create_contact',
            'model': 'contact',
            'expected_fields': {
                'name_first': 'Training',
                'name_last': 'User',
                'email': 'training@example.com',
            },
            'explanation': (
                'A Contact is a person. Every user, customer rep, vendor rep, and employee '
                'is a Contact record. The Contact IS the login — email is the username.\n\n'
                'Contacts are independent of orgs. One person can be a rep for multiple '
                'companies. The org relationship is separate (assigned_to on projects, '
                'contact FK on cash and invoices).\n\n'
                'WC2: This was the Customer table. WC3 separates people (Contact) from '
                'companies (OrgBase). A customer is a company, not a person.'
            ),
        },
        {
            'step': 2,
            'title': 'Create a Customer Org',
            'instruction': (
                'Open the right panel form (Customer). Fill in:\n'
                '• Display name: Training Corp\n'
                '• Type: end_user\n\n'
                'Save the record.'
            ),
            'action': 'create_customer',
            'model': 'customer',
            'expected_fields': {
                'company': 'Training Corp',
                'org_type': 'customer',
                'type': 'end_user',
            },
            'explanation': (
                'An Org is a company. Customer, Vendor, Manufacturer, Rep, Employee — all '
                'are the same OrgBase model with different org_type values. This means:\n\n'
                '• A company can be both your customer AND your vendor\n'
                '• Financial data is stored per org_type in the financial JSON\n'
                '• The DataBrowser shows each type as a separate view\n\n'
                'The org_type determines which financial fields matter:\n'
                '• Customer → AR aging, credit limit, days_avg_paid\n'
                '• Vendor → AP aging, cash terms, lead time\n\n'
                'WC2 had separate Customer, Vendor, Manufacturer, Rep tables. '
                'WC3 unified them into OrgBase with typed proxies.'
            ),
        },
        {
            'step': 3,
            'title': 'Set Credit Limit',
            'instruction': (
                'On the Customer record, find the financial section. Set:\n'
                '• Credit limit: $5,000\n'
                '• Terms: Net 30\n\n'
                'Save the record.\n\n'
                'After saving, check the financial data:\n'
                '• balance_due should be $0\n'
                '• available credit should be $5,000\n'
                '• high_credit should be $0'
            ),
            'action': 'set_credit',
            'model': 'customer',
            'expected_financial': {
                'customer': {
                    'credit': {
                        'limit': 5000.00,
                        'available': 5000.00,
                        'used': 0.00,
                    },
                    'balances': {
                        'due': 0.00,
                        'current': 0.00,
                    },
                    'high_credit': 0.00,
                    'available_cash_entries': 0.00,
                    'total_exposure': 0.00,
                    'days_avg_paid': 0,
                },
            },
            'explanation': (
                'Credit limit controls whether new orders are accepted. The formula:\n\n'
                '  credit_available = credit_limit - balance_due\n\n'
                'When a customer places an order, WC3 checks:\n'
                '  total_exposure = balance_due + open_orders - available_cash_entries\n\n'
                'If total_exposure > credit_limit, the order can be held for review.\n\n'
                'The financial JSON stores all of this per org_type. A company that is '
                'both customer and vendor has separate financial sections:\n'
                '  org.financial.customer.credit.limit = 5000\n'
                '  org.financial.vendor.balances.due = 1200\n\n'
                'These are independent — vendor debt doesn\'t affect customer credit.\n\n'
                'WC2: [Customer]creditLimit, [Customer]balanceDue, [Customer]highCredit'
            ),
        },
        {
            'step': 4,
            'title': 'Link Contact to Customer',
            'instruction': (
                'On the Customer record, find the contacts section.\n'
                'Add the Training User contact as a contact for Training Corp.\n\n'
                'This means Training User is a representative of Training Corp. '
                'When you create an invoice for Training Corp, Training User will '
                'appear as a contact option.'
            ),
            'action': 'link_contact',
            'model': 'customer',
            'exit_point': {
                'name': 'Foundation: Customer Ready',
                'summary': (
                    'You have a Contact (person), a Customer Org (company), '
                    'credit limit set, and the person linked to the company. '
                    'This customer is ready for transactions.'
                ),
            },
            'explanation': (
                'Contacts and Orgs are many-to-many. One person can represent multiple '
                'companies. One company can have multiple contacts.\n\n'
                'The link carries a role (buyer, AP clerk, owner, etc.) which feeds '
                'into RBAC — a buyer can place orders but not approve cash_entries.\n\n'
                'When you create a transaction (order, invoice, cash), the contact '
                'field determines who to notify. The customer field determines who to bill.\n\n'
                'Verify in DataBrowser: open the Contact record. The orgs section should '
                'show Training Corp. Open the Customer record. The contacts section '
                'should show Training User.'
            ),
        },
    ]

    return {
        'id': 'first-customer',
        'label': 'Your First Customer',
        'steps': steps,
        'models_used': ['contact', 'customer'],
        'prerequisite': None,
        'next_sim': 'first-item',
    }


# ── Sim 2: Your First Item ─────────────────────────────────────────────

def get_first_item_scenario() -> Dict[str, Any]:
    """Your First Item — Item → Price/Cost/GL → Opening inventory.

    The user creates the training item that all later flight sims use.
    """
    steps = [
        {
            'step': 1,
            'title': 'Create an Item',
            'instruction': (
                'Open the right panel form (Item). Fill in:\n'
                '• IDA: qqBB200 (the training item ID)\n'
                '• Name: Training Widget\n'
                '• Description: Standard training item for flight simulator exercises\n\n'
                'Save the record.'
            ),
            'action': 'create_item',
            'model': 'item',
            'expected_fields': {
                'ida': 'qqBB200',
                'name': 'Training Widget',
            },
            'explanation': (
                'An Item is anything you sell or buy. It has:\n'
                '• ida — your internal SKU/part number (must be unique)\n'
                '• name — human-readable description\n'
                '• quantity — JSON with on_hand, on_so, on_po, available, etc.\n'
                '• price — JSON with base price, price levels, breaks\n'
                '• cost — JSON with standard, last, average cost\n'
                '• gls — JSON mapping to GL accounts (revenue, cogs, inventory)\n\n'
                'The ida "qqBB200" starts with "qq" — this is the training prefix. '
                'All flight sim items use qq so they\'re easy to find and clean up.\n\n'
                'WC2: [Item]ida_item, [Item]descpt'
            ),
        },
        {
            'step': 2,
            'title': 'Set Price and Cost',
            'instruction': (
                'On the Item record, set:\n'
                '• Base price: $10.00\n'
                '• Standard cost: $6.00\n\n'
                'These go in the price and cost JSON fields:\n'
                '  price.base = 10.00\n'
                '  cost.standard = 6.00\n\n'
                'Save the record.'
            ),
            'action': 'set_pricing',
            'model': 'item',
            'expected_fields': {
                'price': {'base': 10.00},
                'cost': {'standard': 6.00},
            },
            'explanation': (
                'Price and cost are separate concerns:\n\n'
                '• Price is what you charge the customer (revenue side)\n'
                '• Cost is what you paid the vendor (expense side)\n'
                '• Margin = Price - Cost = $10 - $6 = $4 (40%)\n\n'
                'Both are JSON fields because they hold more than one number:\n'
                '• price.base — the starting price\n'
                '• price.levels — volume breaks, customer-specific pricing\n'
                '• cost.standard — what you expect to pay\n'
                '• cost.last — what you actually paid last time\n'
                '• cost.average — weighted average of all purchases\n\n'
                'The flight sims use $10 price and $6 cost because the math is easy:\n'
                '40% gross margin, 5% tax = $0.50 per unit, 5% commission = $0.50 per unit.\n\n'
                'WC2: [Item]unitPrice, [Item]unitCost'
            ),
        },
        {
            'step': 3,
            'title': 'Set GL Accounts',
            'instruction': (
                'On the Item record, set the GL account mappings:\n'
                '• Revenue: 4000-sales_revenue\n'
                '• COGS: 5000-cost_of_goods_sold\n'
                '• Inventory: 1200-inventory\n\n'
                'These go in the gls JSON field.\n'
                'Save the record.'
            ),
            'action': 'set_gl_accounts',
            'model': 'item',
            'expected_fields': {
                'gls': {
                    'revenue': '4000-sales_revenue',
                    'cogs': '5000-cost_of_goods_sold',
                    'inventory': '1200-inventory',
                },
            },
            'explanation': (
                'Every item maps to three GL accounts:\n\n'
                '• Revenue — where sale dollars go (credit on invoice)\n'
                '• COGS — cost of goods sold (debit on invoice)\n'
                '• Inventory — asset account (credit on sale, debit on receipt)\n\n'
                'When you invoice 4 units of this item at $10, the GL entries are:\n'
                '  DR  AR              $42  (customer owes — includes tax)\n'
                '  CR  4000-sales_revenue   $40  (revenue)\n'
                '  CR  TAX-PAYABLE     $2   (tax)\n'
                '  DR  COGS-PRODUCTS   $24  (4 × $6 cost)\n'
                '  CR  INVENTORY       $24  (asset leaves shelf)\n\n'
                'The GL accounts on the item override the system defaults. If an item '
                'has no GL accounts set, the system defaults apply.\n\n'
                'WC2: [Item]glaccount, mapped via Category → GL in the settings.'
            ),
        },
        {
            'step': 4,
            'title': 'Set Opening Inventory',
            'instruction': (
                'On the Item record, set the quantity:\n'
                '• on_hand: 100\n'
                '• available: 100\n'
                '• All others: 0\n\n'
                'This goes in the quantity JSON field.\n'
                'Save the record.'
            ),
            'action': 'set_inventory',
            'model': 'item',
            'expected_fields': {
                'quantity': {
                    'on_hand': 100,
                    'on_so': 0,
                    'on_po': 0,
                    'on_qt': 0,
                    'on_wo': 0,
                    'available': 100,
                },
            },
            'exit_point': {
                'name': 'Foundation: Item Ready',
                'summary': (
                    'You have an item with price ($10), cost ($6), GL accounts, '
                    'and 100 units on hand. This item is ready for the transaction '
                    'flight simulators.'
                ),
            },
            'explanation': (
                'The quantity JSON tracks inventory across all transaction types:\n\n'
                '| Field     | What it means | Changes when |\n'
                '|-----------|--------------|---------------|\n'
                '| on_hand   | Physically in warehouse | Invoice (down), Receipt (up) |\n'
                '| on_so     | Committed to sales orders | Order (up), Invoice (down) |\n'
                '| on_po     | On order from vendors | PO (up), Receipt (down) |\n'
                '| on_qt      | On quotes (quotes) | Quote (up), Convert (down) |\n'
                '| on_wo     | On work orders | WO (up), Complete (down) |\n'
                '| available | on_hand - allocated | Computed |\n\n'
                'Quotes DON\'T reduce available (they\'re just quotes). '
                'Orders DO reduce available (they\'re commitments). '
                'This is the most important distinction in inventory management.\n\n'
                'Starting at 100 gives us room to run all the flight sim scenarios '
                'without going negative.\n\n'
                'WC2: [Item]QtyOnHand, [Item]QtyOrdered, [Item]QtyOnPO'
            ),
        },
    ]

    return {
        'id': 'first-item',
        'label': 'Your First Item',
        'steps': steps,
        'models_used': ['item'],
        'prerequisite': None,
        'next_sim': 'first-sale',
    }


# ── Sim 3: Your First Sale ─────────────────────────────────────────────

def get_first_sale_scenario() -> Dict[str, Any]:
    """Your First Sale — Quote → Convert to Order.

    Uses the customer from sim 1 and the item from sim 2.
    Bridges Phase 1 into Phase 2 (inventory tracking).
    """
    steps = [
        {
            'step': 1,
            'title': 'Create a Quote',
            'instruction': (
                'Open the right panel form (Quote). Fill in:\n'
                '• Customer: Training Corp (from exercise 1)\n'
                '• Contact: Training User\n\n'
                'Save the header first, then add a line:\n'
                '• Item: qqBB200 (Training Widget)\n'
                '• Quantity: 15\n'
                '• Price: $10.00 (should auto-fill from item)\n\n'
                'Save.'
            ),
            'action': 'create_quote',
            'model': 'quote',
            'qty': 15,
            'expected_quantity_change': {
                'on_qt': '+15',
                'on_hand': '100 (unchanged)',
                'available': '100 (unchanged)',
            },
            'explanation': (
                'A Quote is a quote — a conversation with the customer about what '
                'they might buy. It is NOT a commitment.\n\n'
                'What happens when you save the quote line:\n'
                '• on_qt increases by 15 (we\'re quoting 15 units)\n'
                '• on_hand stays at 100 (nothing moved)\n'
                '• available stays at 100 (quotes don\'t allocate)\n'
                '• NO GL entries (a quote has no financial weight)\n'
                '• A Pending record is created (tracks the quantity delta)\n\n'
                'Why quotes don\'t allocate: imagine quoting 50 units to 10 customers. '
                'If quotes allocated, you\'d need 500 units for $5,000 in quotes — '
                'but most quotes don\'t convert. Quotes are visibility, not commitment.\n\n'
                'WC2: This was the Quote window → [QT_Lines] table.'
            ),
        },
        {
            'step': 2,
            'title': 'Convert to Order — partial (9 of 15)',
            'instruction': (
                'On the Quote, click the Convert to Order button.\n'
                'Change the quantity to 9 (the customer only wants 9 of the 15 quoted).\n\n'
                'The conversion creates a new Order record and copies the line.\n'
                'The quote line quantity drops to 6 remaining.\n\n'
                'Watch the left panel — quantities will change.'
            ),
            'action': 'convert_to_order',
            'model': 'order',
            'qty': 9,
            'expected_quantity_change': {
                'on_qt': '15 → 6 (−9)',
                'on_so': '0 → 9 (+9)',
                'on_hand': '100 (unchanged)',
                'available': '100 → 91 (−9)',
            },
            'explanation': (
                'NOW it\'s a commitment. The conversion:\n\n'
                '1. Creates a new Order header (linked to the quote via refs)\n'
                '2. Copies the line to the order with quantity = 9\n'
                '3. Reduces the quote line to 6 remaining\n'
                '4. Creates Pending records for the quantity changes\n\n'
                'Quantity changes:\n'
                '• on_qt: 15 → 6 (9 units moved from quote to order)\n'
                '• on_so: 0 → 9 (9 units committed to this sales order)\n'
                '• available: 100 → 91 (orders ALLOCATE — these 9 are spoken for)\n'
                '• on_hand: still 100 (nothing has physically moved)\n\n'
                'Still NO GL entries. An order is a promise to deliver, not a delivery. '
                'The financial event happens at invoicing.\n\n'
                'Why partial? Real commerce rarely converts 100% of a quote. '
                'The customer negotiates, reduces quantities, drops items. The 6 remaining '
                'on the quote can convert later, expire, or be cancelled.\n\n'
                'WC2: Convert button in the Quote window → creates [SalesOrder].'
            ),
        },
        {
            'step': 3,
            'title': 'Review the Order',
            'instruction': (
                'The right panel should now show the new Order.\n\n'
                'Verify:\n'
                '• Customer: Training Corp\n'
                '• 1 line: qqBB200 × 9 at $10.00 = $90.00\n'
                '• Status: planned or released\n\n'
                'Check the left panel quantities:\n'
                '• on_hand = 100, on_so = 9, on_qt = 6, available = 91\n\n'
                'This order is ready to invoice (ship).'
            ),
            'action': 'review_order',
            'model': 'order',
            'exit_point': {
                'name': 'Your First Sale Complete',
                'summary': (
                    'You created a quote for 15 units, converted 9 to an order. '
                    'The customer has 9 units committed (on_so=9), 6 still quoted (on_qt=6), '
                    'and 91 units available for other customers.\n\n'
                    'Next: run the "Inventory Quantity Tracking" flight sim to continue '
                    'this order through invoicing, purchasing, and receiving.'
                ),
            },
            'explanation': (
                'Summary of what you\'ve built across the three foundation exercises:\n\n'
                '| Record | What it is | Key insight |\n'
                '|--------|-----------|-------------|\n'
                '| Contact | Training User | People are separate from companies |\n'
                '| Customer | Training Corp | Companies have financial data (credit, aging) |\n'
                '| Item | qqBB200 | Products have price, cost, GL accounts, quantity buckets |\n'
                '| Quote | 15 × $10 | Quotes don\'t allocate inventory |\n'
                '| Order | 9 × $10 | Orders DO allocate inventory |\n\n'
                'The data you created here is the foundation for every flight sim in '
                'Phase 2, 3, and 4. The training item qqBB200 with 100 units on hand '
                'at $10 price / $6 cost is the standard starting point.\n\n'
                'The progression: Contact → Customer → Item → Quote → Order → '
                'Invoice → Cash → GL. Each step adds financial weight. The first '
                'three have none. The quote has visibility only. The order commits. '
                'The invoice is the financial event.'
            ),
        },
    ]

    return {
        'id': 'first-sale',
        'label': 'Your First Sale',
        'steps': steps,
        'models_used': ['quote', 'order'],
        'prerequisite': 'first-item',
        'next_sim': 'inventory',
    }


def get_flight_scenario() -> Dict[str, Any]:
    """Return the scripted training scenario with expected values at each step.

    This is the "lesson plan" — what the user should do and what they
    should see at each step. The UI walks through these steps.
    """
    G = _gl_defaults()
    unit_price = Decimal('10.00')
    unit_cost = Decimal('6.00')
    R = sim_rates()
    tax_pct, ship_pct = _pct(R['tax_rate']), _pct(R['shipping_rate'])
    b = _money_breakdown(4, unit_price, R)                  # the invoice for 4 units
    cogs = _r2(unit_cost * 4)
    commission = _r2(b['goods'] * COMMISSION_RATE)
    paid = Decimal('30.00')
    discount = Decimal('10.00')
    after_pay = b['total'] - paid
    write_off = after_pay - discount
    ret_goods = _r2(unit_price)
    ret_tax = _r2(ret_goods * R['tax_rate'])
    ret_credit = ret_goods + ret_tax                        # shipping on the order is not refunded
    m = lambda x: f"${x:,.2f}"

    steps = [
        {
            'step': 1,
            'title': 'Starting Inventory',
            'instruction': 'Select an item with on_hand = 100, price = $10.00, cost = $6.00',
            'action': None,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 0, 'on_po': 0, 'on_qt': 0,
                'allocated': 0, 'available': 100,
            },
            'expected_gl': [],
            'explanation': 'No transactions yet. All 100 units are available.',
        },
        {
            'step': 2,
            'title': 'Create Quote for 15 units',
            'instruction': 'Create a Quote with 1 line: 15 units of this item at $10.00',
            'action': 'create_quote_line',
            'qty': 15,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 0, 'on_po': 0, 'on_qt': 15,
                'allocated': 0, 'available': 100,
            },
            'expected_gl': [],
            'explanation': 'Quote reserves 15 units (on_qt=15). No GL impact — a quote is just a quote. Available stays 100 because quotes don\'t allocate.',
        },
        {
            'step': 3,
            'title': 'Convert 9 units to Order',
            'instruction': 'Create an Order from the Quote for 9 of the 15 units',
            'action': 'create_order_from_quote',
            'qty': 9,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 9, 'on_po': 0, 'on_qt': 6,
                'allocated': 0, 'available': 100,
            },
            'expected_pending': [
                {'purpose': 'on_so', 'delta': '+9'},
                {'purpose': 'on_qt', 'delta': '-9'},
            ],
            'expected_gl': [],
            'explanation': (
                'Order commits 9 units (on_so=9). Quote drops to 6 remaining. Pending records track '
                'the movement. Still NO GL impact — an order is a commitment, not a financial event.\n\n'
                'Available stays 100. An order does NOT allocate: allocation is a salesperson\'s '
                'deliberate act, made by reading on_hand, available and on_so and deciding which '
                'goods are set aside for whom. available = on_hand − allocated, and nothing but a '
                'person moves allocated.'
            ),
        },
        {
            'step': 4,
            'title': 'Create Invoice for 4 units',
            'instruction': (f'Create an Invoice from the Order for 4 of the 9 units, with tax jurisdiction '
                            f'{R["tax_jurisdiction"]} ({tax_pct}) and ship via {R["ship_via"]} ({ship_pct} of goods)'),
            'action': 'create_invoice_from_order',
            'qty': 4,
            'expected_quantity': {
                'on_hand': 96, 'on_so': 5, 'on_po': 0, 'on_qt': 6,
                'allocated': 0, 'available': 96,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '-4'},
                {'purpose': 'on_so', 'delta': '-4'},
            ],
            'expected_gl': [
                {'account': G['ar'], 'side': 'debit', 'amount': float(b['total']),
                 'purpose': f"Accounts Receivable (goods {m(b['goods'])} + shipping {m(b['shipping'])} + tax {m(b['tax'])} = {m(b['total'])})"},
                {'account': G['revenue'], 'side': 'credit', 'amount': float(b['goods']),
                 'purpose': f"Revenue (4 × {m(unit_price)})"},
                {'account': G['shipping'], 'side': 'credit', 'amount': float(b['shipping']),
                 'purpose': f"Shipping revenue ({ship_pct} × {m(b['goods'])}, {R['ship_via']})"},
                {'account': G['tax_payable'], 'side': 'credit', 'amount': float(b['tax']),
                 'purpose': f"Sales Tax Payable ({tax_pct} × {m(b['goods'])}, {R['tax_jurisdiction']})"},
                {'account': G['cogs'], 'side': 'debit', 'amount': float(cogs),
                 'purpose': f"Cost of Goods Sold (4 × {m(unit_cost)})"},
                {'account': G['inventory'], 'side': 'credit', 'amount': float(cogs),
                 'purpose': 'Inventory reduction (4 units leave the shelf)'},
                {'account': G['commission_exp'], 'side': 'debit', 'amount': float(commission),
                 'purpose': f"Commission Expense ({_pct(COMMISSION_RATE)} × {m(b['goods'])} revenue)"},
                {'account': G['commission_pay'], 'side': 'credit', 'amount': float(commission),
                 'purpose': 'Commission Payable (owed to rep)'},
            ],
            'explanation': (
                'THIS is the financial event. Inventory leaves the shelf (on_hand 100→96). '
                'Order backlog drops (on_so 9→5). GL records the sale:\n'
                f"• AR debit {m(b['total'])} (what the customer owes: goods + shipping + tax)\n"
                f"• Revenue credit {m(b['goods'])} (what we earned on the goods)\n"
                f"• Shipping revenue credit {m(b['shipping'])} ({ship_pct} of goods, carrier {R['ship_via']})\n"
                f"• Tax payable credit {m(b['tax'])} ({tax_pct}, owed to the jurisdiction — 2 × shipping)\n"
                f"• COGS debit {m(cogs)} (cost of what we sold)\n"
                f"• Inventory credit {m(cogs)} (asset leaves the books)\n"
                f"• Commission expense {m(commission)} / payable {m(commission)} (owed to rep)"
            ),
        },
        {
            'step': 5,
            'title': 'Create Purchase for 14 units',
            'instruction': 'Create a Purchase Order for 14 units at $6.00 cost',
            'action': 'create_purchase',
            'qty': 14,
            'expected_quantity': {
                'on_hand': 96, 'on_so': 5, 'on_po': 14, 'on_qt': 6,
                'allocated': 0, 'available': 96,
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
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_qt': 6,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '+11'},
                {'purpose': 'on_po', 'delta': '-11'},
            ],
            'expected_gl': [
                {'account': G['inventory'], 'side': 'debit', 'amount': 66.00,
                 'purpose': 'Inventory increase (11 × $6.00 — goods on the shelf)'},
                {'account': G['ap'], 'side': 'credit', 'amount': 66.00,
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
            'title': f"Partial Payment — {m(paid)} of {m(b['total'])} invoice",
            'instruction': f"Record a {m(paid)} cash against the {m(b['total'])} invoice",
            'action': 'partial_payment',
            'amount': float(paid),
            'expected_gl': [
                {'account': G['cash'], 'side': 'debit', 'amount': float(paid),
                 'purpose': 'Cash received'},
                {'account': G['ar'], 'side': 'credit', 'amount': float(paid),
                 'purpose': f"AR reduced (customer owes {m(after_pay)} remaining)"},
            ],
            'explanation': (
                f"Customer pays {m(paid)} of the {m(b['total'])} owed. No inventory change — this is purely financial.\n"
                f"• Cash debit {m(paid)} (money in the bank)\n"
                f"• AR credit {m(paid)} (reduce what they owe)\n"
                f"Remaining balance: {m(b['total'])} - {m(paid)} = {m(after_pay)}"
            ),
        },
        {
            'step': 8,
            'title': f"Discount — {m(discount)} off remaining balance",
            'instruction': f"Apply a {m(discount)} discount to the remaining {m(after_pay)} balance (a user's decision, recorded as theirs)",
            'action': 'discount',
            'amount': float(discount),
            'expected_gl': [
                {'account': G['discount'], 'side': 'debit', 'amount': float(discount),
                 'purpose': 'Discount given (expense — reduces margin)'},
                {'account': G['ar'], 'side': 'credit', 'amount': float(discount),
                 'purpose': f"AR reduced (customer now owes {m(write_off)})"},
            ],
            'explanation': (
                f"We give the customer a {m(discount)} discount. No inventory change.\n"
                f"• Discount expense debit {m(discount)} (cost of the discount)\n"
                f"• AR credit {m(discount)} (reduce what they owe)\n"
                f"Remaining balance: {m(after_pay)} - {m(discount)} = {m(write_off)}\n"
                'Note: This hits the Discount Expense account, NOT Revenue. '
                f"Revenue stays at {m(b['goods'])} — the discount is tracked separately so you can see margin erosion."
            ),
        },
        {
            'step': 9,
            'title': f"Write-off — dismiss {m(write_off)} remaining balance",
            'instruction': f"Write off the remaining {m(write_off)} as uncollectable (a user's decision, recorded as theirs)",
            'action': 'write_off',
            'amount': float(write_off),
            'exit_point': {
                'name': 'Invoice Settled',
                'summary': f"The invoice is fully settled: {m(paid)} cash + {m(discount)} discount + {m(write_off)} write-off = {m(b['total'])}. You can stop here or continue to see returns, aging, and orphan cleanup.",
            },
            'expected_gl': [
                {'account': G['bad_debt'], 'side': 'debit', 'amount': float(write_off),
                 'purpose': 'Bad Debt expense (cost of uncollectable)'},
                {'account': G['ar'], 'side': 'credit', 'amount': float(write_off),
                 'purpose': 'AR zeroed out (invoice fully settled)'},
            ],
            'explanation': (
                f"The {m(write_off)} remaining isn't worth chasing. Write it off.\n"
                f"• Bad Debt debit {m(write_off)} (expense — money we'll never collect)\n"
                f"• AR credit {m(write_off)} (balance now $0)\n"
                f"The invoice is now fully settled: {m(paid)} cash + {m(discount)} discount + {m(write_off)} write-off = {m(b['total'])}."
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
                'on_hand': 108, 'on_so': 5, 'on_po': 3, 'on_qt': 6,
                'allocated': 0, 'available': 108,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '+1'},
            ],
            'expected_gl': [
                {'account': G['revenue'], 'side': 'debit', 'amount': float(ret_goods),
                 'purpose': f"Revenue reversal (1 × {m(unit_price)})"},
                {'account': G['tax_payable'], 'side': 'debit', 'amount': float(ret_tax),
                 'purpose': f"Sales tax reversal ({tax_pct} × {m(ret_goods)})"},
                {'account': G['ar'], 'side': 'credit', 'amount': float(ret_credit),
                 'purpose': f"Credit memo — customer is owed {m(ret_credit)} (shipping is not refunded)"},
                {'account': G['inventory'], 'side': 'debit', 'amount': 6.00,
                 'purpose': 'Inventory restored (1 × $6.00 — item back on shelf)'},
                {'account': G['cogs'], 'side': 'credit', 'amount': 6.00,
                 'purpose': 'COGS reversal (cost of returned unit)'},
            ],
            'explanation': (
                'Customer sends 1 unit back. The goods and their tax reverse; shipping already done does not:\n'
                f"• Revenue debit {m(ret_goods)} (we un-earn the sale)\n"
                f"• Tax debit {m(ret_tax)} (we un-collect the tax)\n"
                f"• AR credit {m(ret_credit)} (we now owe the customer a credit)\n"
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
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_qt': 6,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '-1'},
            ],
            'expected_gl': [
                {'account': G['scrap'], 'side': 'debit', 'amount': 6.00,
                 'purpose': 'Scrap/loss expense (damaged goods — cost of 1 unit)'},
                {'account': G['inventory'], 'side': 'credit', 'amount': 6.00,
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
            'instruction': f"Issue a refund cash of {m(ret_credit)} against the credit memo.",
            'action': 'refund_cash',
            'amount': float(ret_credit),
            'section': 'Reverse Flow',
            'exit_point': {
                'name': 'Returns Complete',
                'summary': 'Return processed, item scrapped, customer refunded. You can stop here or continue to see aging and orphan cleanup.',
            },
            'expected_gl': [
                {'account': G['ar'], 'side': 'debit', 'amount': float(ret_credit),
                 'purpose': 'Clear credit memo balance'},
                {'account': G['cash'], 'side': 'credit', 'amount': float(ret_credit),
                 'purpose': 'Cash outflow — refund to customer'},
            ],
            'explanation': (
                'Pay the customer what we owe from the credit memo.\n'
                f"• AR debit {m(ret_credit)} (clear the credit balance)\n"
                f"• Cash credit {m(ret_credit)} (money leaves the bank)\n"
                'The return cycle is now complete: item returned, scrapped, customer refunded.'
            ),
        },
        # ── Aging ─────────────────────────────────────────────────────
        {
            'step': 13,
            'title': 'Pay vendor — $66.00 AP',
            'instruction': 'Pay the $66.00 owed to the vendor for the 11 received units.',
            'action': 'vendor_cash',
            'amount': 66.00,
            'section': 'Settlement',
            'expected_gl': [
                {'account': G['ap'], 'side': 'debit', 'amount': 66.00,
                 'purpose': 'AP cleared — vendor paid'},
                {'account': G['cash'], 'side': 'credit', 'amount': 66.00,
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
            'title': 'Cancel remaining quote (6 units)',
            'instruction': 'Cancel the 6 units still sitting on the original quote.',
            'action': 'cancel_quote_remainder',
            'qty': 6,
            'section': 'Cleanup',
            'expected_quantity': {
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_qt': 0,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_qt', 'delta': '-6'},
            ],
            'expected_gl': [],
            'explanation': (
                'The remaining 6 quote units are stale — cancel them.\n'
                'On_p drops from 6→0. No GL impact (quotes never had financial weight).\n'
                'This is housekeeping — orphan quotes clutter reports and confuse users.'
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
                'summary': 'All orphans cleared through close_transaction. Books are clean: '
                           'on_hand=107, available=107, no open commitments.',
            },
            'expected_quantity': {
                'on_hand': 107, 'on_so': 0, 'on_po': 0, 'on_qt': 0,
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
                'Available stays 107 — commitments never touched it. Allocation is the only\n'
                'thing that reduces available, and only a person allocates.\n\n'
                'The books are clean. Every transaction from quote to cleanup '
                'is accounted for. No orphans, no dangling commitments.'
            ),
        },
    ]

    # Summary: what happened across the full lifecycle — every number computed
    revenue = b['goods'] - ret_goods
    net_cogs = cogs - _r2(unit_cost)
    gross_margin = revenue - net_cogs
    scrap = _r2(unit_cost)
    net_margin = gross_margin + b['shipping'] - commission - discount - write_off - scrap
    cash_out = _r2(unit_cost * 11) + ret_credit
    invoice_summary = {
        'invoice_total': float(b['total']),
        'breakdown': [
            {'source': 'Revenue', 'amount': float(b['goods'])},
            {'source': 'Shipping', 'amount': float(b['shipping'])},
            {'source': 'Sales Tax', 'amount': float(b['tax'])},
        ],
        'settlement': [
            {'method': 'Cash received', 'amount': float(paid)},
            {'method': 'Discount given', 'amount': float(discount)},
            {'method': 'Written off', 'amount': float(write_off)},
        ],
        'settlement_total': float(paid + discount + write_off),
        'margin_analysis': {
            'revenue': float(revenue),
            'cogs': float(net_cogs),
            'gross_margin': float(gross_margin),
            'shipping_revenue': float(b['shipping']),
            'commission': float(commission),
            'discount': float(discount),
            'bad_debt': float(write_off),
            'scrap': float(scrap),
            'refund_cash': float(ret_credit),
            'net_margin': float(net_margin),
            'margin_pct': float((net_margin / revenue * 100).quantize(Decimal('0.1'))) if revenue else 0.0,
            'note': (
                f"Net margin = gross margin {m(gross_margin)} + shipping {m(b['shipping'])} − commission {m(commission)} "
                f"− discount {m(discount)} − write-off {m(write_off)} − scrap {m(scrap)} = {m(net_margin)}. "
                'The return + scrap turned a thin profit into a loss. This is why Alice tracks erosion at every stage.'
            ),
        },
        'cash_position': {
            'cash_in': float(paid),
            'cash_out': float(cash_out),
            'net_cash': float(paid - cash_out),
            'note': f"We collected {m(paid)} and paid out {m(cash_out)} (vendor {m(_r2(unit_cost * 11))} + refund {m(ret_credit)}).",
        },
    }

    return {
        'steps': steps,
        'invoice_summary': invoice_summary,
        'config': {
            'unit_price': 10.00,
            'unit_cost': 6.00,
            'tax_jurisdiction': R['tax_jurisdiction'],
            'tax_rate': float(R['tax_rate']),
            'ship_via': R['ship_via'],
            'shipping_rate': float(R['shipping_rate']),
            'commission_rate': float(COMMISSION_RATE),
            'starting_on_hand': 100,
        },
        'gl_accounts': G,
    }


def get_cash_flight_scenario() -> Dict[str, Any]:
    """Cash Lifecycle flight scenario.

    Walks through the full cash flow that WC2 handled via Make_Payment,
    CashCreate, ApplyCash, and Ledger_PaySave:

      1. Create Order for 10 units at $10 = $100
      2. Invoice 6 of the 10 (tax jurisdiction test_8%, ship via test_4%)
      3. Accept cash of $80 (tendered $100 cash, change $20)
      4. Apply $50 of the $80 to the invoice
      5. Journal the cash (post GL entries)
      6. Check ledger — cash available $30, invoice balance = total − $50
      7. Apply the rest to close the invoice
      8. What remains of the $80 is unapplied, on account
    Every invoice amount is computed from the jurisdiction and carrier records.

    Key fields demonstrated: amount, available, tendered, change.
    Key behaviors: available decrements on apply, ledger tracks available not amount.
    """
    G = _gl_defaults()
    unit_price = Decimal('10.00')
    unit_cost = Decimal('6.00')
    R = sim_rates()
    tax_pct, ship_pct = _pct(R['tax_rate']), _pct(R['shipping_rate'])
    b = _money_breakdown(6, unit_price, R)
    cogs = _r2(unit_cost * 6)
    cash_amt, first = Decimal('80.00'), Decimal('50.00')
    balance = b['total'] - first
    left_after_first = cash_amt - first
    left_after_close = left_after_first - balance
    m = lambda x: f"${x:,.2f}"

    steps = [
        {
            'step': 1,
            'title': 'Create Order — 10 units × $10.00',
            'instruction': 'Create an Order with 10 units of the training item at $10.00 each. Total = $100.00.',
            'action': 'create_order',
            'qty': 10,
            'expected_cash': None,
            'expected_gl': [],
            'explanation': (
                'No financial event yet. The order is a commitment — 10 units reserved (on_so=10). '
                'No cash fields involved. No GL impact.'
            ),
        },
        {
            'step': 2,
            'title': 'Invoice 6 of 10 — partial shipment',
            'instruction': (f"Create an Invoice from the Order for 6 of the 10 units, tax jurisdiction {R['tax_jurisdiction']}, "
                            f"ship via {R['ship_via']}. Invoice total = {m(b['total'])} "
                            f"({m(b['goods'])} goods + {m(b['shipping'])} shipping ({ship_pct}) + {m(b['tax'])} tax ({tax_pct}))."),
            'action': 'create_invoice_from_order',
            'qty': 6,
            'expected_invoice': {
                'amount': float(b['goods']),
                'shipping': float(b['shipping']),
                'tax': float(b['tax']),
                'total': float(b['total']),
                'balance_due': float(b['total']),
            },
            'expected_gl': [
                {'account': G['ar'], 'side': 'debit', 'amount': float(b['total']),
                 'purpose': f"AR — customer owes {m(b['total'])}"},
                {'account': G['revenue'], 'side': 'credit', 'amount': float(b['goods']),
                 'purpose': f"Revenue — 6 × {m(unit_price)}"},
                {'account': G['shipping'], 'side': 'credit', 'amount': float(b['shipping']),
                 'purpose': f"Shipping — {ship_pct} × {m(b['goods'])}"},
                {'account': G['tax_payable'], 'side': 'credit', 'amount': float(b['tax']),
                 'purpose': f"Sales Tax — {tax_pct} × {m(b['goods'])}"},
                {'account': G['cogs'], 'side': 'debit', 'amount': float(cogs),
                 'purpose': f"COGS — 6 × {m(unit_cost)}"},
                {'account': G['inventory'], 'side': 'credit', 'amount': float(cogs),
                 'purpose': 'Inventory reduction'},
            ],
            'explanation': (
                f"THIS is the financial event. 6 units ship. Invoice created for {m(b['total'])}.\n"
                f"GL records the sale. AR = {m(b['total'])}. Revenue = {m(b['goods'])}. "
                f"Shipping = {m(b['shipping'])}. Tax = {m(b['tax'])} (2 × shipping).\n"
                'The remaining 4 units stay on the order (on_so=4).'
            ),
        },
        {
            'step': 3,
            'title': 'Accept Cash — $80 (tendered $100 cash)',
            'instruction': (
                'Create a Cash record:\n'
                '• amount = $80.00 (what they\'re paying)\n'
                '• tendered = $100.00 (what they handed over)\n'
                '• change = $20.00 (auto-computed)\n'
                '• available = $80.00 (auto-set = amount on creation)\n\n'
                'Do NOT apply it to the invoice yet. This is just accepting the money.'
            ),
            'action': 'create_cash',
            'amount': 80.00,
            'tendered': 100.00,
            'expected_cash': {
                'amount': 80.00,
                'available': 80.00,
                'tendered': 100.00,
                'change': 20.00,
                'status': 'complete',
            },
            'expected_gl': [
                {'account': G['cash'], 'side': 'debit', 'amount': 80.00,
                 'purpose': 'Cash received (amount, not tendered)'},
                {'account': G['ar'], 'side': 'credit', 'amount': 80.00,
                 'purpose': 'AR reduced by cash amount'},
            ],
            'explanation': (
                'Customer hands over $100 cash for an $80 cash. Change = $20.\n\n'
                'Key fields on Cash record:\n'
                '• amount = $80 — the real cash amount\n'
                '• tendered = $100 — what the customer physically gave\n'
                '• change = $20 — computed: tendered - amount\n'
                '• available = $80 — starts equal to amount, decrements as applied\n\n'
                'WC2 equivalent: [Cash]amount, [Cash]amountAvailable, '
                '[Cash]tendered, [Cash]change\n\n'
                'The cash exists but is NOT yet applied to the invoice. '
                'The customer has $80 on account.'
            ),
        },
        {
            'step': 4,
            'title': 'Apply $50 to Invoice',
            'instruction': (
                f"Apply $50 of the $80 cash to the {m(b['total'])} invoice.\n\n"
                'After this step:\n'
                '• Cash.available drops from $80 → $30\n'
                f"• Invoice balance drops from {m(b['total'])} → {m(balance)}\n"
                '• Ledger value_available updates to -$30 (tracks unapplied)\n'
                '• Pending application record created (purpose cash_application)'
            ),
            'action': 'apply_cash_to_invoice',
            'amount': 50.00,
            'expected_cash': {
                'amount': 80.00,
                'available': 30.00,
                'tendered': 100.00,
                'change': 20.00,
            },
            'expected_invoice': {
                'total': float(b['total']),
                'received': float(first),
                'balance_due': float(balance),
                'status': 'partially_paid',
            },
            'expected_gl': [],
            'explanation': (
                f"Partial application. We take $50 of the $80 and apply it to the {m(b['total'])} invoice.\n\n"
                'What changes:\n'
                '• Cash.available: $80 → $30 (decremented by apply amount)\n'
                '• Invoice.totals.received: $0 → $50\n'
                f"• Invoice.totals.balance: {m(b['total'])} → {m(balance)}\n"
                '• Invoice status: "sent" → "partially_paid"\n'
                '• Ledger value_available: -$80 → -$30 (on next cash save)\n\n'
                'What does NOT change:\n'
                '• Cash.amount stays $80 (immutable — the original cash)\n'
                '• Cash.tendered stays $100\n'
                '• Cash.change stays $20\n\n'
                'WC2: This is the ApplyCash dialog. The user picks invoices '
                'and allocates cash dollars across them. amountAvailable tracked '
                'how much was left to allocate.'
            ),
        },
        {
            'step': 5,
            'title': 'Journal the Cash',
            'instruction': (
                'Post the cash to the GL (user-initiated action).\n\n'
                'This creates GlJournal records from the staged metadata.gl_accounts.\n'
                'The cash is now locked — can only be reversed, not edited.'
            ),
            'action': 'post_gl',
            'expected_gl': [
                {'account': G['cash'], 'side': 'debit', 'amount': 80.00,
                 'purpose': 'Cash receipt — full cash amount'},
                {'account': G['ar'], 'side': 'credit', 'amount': 80.00,
                 'purpose': 'AR reduction — full cash amount'},
            ],
            'explanation': (
                'GL journals are created. The cash is now part of the permanent record.\n\n'
                'Note: GL posts the FULL cash amount ($80), not the applied amount ($50). '
                'The journal captures the cash event. The application captures the allocation. '
                'These are two different things:\n'
                '• Cash event: "Customer gave us $80" → GL\n'
                '• Allocation: "We applied $50 to Invoice #X" → Pending application record\n\n'
                'The ledger tracks available ($30) for aging and credit calculations. '
                'The GL tracks the full amount for financial statements.'
            ),
        },
        {
            'step': 6,
            'title': 'Check the Ledger',
            'instruction': (
                'Verify the ledger state for this customer. Ledger rows echo their primary records:\n\n'
                f"• Invoice ledger: value_original = +{m(b['total'])}, value_available = +{m(balance)} (echoes the invoice)\n"
                '• Cash ledger: value_original = -$80, value_available = -$30 (echoes the cash)\n\n'
                'Org financial.summary should show:\n'
                f"• receivable = {m(balance)} (open invoice balances) = receivable_ledger\n"
                '• unapplied_cash = $30 = unapplied_cash_ledger\n'
                f"• net = {m(balance)} − $30 = {m(balance - left_after_first)}; in_step = true\n"
                f"• customer balances.due = {m(balance)} (invoices only; unapplied cash is shown apart)"
            ),
            'action': 'check_ledger',
            'expected_ledger': {
                'invoice_value_original': float(b['total']),
                'invoice_value_available': float(balance),
                'cash_value_original': -80.00,
                'cash_value_available': -30.00,
                'net': float(balance - left_after_first),
            },
            'explanation': (
                'The ledger is the single source of truth for AR aging.\n\n'
                'WC2 equivalent: Ledger_TallyBal computed:\n'
                '• balanceDue from SUM(unAppliedValue) across all ledger records\n'
                '• balanceAvailableCashEntries from SUM(amountAvailable) on Cash\n'
                '• totalExposure = balanceDue + openOrders\n\n'
                'WC3 does the same in update_org_balances():\n'
                '• Reads all Ledger records for org → aging buckets\n'
                '• Reads Cash.available WHERE > 0 → available_cash_entries\n'
                '• total_exposure = balance_due + open_orders - available_cash_entries'
            ),
        },
        {
            'step': 7,
            'title': f"Apply remaining {m(balance)} — close the invoice",
            'instruction': (
                f"Apply {m(balance)} more of the cash to the invoice.\n\n"
                'After this step:\n'
                f"• Cash.available: $30 → {m(left_after_close)}\n"
                f"• Invoice balance: {m(balance)} → $0\n"
                '• Invoice status: "partially_paid" → "paid"\n'
                f"• {m(left_after_close)} remains unapplied on account"
            ),
            'action': 'apply_cash_to_invoice',
            'amount': float(balance),
            'expected_cash': {
                'amount': 80.00,
                'available': float(left_after_close),
            },
            'expected_invoice': {
                'total': float(b['total']),
                'received': float(b['total']),
                'balance_due': 0.00,
                'status': 'paid',
            },
            'explanation': (
                f"Invoice is fully paid. The {m(left_after_close)} remaining on the cash is unapplied.\n\n"
                'This is common in commerce: customer overpays, or pays a round number. '
                'The excess stays on account as available_cash_entries. It can be:\n'
                '• Applied to the next invoice\n'
                '• Refunded\n'
                '• Left on account as a credit\n\n'
                'WC2 tracked this with balanceAvailableCashEntries on Customer. '
                'WC3 tracks it with Cash.available and org.financial.available_cash_entries.'
            ),
        },
        {
            'step': 8,
            'title': 'Summary — the cash lifecycle',
            'instruction': 'Review what happened across all 7 steps.',
            'action': None,
            'exit_point': {
                'name': 'Cash Lifecycle Complete',
                'summary': (
                    f"Order $100 → Invoice {m(b['total'])} (partial) → Cash $80 (tendered $100, change $20) "
                    f"→ Apply $50 → Journal → Apply {m(balance)} → Invoice paid, {m(left_after_close)} on account."
                ),
            },
            'explanation': (
                'The four cash fields and their roles:\n\n'
                '| Field     | Created | After apply $50 | After apply $13 |\n'
                '|-----------|---------|-----------------|------------------|\n'
                '| amount    | $80     | $80             | $80              |\n'
                f"| available | $80     | $30             | {m(left_after_close):<16} |\n"
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
            'tax_jurisdiction': R['tax_jurisdiction'],
            'tax_rate': float(R['tax_rate']),
            'ship_via': R['ship_via'],
            'shipping_rate': float(R['shipping_rate']),
            'starting_on_hand': 100,
        },
        'gl_accounts': G,
    }


#: The scripted scenarios, by console id; a console with none lists its description only.
SCENARIOS = {
    'first-customer': get_first_customer_scenario,
    'first-item': get_first_item_scenario,
    'first-sale': get_first_sale_scenario,
    'inventory': get_flight_scenario,
    'cash-lifecycle': get_cash_flight_scenario,
}


def console_settings() -> List[Dict[str, Any]]:
    """The Setting payloads seed_consoles writes: one per console, steps from its scenario."""
    from apps.accounts.services.chart import UndefinedAccountError
    out = []
    for sequence, c in enumerate(CONSOLES, start=1):
        scenario: Dict[str, Any] = {}
        if c['id'] in SCENARIOS:
            try:
                scenario = SCENARIOS[c['id']]()
            except (UndefinedAccountError, ValueError) as err:
                # The inventory and cash scripts name the company's GL accounts, its tax
                # jurisdiction and its carrier; an installation without them yet seeds the
                # console without its steps and says what is missing. Rerun seed_consoles
                # --force once they are in.
                scenario = {'steps': [], 'steps_pending': str(err)}
        extras = {k: v for k, v in scenario.items() if k not in ('id', 'label', 'steps')}
        out.append({
            'ida': c['id'], 'name': c['label'], 'purpose': PURPOSE, 'explanation': c['description'],
            'config': {'sequence': sequence, 'kind': 'sim', 'description': c['description'],
                       'needs_item': c['needs_item'], 'first_model': c['first_model'],
                       'steps': scenario.get('steps', []), **extras},
        })
    return out
