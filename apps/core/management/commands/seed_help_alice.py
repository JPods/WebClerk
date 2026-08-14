"""Seed Document records for Alice help — one per UI component.

Each Document has purpose='help-alice', the component name, source path,
description of what it does, and how to work with it. Alice searches these
when users paste component names into Get Help.

Usage:
    python manage.py seed_help_alice
    python manage.py seed_help_alice --force  # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document

# Component name → help content
# Grouped by role: detail pages, panels, cards, modals, utilities
COMPONENTS = [
    # ── Detail pages (indigo) ─────────────────────────────────────────
    {
        'name': 'ContactDetailJson',
        'source': 'apps/core/models/contact/pages/ContactDetailJson.tsx',
        'description': 'Contact detail form — the richest model in the system.',
        'body': (
            'ContactDetailJson renders the contact detail page using a JSON layout '
            'from the detail_layout Setting (model_name=contact). Three-column header '
            '(contact info, address, profile) plus tabbed sections (communications, '
            'transactions, documents, actions, metadata).\n\n'
            'To change field arrangement: open the contact, enter Design Mode, drag fields.\n'
            'To change field behavior: edit the field_behaviors Setting for contact.\n'
            'To add a tab: add a section to the detail_layout Setting JSON.\n\n'
            'Contact is the only model with role-conditional prefs: staff, employee, rep, '
            'cart sections activate based on the contact\'s role. See common/schemas/contact.py.'
        ),
    },
    {
        'name': 'ItemDetailJson',
        'source': 'apps/products/pages/ItemDetailJson.tsx',
        'description': 'Item detail form — products, inventory, serial numbers.',
        'body': (
            'ItemDetailJson renders the item detail page using a JSON layout from the '
            'detail_layout Setting (model_name=item). Shows product data, variants, '
            'BOM (bill of materials), serial numbers, specifications.\n\n'
            'To change field arrangement: enter Design Mode.\n'
            'Product-specific panels: BomPanel, SerialPanel, ProductListPanel (warehouse, '
            'variant, xref, spec cards).'
        ),
    },
    {
        'name': 'TransactionDetail',
        'source': 'apps/transactions/components/TransactionDetail.tsx',
        'description': 'Shared transaction renderer — orders, invoices, proposals, purchases.',
        'body': (
            'TransactionDetail is the single renderer for all transaction types. It reads '
            'the detail_layout Setting for the specific model (order, invoice, proposal, '
            'purchase, receipt, requisition, work_order) and renders the form.\n\n'
            'Built from 8 single-purpose components: HeaderRenderer, FieldRow, '
            'LineCardRenderer, TabsRenderer, DesignMode, TransactionPrint, PackingPanel, '
            'CustomerSearch.\n\n'
            'To change layout: edit the detail_layout Setting for the transaction type.\n'
            'To change line card fields: edit the line_card_fields Setting.\n'
            'To change print output: edit the print_layout Setting or the print component '
            'in apps/transactions/components/print/.'
        ),
    },
    {
        'name': 'DynamicDetail',
        'source': 'components/common/DynamicDetail.tsx',
        'description': 'Generic data-driven form renderer — renders any model from JSON layout.',
        'body': (
            'DynamicDetail reads a layout definition (JSON) and renders a form. It is the '
            'core of the Data-Driven UI architecture. 455 lines replace 45,091 lines of '
            'hand-coded detail pages.\n\n'
            'Layout format: { rows: [{ fields: ["field1", "field2"], cols: 2 }] }\n'
            'Stored in: Setting record with purpose=wc:detail_layout, model_name=<model>\n\n'
            'Users can toggle Arrange mode to drag rows, add/remove fields. Changes save '
            'back to the Setting. No code changes needed.\n\n'
            'Widget registry: 10 widgets (text, select, date, number, json-tree, lookup, etc.)\n'
            'Field behaviors come from the field_behaviors Setting per model.'
        ),
    },
    {
        'name': 'OrgDetailJson',
        'source': 'apps/orgs/components/OrgDetail.json.tsx',
        'description': 'Organization detail — shared by customer, vendor, manufacturer, employee, rep.',
        'body': (
            'OrgDetailJson renders all five org model types using a JSON layout from the '
            'detail_layout Setting. The layout is per-model (customer, vendor, etc.).\n\n'
            'Supported by OrgCard (summary), OrgPanel (list), OrgFinancialsPanel (AR/AP), '
            'OrgMetricsPanel (sales history), CommunicationsPanel.\n\n'
            'To change layout: edit detail_layout Setting for the specific org type.'
        ),
    },
    {
        'name': 'BundleDetail',
        'source': 'apps/sync/models/bundle/pages/BundleDetail.tsx',
        'description': 'Sync bundle viewer — records exchanged between installations.',
        'body': (
            'BundleDetail shows the contents of a sync bundle — which records were sent '
            'or received, their status, any conflicts. Used for troubleshooting sync issues '
            'between WebClerk installations.\n\n'
            'Bundles are the transport unit for the sync protocol (Connection + Bundle model).'
        ),
    },
    {
        'name': 'SprintBurndown',
        'source': 'apps/core/models/action/pages/SprintBurndown.tsx',
        'description': 'Sprint burndown chart — tracks project action completion over time.',
        'body': (
            'SprintBurndown renders a burndown chart for a project\'s actions. Shows planned '
            'vs actual completion rate. Data comes from the burndown API endpoint.\n\n'
            'Filtered by project. Actions are the work units (not tasks — actions have '
            'who/what/when/status).'
        ),
    },
    # ── DataBrowser ───────────────────────────────────────────────────
    {
        'name': 'DataBrowser',
        'source': 'pages/admin/DataBrowser.tsx',
        'description': 'Universal data browser — lists and details for any model.',
        'body': (
            'DataBrowser is the single page that renders list and detail views for every '
            'model in the system. Column configuration comes from the workbench_fields '
            'Setting per model.\n\n'
            'Features: column resize/reorder, saved layouts, font size, dark/light mode, '
            'search, pagination, right-click column management.\n\n'
            'To change columns: right-click column header or use List Order button.\n'
            'To save a layout: arrange columns, click Save Layout, name it.\n'
            'System layouts (alice_guess, alphabetical) cannot be overwritten.\n\n'
            'Access at /db/<model_name> or /admin-wb?model=<model_name>.'
        ),
    },
    # ── Panels (teal) ─────────────────────────────────────────────────
    {
        'name': 'CommPanel',
        'source': 'apps/communications/components/CommPanel.tsx',
        'description': 'Communications panel — emails, phones, addresses for a contact.',
        'body': (
            'CommPanel renders a contact\'s communication records (email, phone, address, '
            'domain) as CommCards. 65 lines — replaced CommunicationsPanel (1,704 lines).\n\n'
            'Each CommCard shows the communication record with inline editing. '
            'Add new communications via the + button per type.'
        ),
    },
    {
        'name': 'CustomerSalesPanel',
        'source': 'apps/transactions/components/CustomerSalesPanel.tsx',
        'description': 'Customer sales history panel — shown on customer and contact detail.',
        'body': (
            'Shows transaction history for a customer: orders, invoices, proposals, '
            'payments. Includes totals, aging, and trend data. Embedded as a tab in '
            'OrgDetailJson and ContactDetailJson.'
        ),
    },
    {
        'name': 'OrgFinancialsPanel',
        'source': 'apps/orgs/components/OrgFinancialsPanel.tsx',
        'description': 'Organization financials — AR/AP balances, payment history, aging.',
        'body': (
            'Shows financial summary for any org type: outstanding balance, payment history, '
            'aging buckets, credit limit utilization. Tab in OrgDetailJson.'
        ),
    },
    {
        'name': 'CustomerDataPanel',
        'source': 'apps/orgs/models/customer/pages/CustomerDataPanel.tsx',
        'description': 'Customer-specific data panel — pricing, terms, credit.',
        'body': (
            'Customer-specific fields beyond the base org: price level, payment terms, '
            'credit limit, tax exempt status, shipping preferences. Tab in customer detail.'
        ),
    },
    {
        'name': 'OrgMetricsPanel',
        'source': 'apps/orgs/components/OrgMetricsPanel.tsx',
        'description': 'Organization metrics — sales volume, order frequency, margin trends.',
        'body': (
            'Computed metrics for any org type: total sales, average order value, '
            'order frequency, margin history. Data from transaction aggregations.'
        ),
    },
    {
        'name': 'MetadataPanel',
        'source': 'apps/transactions/components/MetadataPanel.tsx',
        'description': 'Transaction metadata panel — audit trail, GL postings, system info.',
        'body': (
            'Shows system-managed metadata for a transaction: audit trail entries, GL '
            'posting status, sync state, import provenance. Read-only for users. '
            'Tab in TransactionDetail.'
        ),
    },
    # ── Cards (amber) ─────────────────────────────────────────────────
    {
        'name': 'ContactCard',
        'source': 'apps/core/models/contact/pages/ContactCard.tsx',
        'description': 'Contact summary card — compact view for embedding in other pages.',
        'body': (
            'Compact contact display: name, company, primary email/phone. Used inside '
            'transaction headers (bill-to, ship-to), org panels, and search results.'
        ),
    },
    {
        'name': 'TaskCard',
        'source': 'apps/utils/kanban/TaskCard.tsx',
        'description': 'Kanban task card — one action on the Kanban board.',
        'body': (
            'Renders a single action as a draggable card on the Kanban board. Shows '
            'action name, assigned_to, priority, difficulty, deadline. Drag between '
            'status columns to update.'
        ),
    },
    {
        'name': 'SummaryCard',
        'source': 'apps/transactions/components/SummaryCard.tsx',
        'description': 'Transaction summary card — totals, tax, shipping, balance.',
        'body': (
            'Shows transaction totals: subtotal, tax, shipping, discount, total, '
            'payments applied, balance due. Updates in real-time as lines change. '
            'Calculations are server-side (backend is source of truth).'
        ),
    },
    {
        'name': 'ComponentCard',
        'source': 'components/common/ComponentCard.tsx',
        'description': 'Generic card wrapper — consistent styling for any embedded component.',
        'body': (
            'Wrapper component providing consistent card styling: border, padding, '
            'header, collapse/expand. Used by detail pages to wrap panels and sections.'
        ),
    },
    # ── Kanban / Gantt ────────────────────────────────────────────────
    {
        'name': 'KanbanBoardPage',
        'source': 'apps/utils/kanban/KanbanBoardPage.tsx',
        'description': 'Kanban board — drag actions between status columns.',
        'body': (
            'Full Kanban board for project management. Actions are cards, columns are '
            'statuses (open, in progress, blocked, completed). Drag to change status.\n\n'
            'Filter by project. Supports multiple project views. Action detail opens '
            'in a floating window on click.'
        ),
    },
    {
        'name': 'UnifiedGantt',
        'source': 'apps/utils/gantt/UnifiedGantt.tsx',
        'description': 'Gantt chart — action timelines with dependencies.',
        'body': (
            'Gantt chart rendering action timelines. Shows start/deadline dates, '
            'dependencies (parents in refs.parents), percent complete, assigned_to.\n\n'
            'Filter by project. Drag to reschedule. Click for detail editing.'
        ),
    },
    # ── Modals (rose) ─────────────────────────────────────────────────
    {
        'name': 'LineDetailsModal',
        'source': 'apps/transactions/components/LineDetailsModal.tsx',
        'description': 'Line item detail editor — full edit view for a transaction line.',
        'body': (
            'Opens when clicking a line item in a transaction. Shows all line fields: '
            'item, quantity, price, discount, tax, commission, description, specs. '
            'Calculations update in real-time. Save returns to the transaction.'
        ),
    },
    {
        'name': 'ActionsModal',
        'source': 'apps/transactions/components/ActionsModal.tsx',
        'description': 'Transaction actions modal — convert, ship, apply payment.',
        'body': (
            'Manages transaction lifecycle actions: Convert to Order, Convert to Invoice, '
            'Ship Order, Apply Payment, Print. Each action calls a manage_view endpoint. '
            'Available actions depend on transaction type and status.'
        ),
    },
    {
        'name': 'AddPaymentModal',
        'source': 'apps/transactions/components/AddPaymentModal.tsx',
        'description': 'Add payment dialog — record a payment against an invoice.',
        'body': (
            'Create a new payment record: amount, method, reference number, date. '
            'Payment applies against the selected invoice. Backend creates the Payment '
            'record and GL journal entries.'
        ),
    },
    {
        'name': 'KanbanTaskModal',
        'source': 'apps/utils/kanban/KanbanTaskModal.tsx',
        'description': 'Action detail editor in Kanban — full edit within the board.',
        'body': (
            'Floating editor for actions within the Kanban board. Edit all action fields '
            'without leaving the board. Supports comments, attachments, dependencies.'
        ),
    },
    # ── Navigation ────────────────────────────────────────────────────
    {
        'name': 'AppSidebar',
        'source': 'layout/AppSidebar.tsx',
        'description': 'Main navigation sidebar — model list, dashboards, search.',
        'body': (
            'The left sidebar navigation. Model list is configured from '
            'contact.prefs.staff.nav (NavPrefs in Pydantic schema). Dashboards section '
            'shows Kanban, Gantt, item, accounting, alice, databrowser.\n\n'
            'To change which models appear: edit your contact\'s prefs.staff.nav.models array.\n'
            'To change dashboards: edit prefs.staff.nav.dashboards array.'
        ),
    },
    # ── Utilities ─────────────────────────────────────────────────────
    {
        'name': 'ModelScaffold',
        'source': 'apps/utils/scaffold/ModelScaffold.tsx',
        'description': 'Model scaffold — auto-generates list + detail for new models.',
        'body': (
            'Development tool. Auto-generates a working list and detail page for any '
            'model registered in MODEL_REGISTRY. Used to quickly prototype new models '
            'before building proper layouts.'
        ),
    },
    {
        'name': 'AllModelsWorkbench',
        'source': 'apps/utils/scaffold/AllModelsWorkbench.tsx',
        'description': 'All models workbench — overview of every registered model.',
        'body': (
            'Development tool. Shows every model in MODEL_REGISTRY with record counts, '
            'field lists, and quick navigation. Useful for understanding the data model.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed Document records for Alice help — one per UI component'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing records')

    def handle(self, *args, **options):
        force = options['force']
        created = 0
        updated = 0
        skipped = 0

        for comp in COMPONENTS:
            ida = f"help-alice-{comp['name'].lower()}"
            existing = Document.objects.filter(ida=ida).first()

            if existing and not force:
                skipped += 1
                continue

            defaults = {
                'name': comp['name'],
                'purpose': 'help-alice',
                'description': comp['description'],
                'body': comp['body'],
                'status': 'active',
                'path': {'source': comp['source']},
                'config': {
                    'component_name': comp['name'],
                    'source_path': comp['source'],
                },
            }

            obj, was_created = Document.objects.update_or_create(
                ida=ida,
                defaults=defaults,
            )

            if was_created:
                created += 1
                self.stdout.write(f'  Created: {comp["name"]}')
            else:
                updated += 1
                self.stdout.write(f'  Updated: {comp["name"]}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {created} created, {updated} updated, {skipped} skipped'
        ))
