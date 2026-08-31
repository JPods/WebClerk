# Form Parade — Print Form Review Tool

**Route:** `/form-parade`
**Video:** https://vimeo.com/1218709661
**Built:** 2026-08-16

## What It Does

The Form Parade lets users review all commerce print forms in one place before they have real transaction data. Users see every form rendered with realistic sample data, record feedback (Keep / Modify / Don't Need), and print preview — all without leaving the page.

This is an onboarding tool. New users see what their documents will look like on day one, not after they've entered 50 orders and sent the first invoice to a customer.

## How It Works

**Left panel** — 14 reports grouped by business flow:
- **Selling:** Invoice, Credit Memo, Order Confirmation, Pick Ticket, Packing Slip, Proposal, Work Order
- **Getting Paid:** Statement, Aging Report, Payment Receipt
- **Buying:** Purchase Order, Receiving Report, Requisition
- **Catalog & Contacts:** Thank You Letter

Green dot = sample data available. Click to preview.

**Top toolbar** — appears when a report is selected:
- Report name
- Keep / Modify / Don't Need feedback buttons
- Notes field
- Print Preview (triggers browser print dialog on the iframe)
- New Tab (opens the form in a separate window)

**Right panel** — iframe rendering the form with sample data and the company logo from `Company Profile` Setting (`config.logos.primary`).

## Architecture

### React (Frontend)

| File | Purpose |
|------|---------|
| `React2025/src/pages/tools/FormParade.tsx` | Page component |
| `React2025/src/routes/Routes.ts` | Route constant (`/form-parade`) |
| `React2025/src/routes/protectedRoutesConfig.tsx` | Route registration |

### Django (Backend)

| File | Purpose |
|------|---------|
| `apps/core/views/parade_preview_view.py` | `ParadePreviewView` (GET — renders HTML), `ParadeManifestView` (GET — returns grouped report list), `ParadeFeedbackView` (POST — saves feedback) |
| `apps/core/services/parade_of_reports.py` | `build_parade_manifest()` — groups reports by business flow, checks sample data availability. `save_parade_feedback()` — writes feedback to Report record config. |
| `apps/core/sample_data/*.json` | Polished sample data files per model |
| `scripts/seed_print_layouts.py` | Form layout definitions (sections, fields, columns) for all 14 reports |

### API Endpoints

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/wcapi/parade-manifest/` | Returns grouped report list with sample data status |
| GET | `/wcapi/parade-preview/?report_id=N` | Renders a single report as standalone HTML with sample data |
| POST | `/wcapi/parade-feedback/` | Saves Keep/Modify/Don't Need + notes to Report record |

### Sample Data Files

| File | Model | Description |
|------|-------|-------------|
| `invoice.json` | invoice | Wholesale hardware tools order — 5 lines, $4,263.35 |
| `order.json` | order | Contractor building materials — 6 lines, $9,395.97 |
| `payment.json` | payment | Check payment applied to two invoices — $7,841.20 |
| `proposal.json` | proposal | Service proposal with signature blocks |
| `purchase.json` | purchase | Vendor purchase order |
| `statement.json` | customer | Customer statement with aging |
| `contact.json` | contact | Customer/vendor profile |
| `item.json` | item | Product detail |
| `requisition.json` | requisition | Internal maintenance supplies — 8 lines, $2,847.60 |
| `workorder.json` | workorder | HVAC compressor replacement — labor + materials, $4,925.00 |
| `aging.json` | customer | AR aging — 10 customers across 3 reps |
| `_index.json` | — | Index of all sample data files |

### Form Layout Sections

The parade preview renderer handles these section types from `Report.config.form`:

| Section Type | What It Renders |
|-------------|----------------|
| `company_header` | Title + company logo (from Company Profile Setting) |
| `address_blocks` | Multi-column address panels (Bill To, Ship To, etc.) |
| `meta_row` | Horizontal key-value row (date, status, terms) |
| `detail_fields` | Vertical key-value list (description, notes) |
| `line_items` | Item table with column headers (qty, price, extended) |
| `data_table` | Generic data table with group_by, subtotals, grand totals |
| `comments` | Comment block with blue left border |
| `totals` | Right-aligned totals section |
| `conditions` | Terms and conditions text |
| `signature` | Signature blocks with preamble |
| `footer` | Page footer with key fields |

### Company Logo

The logo on each form is pulled from:
```
Company Profile Setting → config.logos.primary
```
Currently: `media/company/logos/jpods-logo-primary.png`

Served via Django media URL, proxied through Vite in development (`/media` proxy in `vite.config.ts`).

### Feedback Storage

Feedback is saved to the Report record:
```json
{
  "config": {
    "parade_feedback": {
      "decision": "keep",
      "notes": "Looks good, maybe add PO number field",
      "user_id": 1,
      "dt_feedback": "2026-08-16T20:15:00+00:00"
    }
  }
}
```

Alice reads these decisions to know which reports the business actually uses.

## Alice Integration

The parade was originally designed for Alice to drive via Chrome DevTools MCP during onboarding. The React page makes it user-facing. Both paths produce the same feedback data.

Alice uses parade feedback to:
- Deactivate reports marked "Don't Need"
- Flag "Modify" reports for follow-up
- Track which reports are actually used (via `metadata.flow.use_count`)
- Coach users who have reports they've never generated

## Adding a New Report

1. Create the form layout in `scripts/seed_print_layouts.py`
2. Run `python manage.py seed_print_layouts` to create the Report record
3. Create a sample data JSON file in `apps/core/sample_data/`
4. Add an entry to `_index.json`
5. If the model doesn't fit existing parade groups, add it to `PARADE_GROUPS` in `parade_of_reports.py`

The form will appear in the parade automatically.
