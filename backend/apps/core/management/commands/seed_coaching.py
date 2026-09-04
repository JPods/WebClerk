"""
seed_coaching — Alice's coaching content: Setting records + Document records + Action records.

Usage:
    ./bin/python manage.py seed_coaching
    ./bin/python manage.py seed_coaching --force

Creates:
  - Setting records (purpose='wc:coaching') — one per key model with tips, field_help, etc.
  - Document records — how-to guides Alice can reference and link to
  - Action records — onboarding checklist items Alice assigns to new users
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from apps.docs.models.document import Document
from apps.core.models.action import Action
import time


def _now_ms():
    return int(time.time() * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# Coaching content per model
# ─────────────────────────────────────────────────────────────────────────────

COACHING = {
    'customer': {
        'tips': [
            {'id': 'cust-01', 'title': 'Customers are the center', 'body': 'Every order, invoice, proposal, and payment links to a customer. Start here.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'cust-02', 'title': 'A customer can also be a vendor', 'body': 'The same contact can have multiple org relationships. Check the contact record to see all hats.', 'type': 'concept', 'level': 'intermediate'},
            {'id': 'cust-03', 'title': 'Price levels matter', 'body': 'Retail, wholesale, distributor, sample — the price level on the customer flows to orders and invoices automatically.', 'type': 'workflow', 'level': 'beginner'},
        ],
        'field_help': {
            'ida': 'Short identifier — unique across all customers. Auto-generated or manually set.',
            'display_name': 'The primary name shown in lists and on printed documents.',
            'status': 'active = doing business. prospect = potential. inactive = paused. retired = closed.',
            'price_level': 'Determines which price tier is used on orders/invoices for this customer.',
            'terms': 'Payment terms (N30, COD, 2/10 Net 30). Sets when payment is due.',
            'email': 'Primary email. Cmd+click label to compose. Synced from communications.',
            'phone': 'Primary phone. Cmd+click label to dial. Synced from communications.',
            'address_full': 'Primary address. Cmd+click label to open in maps.',
            'attention': 'Who to address correspondence to at this organization.',
            'source_name': 'How this customer found you — referral, web, trade show, etc.',
            'dt_created': 'When this customer record was created. Read-only.',
            'dt_modified': 'Last time any field on this record was changed.',
            'is_active': 'Unchecked = hidden from search and dropdowns. Use instead of deleting.',
            'security_level': 'Access tier. Higher = more restricted. 0 = public.',
            'totals': 'Aggregated order/invoice totals. Updated by the system — read-only.',
            'config': 'Custom settings for this customer — ship-to addresses, special instructions.',
            'metadata': 'System-managed data — AR aging, Alice observations, health score.',
            'refs': 'Links to related records. Denormalized cache — PKs are authoritative.',
            'prefs': 'Customer-specific preferences — notification settings, default formats.',
        },
        'actions': {
            'create': 'Enter display name and status. Save. Then add communications (email, phone, address) in the Communications tab.',
            'order': 'From a customer, click "New Order" to create an order pre-linked to this customer.',
            'statement': 'Click "Statement" to generate an AR statement showing open invoices and aging.',
        },
        'warnings': ['Deleting a customer does NOT delete their orders/invoices. Those become orphaned.'],
        'code_examples': [
            {'title': 'List active customers', 'language': 'javascript', 'code': "const res = await getRecords('customer', { status: 'active' });"},
            {'title': 'Search by name', 'language': 'javascript', 'code': "const res = await getRecords('customer', { keyword: 'acme' });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=customer&status=active&ordering=display_name",
            'get': "GET /wcapi/get/?model_name=customer&id={id}",
            'save': "POST /wcapi/save/ {model_name: 'customer', display_name: '...', status: 'active'}",
        },
    },

    'invoice': {
        'tips': [
            {'id': 'inv-01', 'title': 'Invoice lifecycle', 'body': 'planned → released → complete. Only released invoices appear on statements and can be posted to GL.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'inv-02', 'title': 'Balance tracks payments', 'body': 'Balance = Total - Payments. When it reaches 0, the invoice is fully paid.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'inv-03', 'title': 'GL posting is one-way', 'body': 'Once posted, you can only reverse — not edit. Post when the invoice is final.', 'type': 'warning', 'level': 'intermediate'},
        ],
        'field_help': {
            'ida': 'Invoice number — unique identifier. Auto-generated or manually set.',
            'total': 'Sum of all line items. Edit lines to change — total recalculates automatically.',
            'balance': 'Total minus payments received. Read-only. Updated when payments are applied.',
            'status': 'planned = draft. released = sent to customer. complete = paid and closed.',
            'terms': 'Payment terms — determines due date on the ledger record.',
            'price_level': 'Price tier used for line item pricing on this invoice.',
            'dt_needed': 'When customer needs delivery. Drives warehouse priority.',
            'priority': 'Processing priority. Higher number = pick/ship first.',
            'attention': 'Contact name at the customer for this invoice.',
            'company': 'Customer company name. Denormalized from the customer record.',
            'email': 'Billing email. Cmd+click label to compose.',
            'phone': 'Billing phone. Cmd+click label to dial.',
            'address_full': 'Bill-to address. Cmd+click label to open in maps.',
            'ship_via': 'Preferred shipping carrier or method.',
            'invoice_type': 'Invoice = standard. Proforma = quote-like. Credit Note = refund. Deposit = prepay.',
            'source_name': 'Where this invoice originated — order conversion, manual entry, import.',
            'conditions_description': 'Special terms or conditions printed on the invoice.',
            'totals': 'Subtotal, tax, shipping, and grand total. Computed from lines — read-only.',
            'cost': 'Cost-side data — landed cost, margin analysis. Not shown to customers.',
            'finance': 'GL posting data — account codes, journal references, posting status.',
            'config': 'Custom settings — alternate ship-to, special handling instructions.',
            'sell': 'Sales-side envelope — commission data, rep assignments.',
            'source': 'Origin tracking — which order, proposal, or import created this invoice.',
        },
        'actions': {
            'create': 'Select a customer, set status to planned, add line items with items and quantities.',
            'print': 'Click Reports button → Invoice. Opens printable format.',
            'payment': 'Go to Payments → Apply Payments. Select this invoice, enter amount.',
            'gl_post': 'On the invoice toolbar, click Post GL. Creates journal entries by account code.',
        },
        'warnings': [
            "Don't manually set status to 'complete' — let the system do it when balance reaches 0.",
            'GL posting creates permanent journal entries. Review totals before posting.',
        ],
        'code_examples': [
            {'title': 'Get invoice with lines', 'language': 'javascript', 'code': "const res = await getRecord('invoice', id);\nconst lines = res.record.lines;"},
            {'title': 'List overdue invoices', 'language': 'javascript', 'code': "const res = await getRecords('invoice', { status: 'released', ordering: 'dt_created' });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=invoice&status=released",
            'get': "GET /wcapi/get/?model_name=invoice&id={id}",
            'save': "POST /wcapi/save/ {model_name: 'invoice', customer_id: X, status: 'planned'}",
        },
    },

    'order': {
        'tips': [
            {'id': 'ord-01', 'title': 'Orders drive fulfillment', 'body': 'An order is a commitment to deliver. It can generate pick lists, packing slips, and invoices.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'ord-02', 'title': 'Order → Invoice flow', 'body': 'When an order is fulfilled, convert it to an invoice. Lines carry over automatically.', 'type': 'workflow', 'level': 'beginner'},
        ],
        'field_help': {
            'ida': 'Order number — unique identifier.',
            'total': 'Sum of line items. Recalculates when lines are added/changed.',
            'balance': 'Amount not yet invoiced. Decreases as invoices are created.',
            'status': 'planned = not started. released = being fulfilled. complete = shipped/delivered.',
            'priority': 'Helps warehouse sort what to pick first. Higher number = pick first.',
            'dt_needed': 'Customer-requested delivery date. Drives pick list priority.',
            'attention': 'Contact name at the customer for this order.',
            'company': 'Customer company name.',
            'email': 'Order contact email. Cmd+click label to compose.',
            'phone': 'Order contact phone. Cmd+click label to dial.',
            'address_full': 'Ship-to address. Cmd+click label to open in maps.',
            'ship_via': 'Shipping carrier or method for this order.',
            'price_level': 'Price tier — flows from customer unless overridden here.',
            'terms': 'Payment terms — flows from customer unless overridden.',
            'conditions_description': 'Special order conditions printed on documents.',
            'source_name': 'Where this order came from — web, phone, proposal conversion.',
            'totals': 'Subtotal, tax, shipping, total. Computed from lines — read-only.',
            'cost': 'Cost-side data — margin analysis. Internal only.',
            'config': 'Custom settings — alternate ship-to, special handling.',
        },
        'actions': {
            'create': 'Select customer, add line items. Each line needs an item and quantity.',
            'pick': 'Click Reports (🖨) → Pick/Pull Request for warehouse picking list.',
            'convert': 'To invoice: use the order-to-invoice conversion flow.',
        },
        'warnings': ['Changing an order after pick lists are printed can cause fulfillment errors.'],
        'code_examples': [
            {'title': 'Create order', 'language': 'javascript', 'code': "await saveRecord('order', { customer_id: X, status: 'planned' });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=order&ordering=-dt_created",
            'save': "POST /wcapi/save/ {model_name: 'order', customer_id: X}",
        },
    },

    'proposal': {
        'tips': [
            {'id': 'prop-01', 'title': 'Proposals are quotes', 'body': 'A proposal is a price quote sent to a customer. If accepted, it converts to an order.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'prop-02', 'title': 'MSRP vs Unit Price', 'body': 'Proposal lines show both MSRP and the offered unit price so the customer sees the discount.', 'type': 'concept', 'level': 'beginner'},
        ],
        'field_help': {
            'ida': 'Proposal number — unique identifier.',
            'total': 'Proposed total — what the customer would pay if they accept.',
            'status': 'planned = draft. released = sent to customer. complete = accepted or expired.',
            'dt_needed': 'Proposal expiration or decision-needed date.',
            'price_level': 'Price tier for this quote — may differ from customer default.',
            'attention': 'Who at the customer receives this proposal.',
            'company': 'Customer company name.',
            'email': 'Contact email. Cmd+click label to compose.',
            'phone': 'Contact phone. Cmd+click label to dial.',
            'address_full': 'Customer address. Cmd+click label to open in maps.',
            'totals': 'Subtotal, tax, shipping, total. Computed from lines.',
            'conditions_description': 'Terms and conditions printed on the proposal.',
        },
        'actions': {
            'create': 'Select customer, add line items with items, quantities, and pricing.',
            'convert': 'If customer accepts, convert proposal to order.',
            'print': 'Reports (🖨) → Proposal/Quote for professional printable format.',
        },
        'warnings': [],
        'code_examples': [
            {'title': 'List customer proposals', 'language': 'javascript', 'code': "await getRecords('proposal', { customer_id: X });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=proposal",
            'save': "POST /wcapi/save/ {model_name: 'proposal', customer_id: X}",
        },
    },

    'purchase': {
        'tips': [
            {'id': 'po-01', 'title': 'Purchases go to vendors', 'body': 'A purchase order is sent to a vendor to buy goods. It tracks what you ordered vs what you received.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'po-02', 'title': 'PO → Receiving → Payment', 'body': 'Receive goods against the PO, then create a disbursement (payment type=disbursed) to pay the vendor.', 'type': 'workflow', 'level': 'beginner'},
        ],
        'field_help': {
            'ida': 'PO number — unique identifier.',
            'total': 'Total cost of all purchase lines.',
            'balance': 'Amount not yet received or paid.',
            'status': 'planned = draft. released = sent to vendor. complete = fully received.',
            'dt_needed': 'When you need the goods. Communicate to vendor.',
            'priority': 'Internal priority for receiving. Higher = process first.',
            'attention': 'Contact name at the vendor.',
            'company': 'Vendor company name.',
            'email': 'Vendor email. Cmd+click label to compose.',
            'phone': 'Vendor phone. Cmd+click label to dial.',
            'address_full': 'Vendor address. Cmd+click label to open in maps.',
            'ship_via': 'Shipping method — vendor ships to you.',
            'terms': 'Vendor payment terms — when you pay them.',
            'totals': 'Subtotal, tax, shipping, total. Computed from lines.',
            'cost': 'Cost breakdown — landed cost, duty, freight allocation.',
            'source_name': 'What triggered this purchase — reorder, manual, import.',
        },
        'actions': {
            'create': 'Select vendor, add line items with items and quantities.',
            'email': 'Reports (🖨) → PO Email to Vendor sends the PO as PDF.',
            'receive': 'When goods arrive, record receiving against the PO lines.',
        },
        'warnings': ['Receiving more than ordered creates overstock. Check quantities.'],
        'code_examples': [
            {'title': 'Create PO', 'language': 'javascript', 'code': "await saveRecord('purchase', { vendor_id: X, status: 'planned' });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=purchase&vendor_id={id}",
            'save': "POST /wcapi/save/ {model_name: 'purchase', vendor_id: X}",
        },
    },

    'ledger': {  # payment coaching stored under ledger (payment not in registry)

        'tips': [
            {'id': 'pay-01', 'title': 'Two types of payments', 'body': "received = money in (customer pays us). disbursed = money out (we pay vendor). Same model, different type.", 'type': 'concept', 'level': 'beginner'},
            {'id': 'pay-02', 'title': 'Payments reduce balance', 'body': 'Applying a payment to an invoice reduces its balance. When balance = 0, invoice is paid.', 'type': 'concept', 'level': 'beginner'},
        ],
        'field_help': {
            'type': 'received = AR (customer pays us). disbursed = AP (we pay vendor/employee).',
            'amount': 'Payment amount. Must be positive.',
            'status': 'pending = entered. completed = processed. failed = rejected.',
            'reference_number': 'Check number, transaction ID, or other external reference.',
            'gateway': 'manual = entered by hand. stripe/paypal = processed by gateway.',
        },
        'actions': {
            'apply': 'Go to Apply Payments to match a payment to an invoice.',
            'reconcile': 'After bank statement arrives, mark payments as reconciled.',
        },
        'warnings': ['Disbursed payments should link to a purchase order via the purchase field.'],
        'code_examples': [
            {'title': 'Record payment received', 'language': 'javascript', 'code': "await saveRecord('payment', {\n  type: 'received', amount: 500,\n  invoice_id: X, contact_id: Y,\n  gateway: 'manual', status: 'completed'\n});"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=payment&type=received&ordering=-dt_payment",
            'save': "POST /wcapi/save/ {model_name: 'payment', type: 'received', amount: 500}",
        },
    },

    'gl_journal': {
        'tips': [
            {'id': 'gl-01', 'title': 'Journals record financial events', 'body': 'Every invoice, payment, and purchase creates GL journal entries. Debit always equals credit.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'gl-02', 'title': 'Export, don\'t retype', 'body': 'Use GL Journal Export to download bundle.json, then open the Journal Formatter to convert it into your accounting program\'s format. No retyping.', 'type': 'workflow', 'level': 'beginner', 'link': '/tools/journal_formatter.html', 'link_label': 'Open Journal Formatter'},
            {'id': 'gl-03', 'title': 'One format, two destinations', 'body': 'The same bundle.json works for local accounting export and multi-location consolidation. Your accountant sees entries tagged by company UUID regardless of how many locations you have.', 'type': 'concept', 'level': 'intermediate'},
            {'id': 'gl-04', 'title': 'WC3 produces, accounting consumes', 'body': 'WebClerk produces GL journal entries. QuickBooks/Xero/Sage consumes them. WC3 does not do checkbooks, payables, or P&L — that\'s the accounting program\'s job.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'gl-05', 'title': 'Journal Formatter is free', 'body': 'The Journal Formatter is a standalone HTML tool — no server, works offline, runs in any browser. Drop bundle.json, pick your program, download.', 'type': 'concept', 'level': 'beginner'},
        ],
        'field_help': {
            'account': 'GL account code (e.g. ASSET-AR-000). Maps to your chart of accounts.',
            'debit': 'Debit amount. Increases assets and expenses.',
            'credit': 'Credit amount. Increases liabilities, equity, and revenue.',
            'type': 'Source type — sales, purchase, payment, adjustment.',
            'source_model': 'Which record created this entry (invoice, payment, purchase).',
            'division': 'Division or department code. Optional — used for departmental reporting.',
            'batch_id': 'Batch identifier. Journals posted together share a batch.',
        },
        'actions': {
            'export': 'Go to GL Journals → Export. Select period, click Export to download bundle.json.',
            'format': 'Open tools/journal_formatter.html in your browser. Drop bundle.json, pick your accounting program.',
            'upstream': 'Multi-location: the same bundle.json can be sent to your company HQ for consolidation.',
            'reconcile': 'After importing into your accounting program, mark the period as reconciled in WebClerk.',
        },
        'warnings': [
            'GL posting is one-way. Once posted, you reverse — you don\'t edit.',
            'Always verify totals are balanced before importing into your accounting program.',
            'HQ never loads location journals into its own GL. They stay as Bundles for the accounting handoff.',
        ],
        'code_examples': [],
        'api_reference': {
            'export': "python manage.py shell -c \"from apps.sync.services.gl_journal_bundle import build_gl_journal_bundle; import json; print(json.dumps(build_gl_journal_bundle('2026-08'), indent=2, default=str))\"",
        },
    },

    'item': {
        'tips': [
            {'id': 'item-01', 'title': 'Items are what you sell and buy', 'body': 'Every line on an order, invoice, or PO references an item. Items have prices, costs, and inventory.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'item-02', 'title': 'Margin velocity', 'body': 'The real metric: (margin × annual turns) ÷ carry cost. High velocity = productive inventory.', 'type': 'concept', 'level': 'advanced'},
        ],
        'field_help': {
            'ida': 'Item identifier — unique across all items.',
            'sku': 'Stock keeping unit — your internal product code.',
            'name': 'Display name shown on documents and in search.',
            'kind': 'product = physical goods. service = labor/time. bundle = kit of items. component = part of a bundle.',
            'uom': 'Unit of measure — ea, lb, ft, box, etc. Drives quantity calculations.',
            'base_uom': 'Base unit for conversion — e.g., case (uom) = 12 each (base_uom).',
            'status': 'active = available for sale. discontinued = no longer sold.',
            'price': 'Price envelope — prices by level (retail, wholesale, distributor), qty breaks.',
            'cost': 'Cost envelope — vendor cost, landed cost, last cost, average cost.',
            'quantity': 'Inventory envelope — on_hand, committed, available, reorder_point.',
            'margin_pct': 'Margin percentage at current price/cost. Alice flags below-floor items.',
            'margin_velocity': 'Margin × annual turns ÷ carry cost. The real productivity metric.',
            'annual_turns': 'How many times inventory sells per year. Higher = more productive.',
            'velocity_category': 'A/B/C/D ranking by margin velocity. A = top performers.',
            'catalog': 'Catalog assignments — which catalogs include this item.',
            'tax_code': 'Tax classification for this item. Drives tax calculation on lines.',
            'gls': 'GL account assignments — revenue, COGS, inventory accounts.',
            'flags': 'Boolean flags — taxable, commissionable, serialized, lot-tracked.',
            'description': 'Full description envelope — short, long, web, print versions.',
        },
        'actions': {
            'create': 'Enter SKU, name, kind, UOM. Set prices in the price JSON. Set costs in cost JSON.',
        },
        'warnings': ['Changing an item SKU after it appears on orders/invoices can break references.'],
        'code_examples': [
            {'title': 'Search items', 'language': 'javascript', 'code': "await getRecords('item', { keyword: 'drill bit', status: 'active' });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=item&status=active&ordering=name",
        },
    },

    'action': {
        'tips': [
            {'id': 'act-01', 'title': 'Actions are tasks', 'body': 'Track to-dos, assign work, manage projects. Actions have kanban columns, priorities, and deadlines.', 'type': 'concept', 'level': 'beginner'},
        ],
        'field_help': {
            'ida': 'Action identifier — unique across all actions.',
            'action': 'What needs to be done. The task description.',
            'description': 'Detailed description — context, requirements, acceptance criteria.',
            'kanban_column': 'backlog → todo → in_progress → review → done. Drag in Kanban view.',
            'priority': 'Higher number = higher priority. 1 = low, 5 = urgent.',
            'difficulty': 'Estimated complexity. 1 = simple, 5 = very complex.',
            'status': 'open = active. complete = done. cancelled = abandoned.',
            'percent_complete': '0-100. Update as work progresses.',
            'dt_start': 'When work began or should begin.',
            'dt_deadline': 'When this task is due. Shows in red when overdue.',
            'dt_expected': 'When you expect to finish. May differ from deadline.',
            'dt_completed': 'When this action was marked complete. Set by system.',
            'assigned_to': 'Who is responsible. First person = primary owner.',
            'project_name': 'Which project this action belongs to.',
            'sequence': 'Order within the project. Lower = earlier in the plan.',
            'action_type': 'Category — task, bug, feature, meeting, review, etc.',
            'burndown': 'Remaining effort estimate. Decreases toward zero.',
            'linkage': 'Related URL or record reference.',
            'impact': 'Business impact assessment — Alice auto-fills, users correct.',
            'retrospection': 'Post-completion review — what worked, what to improve.',
        },
        'actions': {
            'create': 'Enter task description, set project, assign to a contact, set deadline.',
        },
        'warnings': [],
        'code_examples': [
            {'title': 'List open tasks', 'language': 'javascript', 'code': "await getRecords('action', { kanban_column: 'in_progress', ordering: '-priority' });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=action&kanban_column=todo&ordering=-priority",
        },
    },

    'contact': {
        'tips': [
            {'id': 'cont-01', 'title': 'Contacts link everything', 'body': 'A contact is both a user account and a person. They link to orgs (customer, vendor, rep) and communications (email, phone).', 'type': 'concept', 'level': 'beginner'},
            {'id': 'cont-02', 'title': 'One contact, many hats', 'body': 'A contact can be linked to a customer, vendor, rep, and employee simultaneously.', 'type': 'concept', 'level': 'intermediate'},
        ],
        'field_help': {
            'ida': 'Contact identifier — unique across all contacts.',
            'email': 'Login email. Cmd+click label to compose. Also primary communication email.',
            'phone': 'Primary phone. Cmd+click label to dial.',
            'address_full': 'Primary address. Cmd+click label to open in maps.',
            'role': 'admin, manager, sales, warehouse, accounting, customer, vendor, rep.',
            'company': 'Company affiliation — may differ from org.display_name.',
            'attention': 'Full name as it appears on correspondence.',
            'name_first': 'First name. Used in greetings and informal references.',
            'name_last': 'Last name. Used in formal references and sorting.',
            'title': 'Job title — VP Sales, Warehouse Manager, etc.',
            'department': 'Department within the company.',
            'status': 'active = can log in and transact. inactive = disabled.',
            'contact_type': 'customer, vendor, employee, rep — determines which org links apply.',
            'security_level': 'Access tier. Higher = more restricted data visible.',
            'source_name': 'How this contact was acquired — referral, web form, import.',
            'dt_created': 'When this contact was first created.',
            'dt_last_used': 'Last login or transaction. Helps identify dormant contacts.',
            'times_used': 'Login or transaction count. Activity indicator.',
            'config': 'Contact-specific settings — notification preferences, UI layout.',
            'prefs': 'User preferences — theme, font size, default model, saved filters.',
        },
        'actions': {
            'create': 'Enter email (required), first/last name, company. Set role for access control.',
        },
        'warnings': ['Deleting a contact removes their login. Use is_active=false to disable instead.'],
        'code_examples': [
            {'title': 'Find contact by email', 'language': 'javascript', 'code': "await getRecords('contact', { keyword: 'john@example.com' });"},
        ],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=contact&ordering=name_last",
        },
    },

    'project': {
        'tips': [
            {'id': 'proj-01', 'title': 'Projects group actions', 'body': 'A project is a container for related actions. Weekly sprints or permanent containers — two modes.', 'type': 'concept', 'level': 'beginner'},
        ],
        'field_help': {
            'ida': 'Project identifier — unique across all projects.',
            'name': 'Project name. Shows in Kanban board headers and action dropdowns.',
            'purpose': 'What this project is for — sprint, initiative, client project, etc.',
            'status': 'active = in progress. complete = finished. on_hold = paused.',
            'priority': 'Higher number = more important. Affects action sorting.',
            'dt_start': 'When this project begins or began.',
            'dt_end': 'Target completion date.',
            'percent_complete': 'Overall progress. Calculated from action completion or set manually.',
            'burndown': 'Remaining effort across all actions.',
            'attention': 'Project owner or lead.',
            'category': 'Project type — sprint, campaign, client, internal, etc.',
            'intent': 'One-line goal statement. What does "done" look like?',
            'objective': 'Detailed objectives — key results, deliverables.',
            'tasks': 'Task breakdown — sub-objectives with status tracking.',
            'logistics': 'Resources, budget, timeline constraints.',
            'situation': 'Current project status narrative — updated each review.',
        },
        'actions': {
            'create': 'Set name, category, dates, and owner. Then add actions to the project.',
        },
        'warnings': [],
        'code_examples': [],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=project&status=active",
        },
    },

    'setting': {
        'tips': [
            {'id': 'set-01', 'title': 'Settings are the menu', 'body': 'Settings define how the system behaves — layouts, field options, coaching content, system config. They are the menu; connections are the spec.', 'type': 'concept', 'level': 'intermediate'},
        ],
        'field_help': {
            'ida': 'Setting identifier.',
            'name': 'Setting name — usually purpose:model format.',
            'purpose': 'What this setting controls: wc:coaching, wc:model, wc:ui, wc:system, etc.',
            'parent_model': 'Which model this setting applies to. Empty = system-wide.',
            'scope': 'Who this setting applies to — global, company, user.',
            'status': 'active = in use. inactive = disabled but preserved.',
            'explanation': 'Human description of what this setting does and how to use it.',
            'config': 'The actual configuration data — JSON envelope. Structure varies by purpose.',
            'paths': 'Routing paths — URL patterns, redirect rules. Used by wc:system settings.',
        },
        'actions': {
            'create': 'Set purpose and parent_model. The config JSON structure depends on the purpose.',
        },
        'warnings': ['Changing a setting config can affect all users immediately. Review before saving.'],
        'code_examples': [],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=setting&purpose=wc:coaching",
        },
    },

    'document': {
        'tips': [
            {'id': 'doc-01', 'title': 'Documents are content', 'body': 'Help guides, training materials, reports, file attachments. Searchable by name, slug, and body text.', 'type': 'concept', 'level': 'beginner'},
        ],
        'field_help': {
            'ida': 'Document identifier.',
            'name': 'Document title — shown in lists and search results.',
            'slug': 'URL-friendly identifier. Auto-generated from name if blank.',
            'purpose': 'Category — help, training, report, attachment, policy, etc.',
            'status': 'draft = not visible. published = visible to authorized users.',
            'body': 'Document content — supports Markdown formatting.',
            'description': 'Short summary shown in search results and document lists.',
            'confidential': 'public = anyone. internal = staff only. restricted = need-to-know.',
            'mime_type': 'File type for attachments — application/pdf, image/png, etc.',
            'path': 'File location — URL, local path, or storage reference.',
            'retention_period': 'Days to keep before auto-archive. 0 = keep forever.',
            'count_accessed': 'How many times this document has been opened. Alice tracks this.',
        },
        'actions': {
            'create': 'Set name, purpose, status. Write content in the body field.',
        },
        'warnings': [],
        'code_examples': [],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=document&status=published",
        },
    },

    'ai_message': {
        'tips': [
            {'id': 'msg-01', 'title': 'Messages are interactions', 'body': 'Every user-AI and AI-AI interaction is an AiMessage. Feedback, help lookups, agent observations, forwarded messages — all the same model.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'msg-02', 'title': 'Data never leaves without clearance', 'body': 'Commercial and personal data are auto-blocked. Only technical data with Athena clearance and PII scrubbing can be forwarded to WCHQ.', 'type': 'warning', 'level': 'beginner'},
            {'id': 'msg-03', 'title': 'Help frequency = confusion', 'body': 'help_lookup messages are counted per field. High frequency means users are confused — Alice flags these for admin attention.', 'type': 'concept', 'level': 'intermediate'},
        ],
        'field_help': {
            'kind': 'Message type: feedback, help_lookup, chat, question, answer, observation, directive, forward.',
            'status': 'pending = unprocessed. read = seen. reviewed = classified. actioned = task created. forwarded = sent on. resolved = done.',
            'sender': 'Who sent it — user login name or agent name (alice, allie, noelle, etc.).',
            'sender_contact_id': 'Contact record ID when sender is a user. Null for agents.',
            'receiver': 'Who receives it — agent name, user name, or wchq.',
            'receiver_contact_id': 'Contact record ID when receiver is a user. Null for agents.',
            'subject': 'Short subject line. Auto-generated from context if blank.',
            'body': 'The message content — feedback text, question, observation, etc.',
            'context': 'What the sender was looking at: model, field, page, component, source_path.',
            'classification': 'Data sensitivity: technical (safe), operational (review), commercial (never leaves), personal (never leaves).',
            'clearance': 'Athena gate: local (not reviewed), pending (in queue), cleared (safe to forward), blocked (sensitive data).',
            'scrubbed': 'True after PII scrubbing. Forward requires scrubbed=True.',
            'parent': 'Links replies in a thread. Self-FK.',
            'forward_of': 'Original message this was forwarded from. Tracks provenance.',
            'batch_id': 'Groups related messages. All messages from one help session share a batch_id.',
            'source_instance': 'UUID of the WC3 instance that created this message. For sync.',
        },
        'actions': {
            'feedback': 'User submits via Feedback button in Get Help dialog.',
            'review': 'Alice reviews pending feedback and classifies. Admin approves or edits.',
            'forward': 'Alice requests Athena clearance, then forwards technical messages to WCHQ.',
        },
        'warnings': [
            'Commercial data (prices, orders, customer names) must NEVER leave the instance.',
            'Personal data (contact info, login, PII) must NEVER leave the instance.',
            'Only technical data (wc/react/system) with Athena clearance + scrubbing can be forwarded.',
        ],
        'code_examples': [],
        'api_reference': {
            'list': "GET /wcapi/get/?model_name=ai_message&kind=feedback&status=pending",
            'frequency': "GET /wcapi/get/?model_name=ai_message&kind=help_lookup&ordering=-dt_created",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Page-level help — form objects, UI sections, toolbar items
# ─────────────────────────────────────────────────────────────────────────────

PAGE_HELP = {
    # Transaction detail form sections
    'bill_to': 'Bill-to address block — who gets the invoice. Pulled from customer communications.',
    'ship_to': 'Ship-to address block — where goods are delivered. Can differ from bill-to.',
    'item_code': 'Line item entry — add products/services to this transaction.',
    'FINANCIALS': 'Financial summary — GL posting status, journal entries, payment history.',
    'SELL TOTALS': 'Sales totals — subtotal, tax, shipping, grand total for this transaction.',
    # Toolbar buttons
    'btn-save': 'Save all changes to this record.',
    'btn-add': 'Create a new blank record for this model.',
    'btn-discard': 'Discard unsaved changes and reload from database.',
    'btn-cancel': 'Cancel/void this transaction. Creates a reversal if already posted.',
    'btn-report': 'Print or export — invoice, pick list, packing slip, statement.',
    'btn-reassign': 'Change the customer/vendor on this transaction.',
    'btn-related': 'Show records linked to this one — orders, invoices, payments, actions.',
    # List toolbar
    'btn-filter': 'Filter records by field values. Combine multiple filters with AND.',
    'btn-all': 'Show all records (clear current filter/subset).',
    'btn-subset': 'Show only the currently selected records.',
    'btn-omit': 'Hide the currently selected records.',
    'btn-sort': 'Sort by one or more columns. Click again to reverse.',
    # Navigation
    'sidebar': 'Main navigation — click to switch models. Shift-click opens in DataBrowser.',
    'breadcrumb': 'Shows current model and record. Click segments to navigate back.',
    # Line items
    'line-item-grid': 'Line items — products/services on this transaction. + Item to add rows.',
    'line-qty': 'Quantity ordered/invoiced. Drives extended price calculation.',
    'line-price': 'Unit price — resolved from price chain (catalog → contract → level → base).',
    'line-extended': 'Qty × price. Calculated — editing qty or price recalculates.',
    # JSON panels
    'panel-actions': 'Action items linked to this record. Create tasks, track follow-ups.',
    'panel-comments': 'Internal notes. Not visible to customers on printed documents.',
    'panel-config': 'Custom configuration — ship-to overrides, special handling, preferences.',
    'panel-metadata': 'System data — health score, Alice observations, computed analytics.',
    'panel-refs': 'Related record links. Denormalized cache — FKs are authoritative.',
    'panel-prefs': 'User/contact preferences for this record context.',
}


# ─────────────────────────────────────────────────────────────────────────────
# Document records — how-to guides
# ─────────────────────────────────────────────────────────────────────────────

DOCUMENTS = [
    {
        'name': 'Getting Started with WebClerk',
        'slug': 'getting-started',
        'description': 'First steps for new users — creating customers, entering orders, generating invoices.',
        'body': '''# Getting Started with WebClerk

## Step 1: Create a Customer
Navigate to Orgs → Customer. Click + New. Enter the display name and set status to active. Save.

## Step 2: Add Communications
On the customer detail page, go to the Communications tab. Add email, phone, and address.

## Step 3: Create an Order
Click "New Order" on the customer page. Add line items — each needs an item and quantity.

## Step 4: Convert to Invoice
When the order is fulfilled, convert it to an invoice. Review totals, then set status to released.

## Step 5: Apply Payment
When the customer pays, go to Payments → Apply Payments. Select the invoice and enter the amount.

## Step 6: Export to Accounting
Use the GL Journal Export to send financial data to your accounting program (QuickBooks, Xero, etc.).

All operations go through wcapi — one gate, one security model, one audit trail.
''',
        'status': 'published',
        'model_name': 'system',
        'confidential': 'public',
    },
    {
        'name': 'DataBrowser Guide',
        'slug': 'databrowser-guide',
        'description': 'How to use the DataBrowser for any model — search, sort, layouts, field config.',
        'body': '''# DataBrowser Guide

The DataBrowser at /admin-wb lets you browse, search, and edit any model in WebClerk.

## Selecting a Model
Click the model name in the header or press Cmd/Ctrl+Shift+M. Type to filter, arrow keys to navigate, Enter to select.

## Searching
Type in the search box — searches the database after 400ms. Results are paginated (50 per page).

## Column Configuration
Click "List Cols" to toggle columns on/off. Drag column headers to reorder. Drag the right edge to resize.

## Saved Layouts
Click "Save" to name and save the current field selection, order, and widths. Click a layout name to load it. Shift-click to delete.

## Form Layout
Click "Form" to open the detail form layout editor. Reorder fields, toggle visibility, set row sizes for text/JSON fields.

## Field Behaviors
Labels are color-coded: blue = clickable action (email, phone, map), green = select list, purple = FK lookup. Click blue labels to launch the action.

## Shift-Click Power User
Shift-click any model in the sidebar to open it in the DataBrowser instead of its dedicated page.

## Keyboard Shortcuts
- Cmd/Ctrl+Shift+M — toggle model picker
- Arrow Up/Down — navigate records in list
- Escape — close model picker
''',
        'status': 'published',
        'model_name': 'system',
        'confidential': 'public',
    },
    {
        'name': 'wcapi Reference',
        'slug': 'wcapi-reference',
        'description': 'API reference for all wcapi endpoints — the single gate for all CRUD operations.',
        'body': '''# wcapi API Reference

All data operations flow through wcapi. No exceptions.

## Endpoints

### GET /wcapi/get/
List or retrieve records.
- `?model_name=customer` — list all customers
- `?model_name=customer&id=42` — get single record with related data
- `?keyword=acme` — search
- `?status=active` — filter
- `?ordering=-dt_created` — sort (prefix - for desc)
- `?limit=50&offset=0` — pagination

### POST /wcapi/save/
Create or update a record.
```json
{
  "model_name": "customer",
  "id": 42,
  "display_name": "Acme Corp",
  "status": "active"
}
```
Omit `id` to create new. Include `id` to update.

### POST /wcapi/delete/
Soft-delete a record.
```json
{"model_name": "customer", "id": 42}
```

### POST /wcapi/manage/
Administrative actions (GL posting, tally reports, etc.).
```json
{"action": "post_gl", "model_name": "invoice", "id": 42}
```

### GET /wcapi/model_name/list/
List all available model names.

### GET /wcapi/model_name/detail/?model_name=customer
Get field metadata for a model.

## Security
Every request requires JWT auth. Role-based query scoping restricts external users to their own data. Field filtering strips unauthorized fields from responses. See readmes/wcapi-query-scoping.md.
''',
        'status': 'published',
        'model_name': 'system',
        'confidential': 'internal',
    },
    {
        'name': 'Pricing Architecture',
        'slug': 'pricing-architecture',
        'description': 'How WC3 resolves prices: catalogs, price levels, qty breaks, margin warnings. The full chain explained.',
        'body': '''# Pricing Architecture

## The Chain
Every line item resolves its price through this chain (first match wins):

1. **Catalog item-specific** — item listed in an active catalog for this customer
2. **OrgItem contract** — customer-specific price override
3. **Customer price_level** — retail, wholesale, distributor, or sample
4. **Explicit level** — line or header override
5. **Item base price** — fallback

After the price resolves: quantity breaks adjust it, then universal catalog % discounts apply.

## Price Levels
Four levels stored on each item: retail, wholesale, distributor, sample. Plus base (list) and msrp.

## Quantity Breaks
JSON on the item — each break row has per-level columns (dollar and/or percentage):
```json
{"min_qty": 25, "base": 14.00, "retail": 11.00, "wholesale_pct": 33.3}
```
Dollar wins. Percentage calculates from base. Alice recalculates when base changes.

## Catalogs
Two modes: item-specific (CatalogLine with fixed price) or universal % (blanket discount on all products). Catalogs target customers by org FK, contact list, contact type, or "all."

## Margin Warning
If the resolved price falls below the margin floor (default 15%), `below_margin_floor` is flagged. **The system warns — it never overrides the user's price.**

Full readme: readmes/topics/transactions/pricing-architecture.md
''',
        'status': 'published',
        'model_name': 'system',
        'confidential': 'public',
    },
    {
        'name': 'Payment Application',
        'slug': 'payment-application',
        'description': 'How payments work: apply to invoices, early payment discounts, write-off differences, unapplied payments, AR aging.',
        'body': '''# Payment Application

## The One Rule
Every dollar gets its own Payment record. Cash, discounts, and write-offs are all Payment records with their own GL posting and audit trail.

## Three Payment Types

| Type | When | Example |
|------|------|---------|
| **Cash/check/card** | Normal payment | Customer pays $980 |
| **Early payment discount** | Within terms window | 2/10 Net 30 → $20 discount auto-created |
| **Write-off difference** | Small balance not worth collecting | $0.50 remaining → write off |

## Early Payment Discount
Invoice has terms "2/10 Net 30". Customer pays within 10 days. System auto-creates a discount Payment for 2% of the invoice total. Two Payment records close the invoice: cash + discount.

## Write-Off Difference
Check the "Write off difference" box when applying payment. Any remaining balance becomes a write-off Payment posted to the write-off GL account.

## Unapplied Payments
Payment with no invoice number → sits as unapplied. Reduces customer balance for credit check. Does NOT clear past-due invoices. Apply to specific invoices later.

## AR Aging (Alice Nightly)
Fixed buckets: Future, Current, Past 30, Past 60, Past 90+. Plus avgDaysPaid, highCredit, totalExposure.

Full readme: readmes/topics/transactions/payment-application.md
''',
        'status': 'published',
        'model_name': 'system',
        'confidential': 'public',
    },
    {
        'name': 'Journal Formatter — GL Export Tool',
        'slug': 'journal-formatter',
        'description': 'How to export GL journals and format them for your accounting program.',
        'body': '''# Journal Formatter — GL Export Tool

## What It Does

The Journal Formatter takes a bundle.json from WebClerk's GL Journal Export
and converts it into the file format your accounting program needs.

Same idea as Statement Sorter but in reverse:
- **Statement Sorter**: Bank CSV → WebClerk (inbound)
- **Journal Formatter**: WebClerk → QuickBooks/Xero/Sage (outbound)

## How to Use

1. **Export**: In WebClerk, go to GL Journals → Export. Select the period. Downloads `bundle.json`.
2. **Format**: Open `journal_formatter.html` in your browser (standalone — no server needed).
3. **Drop**: Drop `bundle.json` onto the page.
4. **Pick**: Select your accounting program. It remembers your choice for next time.
5. **Download**: Click Download. Import the file into your accounting program.

## Supported Programs

- QuickBooks Desktop (IIF format)
- QuickBooks Online (CSV)
- Xero (CSV)
- Sage 50/100 (CSV)
- FreshBooks (CSV)
- Generic CSV (works with anything)

## Multi-Location Companies

If your company has multiple locations, each running WebClerk:
- Each location exports its own bundle.json
- Bundles can be sent upstream to HQ for consolidation
- HQ downloads all locations' bundles and formats them together
- The accountant sees entries tagged by company — same format whether
  one location or fifty

## Key Rule

WebClerk produces GL journal entries. Your accounting program consumes them.
WebClerk does not do checkbooks, payables, or P&L — that is the accounting
program's job. Clean boundary, clean handoff.

Full readme: readmes/transactions/journal-formatter.md
''',
        'status': 'published',
        'model_name': 'gl_journal',
        'confidential': 'public',
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding action records — Alice assigns to new users
# ─────────────────────────────────────────────────────────────────────────────

ONBOARDING_ACTIONS = [
    {'action': {'en': 'Create your first customer'}, 'description': {'en': 'Go to Orgs → Customer, click + New, enter a display name and save.'}, 'sequence': 1, 'priority': 1},
    {'action': {'en': 'Add email and phone to a customer'}, 'description': {'en': 'Open a customer, go to Communications tab, add email and phone.'}, 'sequence': 2, 'priority': 1},
    {'action': {'en': 'Create your first order'}, 'description': {'en': 'From a customer page, click New Order. Add a line item with an item and quantity.'}, 'sequence': 3, 'priority': 1},
    {'action': {'en': 'Try the DataBrowser'}, 'description': {'en': 'Go to /admin-wb or press Cmd+Shift+M. Browse any model, try column config and layouts.'}, 'sequence': 4, 'priority': 2},
    {'action': {'en': 'Save a layout'}, 'description': {'en': 'In the DataBrowser, configure columns, then click Save Layout and name it.'}, 'sequence': 5, 'priority': 2},
    {'action': {'en': 'Print an invoice'}, 'description': {'en': 'Open an invoice, click Reports (🖨), select Invoice. Review the print format.'}, 'sequence': 6, 'priority': 2},
    {'action': {'en': 'Explore field behaviors'}, 'description': {'en': 'In the DataBrowser detail pane, notice color-coded labels. Click blue labels (email, phone, address) to test actions.'}, 'sequence': 7, 'priority': 3},
    {'action': {'en': 'Use the Form Layout editor'}, 'description': {'en': 'Click the Form button in the DataBrowser. Reorder fields, toggle visibility, set row sizes. Click Apply.'}, 'sequence': 8, 'priority': 3},
    {'action': {'en': 'Customize a select list'}, 'description': {'en': 'Dropdowns (status, priority, terms, shipping carrier, etc.) ship with starter options. Cmd+click any field label to add, rename, or remove options. These are YOUR lists — customize them to match your business.'}, 'sequence': 9, 'priority': 2},
]


class Command(BaseCommand):
    help = 'Seed Alice coaching content — Settings, Documents, and onboarding Actions'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing')

    def handle(self, *args, **options):
        force = options.get('force', False)
        now = _now_ms()

        # ── Coaching Settings ──
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding coaching Settings...'))
        s_created = s_updated = s_skipped = 0
        for model_key, content in COACHING.items():
            existing = Setting.objects.filter(parent_model=model_key, purpose='wc:coaching').first()
            data = {
                'tips': content.get('tips', []),
                'field_help': content.get('field_help', {}),
                'actions': content.get('actions', {}),
                'warnings': content.get('warnings', []),
                'code_examples': content.get('code_examples', []),
                'api_reference': content.get('api_reference', {}),
            }
            if existing and not force:
                s_skipped += 1
                continue
            try:
                coach_expl = f"Alice coaching tips and field help for {model_key}. Contextual guidance shown to users during data entry."
                if existing:
                    existing.config = data
                    existing.explanation = coach_expl
                    existing.save()
                    s_updated += 1
                else:
                    Setting.objects.create(name=f'alice_coaching:{model_key}', parent_model=model_key, purpose='wc:coaching', config=data, explanation=coach_expl)
                    s_created += 1
                self.stdout.write(f'  {model_key}: {len(data["tips"])} tips, {len(data["field_help"])} field helps')
            except Exception as e:
                s_skipped += 1
                self.stdout.write(self.style.WARNING(f'  {model_key}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Coaching: {s_created} created, {s_updated} updated, {s_skipped} skipped'))

        # ── Page Help Setting ──
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding page help...'))
        page_existing = Setting.objects.filter(parent_model='system', purpose='wc:coaching', name='alice_coaching:page_help').first()
        if page_existing and not force:
            self.stdout.write(f'  page_help: skipped (exists)')
        else:
            page_data = {'page_help': PAGE_HELP, 'field_help': {}, 'tips': [], 'warnings': []}
            try:
                if page_existing:
                    page_existing.config = page_data
                    page_existing.save()
                else:
                    Setting.objects.create(
                        name='alice_coaching:page_help', parent_model='system',
                        purpose='wc:coaching', config=page_data,
                        explanation='Page-level help for form objects, toolbar buttons, and UI sections.',
                    )
                self.stdout.write(f'  page_help: {len(PAGE_HELP)} entries')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  page_help: {e}'))

        # ── Documents ──
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding coaching Documents...'))
        d_created = d_skipped = 0
        for doc in DOCUMENTS:
            exists = Document.objects.filter(slug=doc['slug']).exists()
            if exists and not force:
                d_skipped += 1
                continue
            if exists:
                Document.objects.filter(slug=doc['slug']).update(
                    name=doc['name'], description=doc['description'], body=doc['body'],
                    status=doc['status'], model_name=doc.get('model_name', ''),
                    dt_modified=now,
                )
                d_created += 1  # count as refreshed
            else:
                Document.objects.create(
                    name=doc['name'], slug=doc['slug'], description=doc['description'],
                    body=doc['body'], status=doc['status'],
                    model_name=doc.get('model_name', ''),
                    confidential=doc.get('confidential', 'internal'),
                    dt_created=now, dt_modified=now,
                )
                d_created += 1
            self.stdout.write(f'  Doc: {doc["name"]}')

        self.stdout.write(self.style.SUCCESS(f'Documents: {d_created} created, {d_skipped} skipped'))

        # ── Onboarding Actions ──
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding onboarding Actions...'))
        a_created = a_skipped = 0
        for act in ONBOARDING_ACTIONS:
            title = act['action'].get('en', '')
            exists = Action.objects.filter(
                action__en=title,
                project_name='Alice Onboarding',
            ).exists()
            if exists:
                a_skipped += 1
                continue
            Action.objects.create(
                action=act['action'],
                description=act.get('description', {}),
                sequence=act.get('sequence', 0),
                priority=act.get('priority', 1),
                kanban_column='todo',
                status='open',
                project_name='Alice Onboarding',
                project_ida='alice-onboarding',
                dt_created=now,
                dt_modified=now,
                metadata={'health': 'seed', 'coaching': True},
            )
            a_created += 1
            self.stdout.write(f'  Action: {title}')

        self.stdout.write(self.style.SUCCESS(f'Onboarding actions: {a_created} created, {a_skipped} skipped'))
