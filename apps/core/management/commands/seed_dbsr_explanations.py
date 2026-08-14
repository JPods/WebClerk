"""
seed_dbsr_explanations — Populate .metadata.explanation on all database supporting records.

Database Supporting Records (DBSRs) are the Settings and Reports that configure
how WC3 operates: field access, layouts, schema maps, search presets, GL defaults,
Alice coaching, feature flags, and report templates.

Each DBSR gets a plain-English explanation of what it does, why it exists, and how
it affects the user experience. The explanation lives at metadata.explanation —
immediately available without any lookup.

After populating, run seed_dbsr_document to generate the consolidated index.

Usage:
    python manage.py seed_dbsr_explanations
    python manage.py seed_dbsr_explanations --force   # overwrite existing explanations
    python manage.py seed_dbsr_explanations --dry-run  # show what would be written
"""
import json
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from apps.core.models.report import Report


# ═══════════════════════════════════════════════════════════════════════
# Purpose-level explanation templates
# ═══════════════════════════════════════════════════════════════════════
# {model} is replaced with the parent_model name (e.g., "contact", "order")

PURPOSE_EXPLANATIONS = {
    'wc:field_access': (
        'Controls which fields on the {model} record are visible and editable '
        'by role. External users see only fields listed in their role\'s view '
        'list. Internal users see all fields unless explicitly restricted. '
        'This is the RBAC field filter — it runs on every API response.'
    ),
    'wc:workbench_fields': (
        'Defines the DataBrowser column layout for {model} records. '
        'config.db.list controls which columns appear in the list view and their '
        'widths. config.db.detail controls the detail panel fields. '
        'config.db.panel controls embedded sub-panels (line items, related records). '
        'Users can customize via Design Mode; this is the system default.'
    ),
    'wc:schema_map': (
        'Documents the Pydantic schema for the {model} model — every JSON envelope '
        'field (metadata, refs, prefs, config, comments, actions) with its type, '
        'default, and purpose. This is the contract: any code reading or writing '
        '{model} JSON fields must conform to this schema. Alice uses it to validate '
        'data quality. Sync uses it to map fields between installations.'
    ),
    'wc:search': (
        'A saved search preset for {model} records. Appears in the search dropdown '
        'so users can quickly filter by common criteria (e.g., current month, '
        'active status, assigned to me). Shared across all users by default; '
        'users can also save personal searches in their prefs.'
    ),
    'wc:detail_layout': (
        'Defines the app-level detail view layout for {model} records — which fields '
        'appear, their order, grouping, and display format. This is the structured '
        'business form (as opposed to the DataBrowser raw field view). '
        'The layout is JSON-driven via DynamicDetail.'
    ),
    'wc:db_defaults': (
        'Default values applied to new {model} records at creation time. '
        'Includes GL account assignments, status defaults, and standard field '
        'values. These save data entry time and ensure consistency across '
        'the installation.'
    ),
    'wc:selectlist': (
        'Defines the dropdown/select list options for {model} fields. '
        'These are the pick lists users choose from — statuses, types, '
        'categories, and other controlled vocabularies. Centralizing them '
        'here ensures consistency and makes them syncable between installations.'
    ),
    'wc:keywords': (
        'Keyword index for {model} records — extracted automatically from '
        'key fields to enable fast full-text search. Alice refreshes these '
        'periodically. The keyword list determines what users find when they '
        'type in the search bar.'
    ),
    'wc:coaching': (
        'Instructions for Alice (the AI assistant) on how to handle {model} '
        'records. Includes field validation rules, data quality checks, '
        'common patterns to watch for, and recommended actions. Alice reads '
        'these at startup and applies them during her observation cycles.'
    ),
    'wc:print_layout': (
        'Print template layout for {model} documents. Defines which fields '
        'appear on the printed/PDF output, their positions, and formatting. '
        'Used by the PrintDocumentLayout component and the pdfme designer. '
        'This is the system default; users can customize per-document.'
    ),
    'wc:model_related': (
        'Defines which related models are shown as panels when viewing a '
        '{model} record. For example, viewing a customer shows their orders, '
        'invoices, and contacts as sub-panels. Controls the relationship '
        'navigation experience.'
    ),
    'wc:enrichment_panels': (
        'Configures the enrichment sidebar panels for {model} records. '
        'These panels show contextual data — purchase history, credit status, '
        'Alice insights — alongside the main record. They help users make '
        'decisions without leaving the current view.'
    ),
    'wc:conditions_sales': (
        'Sales conditions and terms templates for {model} transactions. '
        'These are the standard terms, disclaimers, and conditions that '
        'appear on proposals, orders, and invoices. Editable per transaction '
        'but seeded from these defaults.'
    ),
    'wc:config': (
        'System configuration for {model} behavior. Controls processing '
        'rules, feature settings, and operational parameters that affect '
        'how {model} records are created, validated, and processed.'
    ),
    'wc:feature': (
        'Feature flag controlling a specific WC3 capability. When active, '
        'the feature is available to users. When inactive, it is hidden '
        'from the UI and disabled in the API. Used for staged rollouts '
        'and installation-specific customization.'
    ),
    'wc:company_profile': (
        'The installation\'s company identity — name, address, logo, tax IDs, '
        'and business settings. Appears on printed documents, email headers, '
        'and the login page. Every WC3 installation has exactly one.'
    ),
    'wc:collaborate': (
        'Configuration for WebClerk HQ collaboration — sync settings, '
        'data sharing rules, and connection parameters for the WC_HQ '
        'data service. Controls what data flows between this installation '
        'and the central WebClerk ecosystem.'
    ),
    'wc:wchq_connection': (
        'Connection credentials and endpoint for the WebClerk HQ service. '
        'Used by the sync engine to exchange data with the central '
        'WebClerk ecosystem — item libraries, pricing updates, and '
        'cross-company commerce.'
    ),
    'wc:exchange_rates': (
        'Currency exchange rate configuration — base currency, update '
        'frequency, and rate source. Used by multi-currency transactions '
        'to convert between currencies at the correct rate.'
    ),
    'wc:payment_gateway': (
        'Payment gateway configuration — processor credentials, supported '
        'methods, and transaction settings. Controls how online payments '
        'are processed and reconciled.'
    ),
    'wc:qa_questions': (
        'Quality assurance question templates for {model} records. '
        'Used by the QA module to prompt users for structured feedback '
        'and compliance checks. Answers are stored on the record.'
    ),
    'wc:qa_counters': (
        'Tracks QA completion counts and scoring across the installation. '
        'Used by Alice to identify areas where QA attention is needed '
        'and to measure improvement over time.'
    ),
    'wc:dd_card': (
        'Dashboard card configuration — defines the summary cards shown '
        'on the main dashboard. Each card shows a count, trend, or KPI '
        'for a specific model or metric.'
    ),
    'wc:react_settings': (
        'React frontend configuration — UI feature flags, component settings, '
        'and display parameters passed to the frontend at load time.'
    ),
    'wc:list_column_config': (
        'Column configuration for the {model} list view — which columns '
        'are visible, their order, and widths. This is the legacy format; '
        'new installations use workbench_fields instead.'
    ),
    'wc:serial_settings': (
        'Serial number tracking configuration for {model}. Controls how '
        'serial numbers are assigned, validated, and tracked through the '
        'inventory lifecycle — receipt, transfer, sale, return, and warranty.'
    ),
    'wc:print_defaults': (
        'Default print settings — paper size, margins, orientation, and '
        'output format. Applied to all print jobs unless overridden by '
        'a specific print layout.'
    ),
}

