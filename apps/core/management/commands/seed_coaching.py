"""
seed_coaching — Alice's coaching content: Setting records + Document records + Action records.

Usage:
    ./bin/python manage.py seed_coaching
    ./bin/python manage.py seed_coaching --force

Creates:
  - Setting records (purpose='alice_coaching') — one per key model with tips, field_help, etc.
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
            'display_name': 'The primary name shown in lists and on printed documents.',
            'status': 'active = doing business. prospect = potential. inactive = paused. retired = closed.',
            'price_level': 'Determines which price tier is used on orders/invoices for this customer.',
            'terms': 'Payment terms (N30, COD, 2/10 Net 30). Sets when payment is due.',
            'email': 'Primary email — click the label to compose. Synced from communications.',
            'phone': 'Primary phone — click the label to dial. Synced from communications.',
            'address_full': 'Primary address — click the label to open in Google Maps.',
            'attention': 'Who to address correspondence to at this organization.',
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
            'total': 'Sum of all line items. Edit lines to change — total recalculates automatically.',
            'balance': 'Total minus payments received. Read-only. Updated when payments are applied.',
            'status': 'planned = draft. released = sent to customer. complete = paid and closed.',
            'terms': 'Payment terms — determines due date on the ledger record.',
            'price_level': 'Price tier used for line item pricing on this invoice.',
        },
        'actions': {
            'create': 'Select a customer, set status to planned, add line items with items and quantities.',
            'print': 'Click Reports (🖨) button → Invoice. Opens printable format.',
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
            'total': 'Sum of line items. Recalculates when lines are added/changed.',
            'status': 'planned = not started. released = being fulfilled. complete = shipped/delivered.',
            'priority': 'Helps warehouse sort what to pick first.',
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
            'total': 'Proposed total — what the customer would pay if they accept.',
            'status': 'planned = draft. released = sent to customer. complete = accepted or expired.',
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
            'total': 'Total cost of all purchase lines.',
            'status': 'planned = draft. released = sent to vendor. complete = fully received.',
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

    'item': {
        'tips': [
            {'id': 'item-01', 'title': 'Items are what you sell and buy', 'body': 'Every line on an order, invoice, or PO references an item. Items have prices, costs, and inventory.', 'type': 'concept', 'level': 'beginner'},
            {'id': 'item-02', 'title': 'Margin velocity', 'body': 'The real metric: (margin × annual turns) ÷ carry cost. High velocity = productive inventory.', 'type': 'concept', 'level': 'advanced'},
        ],
        'field_help': {
            'sku': 'Stock keeping unit — your internal product code.',
            'name': 'Display name shown on documents and in search.',
            'kind': 'product = physical goods. service = labor/time. bundle = kit of items.',
            'uom': 'Unit of measure — ea, lb, ft, box, etc.',
            'status': 'active = available for sale. discontinued = no longer sold.',
            'price_level': 'Prices stored in the price JSON by level (retail, wholesale, distributor).',
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
            'kanban_column': 'backlog → todo → in_progress → review → done. Drag in Kanban view.',
            'priority': 'Higher number = higher priority. 1 = low, 5 = urgent.',
            'percent_complete': '0-100. Update as work progresses.',
            'dt_deadline': 'When this task is due. Shows in red when overdue.',
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
            'email': 'Login email — also used as the primary communication email.',
            'role': 'admin, manager, sales, warehouse, accounting, customer, vendor, rep.',
            'company': 'Company affiliation — may differ from org.display_name.',
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
            existing = Setting.objects.filter(parent_model=model_key, purpose='alice_coaching').first()
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
                if existing:
                    existing.config = data
                    existing.save()
                    s_updated += 1
                else:
                    Setting.objects.create(name=f'alice_coaching:{model_key}', parent_model=model_key, purpose='alice_coaching', config=data)
                    s_created += 1
                self.stdout.write(f'  {model_key}: {len(data["tips"])} tips, {len(data["field_help"])} field helps')
            except Exception as e:
                s_skipped += 1
                self.stdout.write(self.style.WARNING(f'  {model_key}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Coaching: {s_created} created, {s_updated} updated, {s_skipped} skipped'))

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
                    status=doc['status'], model_name=doc['model_name'],
                    dt_modified=now,
                )
                d_created += 1  # count as refreshed
            else:
                Document.objects.create(
                    name=doc['name'], slug=doc['slug'], description=doc['description'],
                    body=doc['body'], status=doc['status'], model_name=doc['model_name'],
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
