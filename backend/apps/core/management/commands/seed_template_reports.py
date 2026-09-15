"""Seed Report records for markdown template documents.

These three reports use output_type='merge' — the MarkdownEditor renders them
using {{field.path}} and {{#each lines}} token syntax. Config carries:
  - action: 'markdown_template'   (renderer key)
  - template: <markdown string>   (the template content)

Token syntax reference: readmes/topics/ai/markdown-templates.md
  {{field.path}}             — simple field
  {{field.path|format}}      — with format hint (currency, date, number, percent)
  {{#each lines}} ... {{/each}}  — iterate order/invoice lines

quantity.active  = the verb quantity for the document type (shipped on invoice, etc.)
quantity.remaining = not yet transferred downstream (on order = not yet shipped)

Usage:
    ./manage.py seed_template_reports
    ./manage.py seed_template_reports --force   # overwrite existing templates
"""
from django.core.management.base import BaseCommand
from apps.core.models.report import Report


# ── Pick List ──────────────────────────────────────────────────────────────────
# Sorted by warehouse / bin so the picker walks the warehouse once.
# quantity.remaining = ordered but not yet shipped — the correct "to pick" qty.

PICK_LIST_TEMPLATE = """\
# Pick List — Order {{ida}}

**Customer:** {{name}}  **Date:** {{dt_created|date}}  **Priority:** {{priority}}  **Ship Via:** {{ship_via}}

---

| ☐ | Item | Description | Qty to Pick | Warehouse | Bin |
|---|------|-------------|-------------|-----------|-----|
{{#each lines}}
| ☐ | {{item.ida_item}} | {{item.description}} | {{quantity.remaining|number}} | {{physical.warehouse}} | {{physical.bin}} |
{{/each}}

---

**Picker:** ________________________  **Date Picked:** ________________________

**Notes / Shorts:**




---
*Print date: {{dt_created|date}}  ·  Order {{ida}}  ·  Warehouse copy — do not ship*
"""

# ── Packing Slip ───────────────────────────────────────────────────────────────
# Attached to the shipment — no prices. quantity.active on an invoice = qty shipped.

PACKING_SLIP_TEMPLATE = """\
# Packing Slip

**Ship To:**

{{config.ship_to.company}}
{{config.ship_to.attention}}
{{config.ship_to.address1}}
{{config.ship_to.city_state_zip}}

---

| Field | Value |
|-------|-------|
| **Order #** | {{ida}} |
| **Ship Date** | {{dt_created|date}} |
| **Ship Via** | {{ship_via}} |
| **Tracking #** |  |

---

| Item | Description | Qty Shipped | UOM | Weight |
|------|-------------|-------------|-----|--------|
{{#each lines}}
| {{item.ida_item}} | {{item.description}} | {{quantity.active|number}} | {{item.unit_measure}} | {{physical.weight.value|number}} |
{{/each}}

---

**Total Weight:** ____________  **# of Boxes:** ____________

*Thank you for your order. Questions? Contact us at {{config.communication.email}}*

---
*Packing slip — no prices — {{ida}} — customer copy*
"""

# ── Customer Statement ─────────────────────────────────────────────────────────
# Contact-level report. Lines = open invoices from the AR aging service.
# The #each block iterates the invoices array provided by the data source.

CUSTOMER_STATEMENT_TEMPLATE = """\
# Account Statement

**{{name}}**
{{config.addresses.billing}}

**Statement Date:** {{dt_created|date}}  **Account #:** {{ida}}  **Phone:** {{config.communication.phone}}

---

## Open Invoices

| Date | Invoice # | Due Date | Amount | Balance |
|------|-----------|----------|--------|---------|
{{#each invoices}}
| {{dt_created|date}} | {{ida}} | {{dt_due|date}} | {{totals.total|currency}} | {{totals.balance|currency}} |
{{/each}}

---

| | |
|-|-|
| **Current (0–30 days)** | {{aging.current|currency}} |
| **31–60 days** | {{aging.past_31_60|currency}} |
| **61–90 days** | {{aging.past_61_90|currency}} |
| **Over 90 days** | {{aging.past_90|currency}} |
| **Total Balance Due** | **{{aging.balance_due|currency}}** |

---

*Please remit payment to the address above. Questions? Call {{config.communication.phone}} or email {{config.communication.email}}*

---
*Statement generated {{dt_created|date}}  ·  Account {{ida}}  ·  Customer copy*
"""


# ── Report definitions ─────────────────────────────────────────────────────────

TEMPLATE_REPORTS = [
    {
        'ida': 'wchq-rpt-pick-list-md',
        'name': 'Pick List',
        'description': 'Warehouse pick list sorted by bin — checkboxes, qty to pick, location',
        'model_name': 'order',
        'output_type': 'merge',
        'category': 'list',
        'purpose': 'operational',
        'sort_order': 5,
        'config': {
            'action': 'markdown_template',
            'template': PICK_LIST_TEMPLATE,
            'sort_lines_by': ['physical.warehouse', 'physical.bin'],
        },
    },
    {
        'ida': 'wchq-rpt-packing-slip-md',
        'name': 'Packing Slip',
        'description': 'Packing slip for shipment — ship-to address, line items, qty shipped, weight. No prices.',
        'model_name': 'order',
        'output_type': 'merge',
        'category': 'report',
        'purpose': 'operational',
        'sort_order': 6,
        'config': {
            'action': 'markdown_template',
            'template': PACKING_SLIP_TEMPLATE,
            'hide_prices': True,
        },
    },
    {
        'ida': 'wchq-rpt-customer-statement-md',
        'name': 'Customer Statement',
        'description': 'Open invoice statement with aging buckets — current / 30 / 60 / 90+ days',
        'model_name': 'contact',
        'output_type': 'merge',
        'category': 'statement',
        'purpose': 'financial',
        'sort_order': 2,
        'config': {
            'action': 'markdown_template',
            'template': CUSTOMER_STATEMENT_TEMPLATE,
            'data_source': 'customer_statement',
        },
    },
]


class Command(BaseCommand):
    help = 'Seed markdown template Report records (pick list, packing slip, customer statement)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite the template field in existing records',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        created = updated = skipped = 0

        for spec in TEMPLATE_REPORTS:
            ida = spec['ida']
            defaults = {
                'name': spec['name'],
                'description': spec.get('description', ''),
                'model_name': spec['model_name'],
                'output_type': spec['output_type'],
                'category': spec['category'],
                'purpose': spec.get('purpose', ''),
                'sort_order': spec.get('sort_order', 0),
                'is_active': True,
            }

            report, was_created = Report.objects.update_or_create(
                ida=ida,
                defaults=defaults,
            )

            if was_created:
                report.config = spec['config']
                report.save(update_fields=['config'])
                created += 1
                self.stdout.write(f'  Created: {spec["name"]} ({ida})')
            else:
                existing_template = (report.config or {}).get('template', '')
                if force or not existing_template:
                    report.config = spec['config']
                    report.save(update_fields=['config'])
                    updated += 1
                    self.stdout.write(f'  Updated: {spec["name"]} ({ida})')
                else:
                    skipped += 1
                    self.stdout.write(
                        f'  Skipped template: {spec["name"]} ({ida}) — '
                        f'has existing template; use --force to overwrite'
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Template reports: {created} created, {updated} updated, {skipped} skipped'
        ))