# Fallback for purposes not in the dictionary
DEFAULT_EXPLANATION = (
    'System configuration record (purpose: {purpose}). '
    'Controls operational behavior for {model} within this WC3 installation.'
)


# ═══════════════════════════════════════════════════════════════════════
# Report category explanations
# ═══════════════════════════════════════════════════════════════════════

REPORT_CATEGORY_EXPLANATIONS = {
    'customer_facing': (
        'Customer-facing document template. Generates output that customers '
        'see — invoices, statements, order confirmations, proposals. '
        'The template defines layout, fields, and formatting. Data is '
        'populated from the transaction record at print/email time.'
    ),
    'operations': (
        'Internal operations report. Used by staff for day-to-day work — '
        'pick lists, packing slips, delivery manifests, cycle count sheets. '
        'Designed for efficiency: large fonts, barcodes, minimal decoration.'
    ),
    'report': (
        'Analytical report template. Summarizes data across records — '
        'sales by period, aged receivables, inventory valuation, commission '
        'summaries. Can be run on-demand or scheduled.'
    ),
    'form': (
        'Printable form template. Structured input documents — purchase '
        'orders, work orders, receiving forms, inspection checklists. '
        'Includes data fields plus blank areas for handwritten notes.'
    ),
    'vendor_facing': (
        'Vendor-facing document template. Purchase orders, RFQs, and '
        'receiving documents sent to suppliers. Includes your company '
        'information, vendor terms, and line item details.'
    ),
    'letter': (
        'Letter/correspondence template. Structured letters with {{tokens}} '
        'for personalization — collection notices, welcome letters, '
        'credit applications. Users paste tokens into their email/word '
        'processor; WC3 provides the data, not the formatting.'
    ),
    'statement': (
        'Account statement template. Shows a customer\'s transaction history '
        'and balance — open invoices, payments received, aging buckets. '
        'Typically sent monthly or on request.'
    ),
    'function': (
        'Functional report — executes a process rather than just displaying '
        'data. Examples: journal posting, inventory adjustment, batch '
        'invoice generation. The report config defines both the output '
        'format and the processing rules.'
    ),
    'label': (
        'Label/tag template for printing. Item labels, shelf tags, barcode '
        'labels, shipping labels. Designed for label printers or cut-sheet '
        'label stock. Size and layout match specific label formats.'
    ),
}


