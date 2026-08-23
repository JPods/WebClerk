"""
Flight Simulator: Onboarding — Phase 1 foundation exercises.

Three guided simulations that create the data all later sims depend on:
  1. Your First Customer — Contact → Customer Org → Credit limit
  2. Your First Item — Item → Price/Cost/GL → Opening inventory
  3. Your First Sale — Proposal → Convert to Order

Each returns a scenario dict with steps, expected values, and explanations.
The frontend walks through the steps; the user does real actions on real forms.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict


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
                'contact FK on payments and invoices).\n\n'
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
                'display_name': 'Training Corp',
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
                '• Vendor → AP aging, payment terms, lead time\n\n'
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
                    'available_payments': 0.00,
                    'total_exposure': 0.00,
                    'days_avg_paid': 0,
                },
            },
            'explanation': (
                'Credit limit controls whether new orders are accepted. The formula:\n\n'
                '  credit_available = credit_limit - balance_due\n\n'
                'When a customer places an order, WC3 checks:\n'
                '  total_exposure = balance_due + open_orders - available_payments\n\n'
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
                'into RBAC — a buyer can place orders but not approve payments.\n\n'
                'When you create a transaction (order, invoice, payment), the contact '
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
                '• Revenue: REV-SALES-000\n'
                '• COGS: COGS-PRODUCTS-000\n'
                '• Inventory: ASSET-INVENTORY-000\n\n'
                'These go in the gls JSON field.\n'
                'Save the record.'
            ),
            'action': 'set_gl_accounts',
            'model': 'item',
            'expected_fields': {
                'gls': {
                    'revenue': 'REV-SALES-000',
                    'cogs': 'COGS-PRODUCTS-000',
                    'inventory': 'ASSET-INVENTORY-000',
                },
            },
            'explanation': (
                'Every item maps to three GL accounts:\n\n'
                '• Revenue — where sale dollars go (credit on invoice)\n'
                '• COGS — cost of goods sold (debit on invoice)\n'
                '• Inventory — asset account (credit on sale, debit on receipt)\n\n'
                'When you invoice 4 units of this item at $10, the GL entries are:\n'
                '  DR  AR              $42  (customer owes — includes tax)\n'
                '  CR  REV-SALES-000   $40  (revenue)\n'
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
                    'on_p': 0,
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
                '| on_p      | On proposals (quotes) | Proposal (up), Convert (down) |\n'
                '| on_wo     | On work orders | WO (up), Complete (down) |\n'
                '| available | on_hand - allocated | Computed |\n\n'
                'Proposals DON\'T reduce available (they\'re just quotes). '
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
    """Your First Sale — Proposal → Convert to Order.

    Uses the customer from sim 1 and the item from sim 2.
    Bridges Phase 1 into Phase 2 (inventory tracking).
    """
    steps = [
        {
            'step': 1,
            'title': 'Create a Proposal',
            'instruction': (
                'Open the right panel form (Proposal). Fill in:\n'
                '• Customer: Training Corp (from exercise 1)\n'
                '• Contact: Training User\n\n'
                'Save the header first, then add a line:\n'
                '• Item: qqBB200 (Training Widget)\n'
                '• Quantity: 15\n'
                '• Price: $10.00 (should auto-fill from item)\n\n'
                'Save.'
            ),
            'action': 'create_proposal',
            'model': 'proposal',
            'qty': 15,
            'expected_quantity_change': {
                'on_p': '+15',
                'on_hand': '100 (unchanged)',
                'available': '100 (unchanged)',
            },
            'explanation': (
                'A Proposal is a quote — a conversation with the customer about what '
                'they might buy. It is NOT a commitment.\n\n'
                'What happens when you save the proposal line:\n'
                '• on_p increases by 15 (we\'re quoting 15 units)\n'
                '• on_hand stays at 100 (nothing moved)\n'
                '• available stays at 100 (proposals don\'t allocate)\n'
                '• NO GL entries (a quote has no financial weight)\n'
                '• A Pending record is created (tracks the quantity delta)\n\n'
                'Why proposals don\'t allocate: imagine quoting 50 units to 10 customers. '
                'If proposals allocated, you\'d need 500 units for $5,000 in quotes — '
                'but most quotes don\'t convert. Proposals are visibility, not commitment.\n\n'
                'WC2: This was the Quote window → [QT_Lines] table.'
            ),
        },
        {
            'step': 2,
            'title': 'Convert to Order — partial (9 of 15)',
            'instruction': (
                'On the Proposal, click the Convert to Order button.\n'
                'Change the quantity to 9 (the customer only wants 9 of the 15 quoted).\n\n'
                'The conversion creates a new Order record and copies the line.\n'
                'The proposal line quantity drops to 6 remaining.\n\n'
                'Watch the left panel — quantities will change.'
            ),
            'action': 'convert_to_order',
            'model': 'order',
            'qty': 9,
            'expected_quantity_change': {
                'on_p': '15 → 6 (−9)',
                'on_so': '0 → 9 (+9)',
                'on_hand': '100 (unchanged)',
                'available': '100 → 91 (−9)',
            },
            'explanation': (
                'NOW it\'s a commitment. The conversion:\n\n'
                '1. Creates a new Order header (linked to the proposal via refs)\n'
                '2. Copies the line to the order with quantity = 9\n'
                '3. Reduces the proposal line to 6 remaining\n'
                '4. Creates Pending records for the quantity changes\n\n'
                'Quantity changes:\n'
                '• on_p: 15 → 6 (9 units moved from quote to order)\n'
                '• on_so: 0 → 9 (9 units committed to this sales order)\n'
                '• available: 100 → 91 (orders ALLOCATE — these 9 are spoken for)\n'
                '• on_hand: still 100 (nothing has physically moved)\n\n'
                'Still NO GL entries. An order is a promise to deliver, not a delivery. '
                'The financial event happens at invoicing.\n\n'
                'Why partial? Real commerce rarely converts 100% of a quote. '
                'The customer negotiates, reduces quantities, drops items. The 6 remaining '
                'on the proposal can convert later, expire, or be cancelled.\n\n'
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
                '• on_hand = 100, on_so = 9, on_p = 6, available = 91\n\n'
                'This order is ready to invoice (ship).'
            ),
            'action': 'review_order',
            'model': 'order',
            'exit_point': {
                'name': 'Your First Sale Complete',
                'summary': (
                    'You created a proposal for 15 units, converted 9 to an order. '
                    'The customer has 9 units committed (on_so=9), 6 still quoted (on_p=6), '
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
                '| Proposal | 15 × $10 | Quotes don\'t allocate inventory |\n'
                '| Order | 9 × $10 | Orders DO allocate inventory |\n\n'
                'The data you created here is the foundation for every flight sim in '
                'Phase 2, 3, and 4. The training item qqBB200 with 100 units on hand '
                'at $10 price / $6 cost is the standard starting point.\n\n'
                'The progression: Contact → Customer → Item → Proposal → Order → '
                'Invoice → Payment → GL. Each step adds financial weight. The first '
                'three have none. The proposal has visibility only. The order commits. '
                'The invoice is the financial event.'
            ),
        },
    ]

    return {
        'id': 'first-sale',
        'label': 'Your First Sale',
        'steps': steps,
        'models_used': ['proposal', 'order'],
        'prerequisite': 'first-item',
        'next_sim': 'inventory',
    }


__all__ = [
    'get_first_customer_scenario',
    'get_first_item_scenario',
    'get_first_sale_scenario',
]
