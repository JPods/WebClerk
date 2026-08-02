# WC3 Print Template System — pdfme

## Overview

WC3 uses [pdfme](https://pdfme.com/) v6.1.11 for client-side PDF generation. Templates are
JSON documents stored in the `core.Report` model and edited via the visual PDF Designer
at `/pdf-designer`. No server-side dependencies (no WeasyPrint, no wkhtmltopdf).

## Architecture

```
Report model (config.pdfme_template)    ← Template storage (JSON)
    ↓
PDF Designer (/pdf-designer)            ← Visual WYSIWYG editor
    ↓
@pdfme/generator                        ← Client-side PDF generation
    ↓
Download / Print / Email attachment     ← Output
```

### Key Files

| File | What it does |
|------|-------------|
| `React2025/src/services/pdfme/templateService.ts` | Load/save templates from Report model |
| `React2025/src/services/pdfme/generateCommercePdf.ts` | Programmatic PDF generation from transaction data |
| `React2025/src/services/pdfme/starter-templates/*.json` | Bundled starter templates |
| `React2025/src/pages/tools/PdfDesigner.tsx` | Visual template editor page |
| `React2025/src/hooks/useExportPdf.ts` | React hooks for PDF export |
| `React2025/src/apps/transactions/components/PrintPreviewModal.tsx` | Print preview with Download PDF button |
| `React2025/src/apps/transactions/components/print/` | HTML print components (browser print fallback) |

### npm Packages

- `@pdfme/common` v6.1.11 — Type definitions
- `@pdfme/generator` v6.1.11 — PDF byte generation
- `@pdfme/schemas` v6.1.11 — Schema plugins (text, table, line, rectangle, svg, image, multiVariableText)
- `@pdfme/ui` v6.1.11 — Designer UI component

## Template Structure

A pdfme template is a JSON object:

```json
{
  "basePdf": {
    "width": 215.9,          // US Letter width in mm
    "height": 279.4,         // US Letter height in mm
    "padding": [12.7, 12.7, 12.7, 12.7],
    "staticSchema": [...]    // Footer elements on every page
  },
  "schemas": [
    [                         // Page 1 schemas
      {
        "name": "companyName",
        "type": "text",
        "position": { "x": 20, "y": 20 },
        "width": 80,
        "height": 12,
        "fontSize": 18,
        "content": "Default Value"
      },
      {
        "name": "lineItems",
        "type": "table",       // Auto-expanding table
        "head": ["Item #", "Description", "Qty", "Unit Price", "Extended"],
        "content": "[]"
      }
    ]
  ]
}
```

### Schema Types Available

| Type | Use For |
|------|---------|
| `text` | Labels, values, addresses, comments |
| `table` | Line items (auto-expands, handles pagination) |
| `multiVariableText` | Compound fields like "Invoice #{InvoiceNo}\n{Date}" |
| `line` | Dividers, borders |
| `rectangle` | Boxes, backgrounds |
| `image` | Logos |
| `svg` | Vector icons |

### Table Schema (most important for commerce)

```json
{
  "type": "table",
  "head": ["Item #", "Description", "Qty", "Price", "Extended"],
  "headWidthPercentages": [12, 38, 10, 15, 15],
  "headStyles": { "fontSize": 11, "backgroundColor": "#f0f0f0" },
  "bodyStyles": { "fontSize": 10, "alternateBackgroundColor": "#fafafa" },
  "columnStyles": { "alignment": { "0": "left", "3": "right", "4": "right" } },
  "content": "[[\"ITEM1\",\"Widget\",\"5\",\"$10.00\",\"$50.00\"]]"
}
```

## Template Storage in WC3

Templates live in `core.Report` records:

| Report Field | Usage |
|-------------|-------|
| `name` | Template display name ("Invoice - Standard") |
| `model_name` | Document type ("invoice", "proposal", "order") |
| `output_type` | Always "print" |
| `category` | "document" |
| `config.pdfme_template` | The full pdfme template JSON |
| `config.field_map` | Maps WC3 field paths to template input names |

### Field Map Example

```json
{
  "companyName": "_company.name",
  "billTo": "_billTo",
  "invoiceInfo.InvoiceNo": "ida",
  "invoiceInfo.Date": "_dateFormatted",
  "lineItems": "_lines",
  "total": "totals.total",
  "balance": "totals.balance"
}
```

Fields starting with `_` are computed by the caller (formatted addresses, date strings, etc.).

## Available Templates

### Starter Templates (bundled)

| Template | Document Type | Heritage |
|----------|-------------|----------|
| Invoice - Standard | invoice | pdfme playground + WC2 field set |

### HTML Print Components (browser print fallback)

| Component | Heritage |
|-----------|---------|
| InvoicePrintDocument | Generic base layout |
| InvoiceStandardPrint | WC2 Invoice 1 — Ord/Ship/B-O columns, bordered rows |
| InvoiceShippingPrint | WC2 Invoice 2 — 4-column header, DownPayment, Contract Detail |
| InvoiceServicePrint | JIT/JPods — Job#, Instructions, Shipped/Ordered/Bk-Ord |
| ProposalPrintDocument | WC2 Proposal — Accept/Use columns, Base/Disc%/Unit, dual signature |
| StatementPrintDocument | WC2 Statement — aging summary, transaction detail |
| OrderPrintDocument | Standard order confirmation |
| PurchasePrintDocument | Purchase order |
| WorkorderPrintDocument | Work order |
| ReceiptPrintDocument | Receipt |
| AdjustmentPrintDocument | Credit memo / adjustment |
| RequisitionPrintDocument | Internal requisition |
| ProjectPrintDocument | Project summary |
| TaxReportPrintDocument | Tax report |

## PDF Designer

The visual designer at `/pdf-designer` allows:

1. **Create** — Start from a starter template or blank
2. **Edit** — Drag/drop fields, resize, style, add tables
3. **Save** — Saves to WC3 Report model (config.pdfme_template)
4. **Preview** — Generate PDF with sample data
5. **Export** — Download template JSON for version control

### Using the Designer

1. Navigate to `/pdf-designer`
2. Choose a starter template or existing saved template
3. Customize layout in the visual editor
4. Click "Save Template" to store in WC3
5. Template is now available in print preview dropdown

## Generation Flow

When a user clicks "Download PDF" on a transaction:

1. `PrintPreviewModal` passes `pdfData` to `downloadTransactionPdf()`
2. `generateCommercePdf.ts` builds a template + inputs programmatically
3. `@pdfme/generator.generate()` produces PDF bytes
4. Browser triggers file download

For template-based generation (future):

1. Load template JSON from Report model via `loadTemplateById()`
2. Build inputs from transaction data via `buildInputsFromTransaction()`
3. `@pdfme/generator.generate()` produces PDF bytes

## Open Source References

| Source | License | Coverage |
|--------|---------|----------|
| [pdfme playground](https://github.com/pdfme/pdfme) | MIT | Invoice, Quote templates + Designer |
| [ERPNext](https://github.com/frappe/erpnext) | GPL v3 | All commerce docs (Jinja/HTML) |
| [Odoo](https://github.com/odoo/odoo) | LGPL v3 | All commerce docs (QWeb/XML) |
| [Invoice Ninja](https://github.com/invoiceninja/invoiceninja) | ELv2 | Invoice, Quote, Credit Note, PO, Statement |
| [Anvil html-pdf-invoice](https://github.com/anvilco/html-pdf-invoice-template) | MIT | Clean invoice HTML + React-pdf |

## WC2 Form Heritage

292 forms in WC2 (275 active), organized by 4D table ID. Key patterns harvested:

- **Proposal**: Accept/Use columns, Base/Disc%/Unit pricing, dual signature block
- **Invoice Standard**: Ord/Ship/B-O columns, bordered empty rows, serial numbers
- **Invoice Shipping**: 4-column header (Bill/Ship/Contact/Customer), DownPayment, Contract Detail
- **Invoice Service**: Job#, Instructions, italic styling, simple "Total Due" for international
- **Statement**: Aging summary (Current/1-30/31-60/61+), response area, transaction detail

All WC2 field names mapped to WC3 JSONB field paths in the field_map system.