def build_explanation(purpose, parent_model, name, ida):
    """Build an explanation string for a Setting record."""
    model_name = parent_model or 'system'
    template = PURPOSE_EXPLANATIONS.get(purpose, DEFAULT_EXPLANATION)
    return template.format(
        model=model_name,
        purpose=purpose,
    )


def build_report_explanation(report):
    """Build an explanation string for a Report record."""
    category = report.category or 'report'
    base = REPORT_CATEGORY_EXPLANATIONS.get(category, (
        f'Report template (category: {category}). '
        'Generates formatted output from WC3 data.'
    ))
    # Add the specific report's name and description
    parts = [base]
    if report.description:
        parts.append(f'This report: {report.description}')
    return ' '.join(parts)


class Command(BaseCommand):
    help = 'Populate metadata.explanation on all database supporting records'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing explanations')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be written without saving')

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        updated = 0
        skipped = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            'seed_dbsr_explanations — populating metadata.explanation'))

        # ── Settings ──
        for setting in Setting.objects.all().order_by('purpose', 'parent_model'):
            metadata = setting.metadata or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata.replace("'", '"'))
                except (json.JSONDecodeError, ValueError):
                    metadata = {}

            existing = metadata.get('explanation', '')
            if existing and not force:
                skipped += 1
                continue

            explanation = build_explanation(
                setting.purpose, setting.parent_model,
                setting.name, setting.ida
            )

            if dry_run:
                self.stdout.write(f'  [DRY] Setting {setting.ida}: {explanation[:80]}...')
            else:
                metadata['explanation'] = explanation
                Setting.objects.filter(pk=setting.pk).update(metadata=metadata)
            updated += 1

        # ── Reports ──
        for report in Report.objects.all().order_by('category', 'name'):
            metadata = report.metadata or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata.replace("'", '"'))
                except (json.JSONDecodeError, ValueError):
                    metadata = {}

            existing = metadata.get('explanation', '')
            if existing and not force:
                skipped += 1
                continue

            explanation = build_report_explanation(report)

            if dry_run:
                self.stdout.write(f'  [DRY] Report {report.name}: {explanation[:80]}...')
            else:
                metadata['explanation'] = explanation
                Report.objects.filter(pk=report.pk).update(metadata=metadata)
            updated += 1

        action = 'Would update' if dry_run else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action} {updated} records, skipped {skipped} (already had explanations)'))
