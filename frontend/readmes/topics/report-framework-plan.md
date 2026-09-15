# Report Framework Plan

## What wc2 Had

From code review of 00WebClerk19:

### Report Types (from wc2 Defined Reports dialog)
| Code | Type | Examples |
|------|------|---------|
| GTsR | Print reports | Order forms, pick lists, packing slips, BOL |
| EDIx | Scripts/exports | UPS posting, EDI, data clearing, imports |
| GTSR | Print variants | Single-loop barcodes, pack lists |

### Key wc2 Functions
- **ExecuteUserReport** — loads UserReport record by name, runs ScriptBegin (4D code stored as text)
- **AcceptPrint** — model-specific accept+print: acceptOrders, acceptInvoice, acceptPO, acceptPropsl
- **action_Reports** — opens 4D Quick Report editor on current selection
- **action_Labels** — label/barcode printing
- **action_PrintSelection** — print selected records
- **BOMReport** — bill of materials explosion
- **RptEmpCommis / RptRepCommis** — commission reports
- **ForecastTrendReport5Yr** — 5-year trend analysis
- **GL_RptRay** — GL report builder
- **Bonus_Report_*** — bonus calculation reports (credits, multipliers, sales, samples)
- **CallReport** — sales call reports

### How wc2 Stored Reports
- **UserReport table** — name, script text, table association, creator (GTsR/EDIx)
- **4D Quick Reports** — visual report builder stored as blobs
- **Hardcoded methods** — model-specific report methods (BOMReport, etc.)

## What wc3 Already Has

- **Report model** — `apps/core/models/report.py` with output_type, category, template
- **TransactionPrint.tsx** — standalone HTML print from layout JSON + data
- **Report dropdown** — in TransactionToolbar (Print, Email, Labels, Clone)
- **PDF generation** — pdfme library available in React2025

## The Plan

### Phase 1: Report Records (Now)

Each report is a **Report model record** — user-facing, not a Setting:

```
Settings = system defaults, wc3 behaviors (how the system works)
Reports  = user behaviors (what users produce)
```

```json
Report record:
{
  "name": "Standard Order",
  "model_name": "order",
  "output_type": "print",       // print | email | label | export | script
  "category": "report",         // report | statement | list | summary | letter | label | export
  "role_required": "",           // blank = all users
  "sort_order": 1,
  "config": {
    "template": "standard",      // maps to a print template
    "paper": "letter",
    "orientation": "portrait",
    "show_prices": true,
    "show_costs": false,
    "conditions_on_print": true,
    "notes_on_print": true,
  }
}
```

The Report dropdown queries: `Report.objects.filter(model_name=modelName, is_active=True)`

### Phase 2: Template Library

Templates are HTML builders — same pattern as current TransactionPrint but configurable:

| Template | What it renders |
|----------|----------------|
| `standard` | Full document: header, lines, totals, notes, conditions |
| `picklist` | Warehouse version: item, location, bin, qty, check column |
| `packslip` | No prices: item, qty shipped, description |
| `bol` | Bill of lading: carrier, weight, piece count |
| `statement` | Customer statement: invoices, payments, aging |
| `label` | Item/shipping labels with barcodes |
| `summary` | Totals only, no line detail |

Each template reads from the same data + layout JSON. The `config` on the report Setting controls what to show/hide.

### Phase 3: Report Runner

```
User clicks Report ▾
  → Dropdown queries report Settings for this model
  → Shows: Standard Order, Pick List, Packing Slip, BOL, ...
  → User clicks one
  → Report runner:
      1. Reads the report Setting config
      2. Selects the template
      3. Builds HTML from data + layout + config
      4. Opens print window (or sends email, or generates PDF, or exports CSV)
```

### Phase 4: Custom Reports

Users create their own reports via DataBrowser on the Setting model:
- Pick a model (order, invoice, etc.)
- Choose a template
- Configure: show/hide prices, costs, notes, conditions
- Name it
- It appears in the Report dropdown

Alice coaches: "You keep printing orders without prices for your warehouse team.
Want me to create a Pick List report for you?"

### Phase 5: Salvageable from wc2

| wc2 Function | wc3 Equivalent |
|---|---|
| ExecuteUserReport + ScriptBegin | Report Setting + template selection |
| 4D Quick Reports | DataBrowser export (CSV/PDF) |
| AcceptPrint flow | TransactionToolbar → Report dropdown |
| BOMReport | Template: bom_explosion |
| Commission reports | Template: commission_summary |
| GL reports | Template: gl_journal |
| Forecast/trend | Dashboard widget (not a print report) |
| Labels/barcodes | Template: label (pdfme for layout) |
| EDI export | Template: edi_export (JSON/CSV output) |
| Statement | Template: statement (aging buckets) |

### Storage

```
Setting records (purpose='report')
  ├── per model (parent_model='order', 'invoice', etc.)
  ├── per company (seeded defaults + user-created)
  └── synced via Connection/Bundle like all Settings

Templates
  ├── Built-in: standard, picklist, packslip, bol, statement, label, summary
  ├── Stored as: React components OR HTML builder functions
  └── NOT stored in database — they're code, versioned with the app

Report output
  ├── print → openPrintWindow (existing)
  ├── email → server-side: render HTML, send via SMTP
  ├── pdf → pdfme or server-side wkhtmltopdf
  ├── csv → client-side export (existing in DataBrowser)
  └── label → pdfme with label template
```

### The Principle

Reports are data-driven like everything else. The Setting defines WHAT to show.
The template defines HOW to show it. The layout JSON defines WHERE the fields are.
Same architecture as the working form — one renderer, many configurations.
