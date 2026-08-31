# Report System Overview -- Editors, Scripts, Output, Forms

**Established:** 2026-08-13
**Flowchart:** `readmes/charts/flowcharts/wc3-report-system.dot` (.svg and .pdf rendered)

---

## The Report Record

Every report, form, letter, export, and function in WC3 is a **Report record**. One model, many purposes.

| Field | What it controls |
|-------|-----------------|
| `editor_type` | Which editor renders the content field (plain, markdown, html, svg) |
| `content` | Document body template -- interpreted by editor_type |
| `script_before` | Runs once before processing |
| `script_during` | Runs once per record |
| `script_after` | Runs once after processing |
| `config` | Extended JSON: form layout, template, parameters, SVG template |
| `output_type` | What it produces: print, email, screen, export, json, label, merge, api |
| `category` | Menu grouping: customer_facing, vendor_facing, operations, statement, report, form, function |
| `purpose` | Lifecycle stage: mvp, svg-form-staged, svg-form, custom-page, form-detail, function |
| `is_active` | Visible to users when True |
| `dt_approved` | Timestamp when approved for production use (0 = not yet) |

---

## Editor Types

**Migration:** core 0039

### plain
- **Editor:** Textarea (12 rows)
- **Rendering:** `<pre>` with preserved whitespace
- **Use case:** Scripts, raw text, simple notes
- **Token support:** No

### markdown
- **Editor:** @uiw/react-md-editor with edit/preview split
- **Rendering:** Python `markdown` library -> HTML -> WeasyPrint -> PDF
- **Use case:** Letters, internal reports, documentation, email templates
- **Token support:** Yes -- `{{field.path}}`, `{{field.path|currency}}`, `{{#each lines}}...{{/each}}`
- **Component:** `src/components/common/MarkdownEditor.tsx`

### svg
- **Editor:** PrintLayoutDesigner (panel-based visual editor)
- **Rendering:** SVG populate (resolve IDs -> data, clone line panels)
- **Use case:** Designed print forms -- invoices, POs, proposals
- **SVG workflow:** Select fields -> Export SVG -> Design externally -> Import back -> Populate with data
- **Component:** `src/components/print/PrintLayoutDesigner.tsx`, `src/components/print/SvgFormGenerator.ts`

**Removed:** `html` (TinyMCE). WC3 is not an email or letter formatting tool. Users have Gmail, Word, Pages -- WC3 provides `{{token}}` fields and data export.

### Relationship to Script Fields

The `content` field is the **document template** -- what the report looks like.
The `script_before`, `script_during`, `script_after` fields are **computation logic** -- what the report calculates.

A report can have both: scripts compute the data, content provides the layout.
A report can have just content (static letter) or just scripts (data export) or neither (built-in template like Invoice).

### Frontend Architecture

**EditorField Component:** `react-joint/src/components/fields/EditorField.tsx`

A reusable field widget that switches editor based on its `editorType` prop:

- Registered as `editor` in the widget registry (`components/fields/index.tsx`)
- Added to `AdminFieldKind` type (`apps/utils/3column/types.ts`)
- All three sub-editors (plain, markdown, TinyMCE) are **lazy-loaded** -- no bundle cost until used

| Context | How it works |
|---------|-------------|
| **ReportDetail.tsx** | Editor Type dropdown + EditorField reads `watch("editor_type")` to switch live |
| **ReportDisplay.tsx** | Detects `content` field, renders EditorField with record's `editor_type` |
| **DataBrowser (3-column)** | `RecordDetailColumn.tsx` handles `kind: "editor"` -- reads sibling `editor_type` from `formValues` |

**npm packages:** `@uiw/react-md-editor` -- Markdown editor with preview.

### Backend Rendering

`apps/core/services/report_renderer.py` -- `_render_content_report()`

| editor_type | Conversion | Result |
|-------------|-----------|--------|
| `plain` | Wrapped in `<pre>` | Whitespace-preserved plain text |
| `markdown` | `markdown.markdown()` with tables + fenced_code extensions | Styled HTML |

Both are wrapped in the standard page template (`_BASE_CSS` + company header). For customer-facing output, users copy resolved tokens into their own tools.

**Python dependency:** `markdown` (pip) -- installed in WC3 venv. Graceful fallback to `<pre>` if not available.

### Field Behaviors (seed_field_access.py)

| Field | Behavior type | Widget |
|-------|--------------|--------|
| `editor_type` | `select` (inline options) | Dropdown: Plain text / Markdown / HTML |
| `content` | `editor` | EditorField -- switches on sibling editor_type |

Run `python manage.py seed_field_access` after migration to populate.

---

## The Script Pipeline

Scripts and content are **parallel layers**. Scripts compute the data. Content provides the layout.

### The Three Phases

| Phase | Field | Runs | Purpose |
|-------|-------|------|---------|
| **Before** | `script_before` | Once, before the first record | Initialize accumulators, open connections, establish working set |
| **During** | `script_during` | Once per record in the set | Business logic -- calculate, accumulate, format, transform |
| **After** | `script_after` | Once, after the last record | Write results, format output, send notifications, close streams |

```
+-----------------------------------------------------+
|  script_before --- runs ONCE                         |
|  * initialize accumulators                           |
|  * open connections / streams                        |
|  * establish working set                             |
+------------------------------------------------------+
|  script_during --- runs per RECORD                   |
|  * calculate / accumulate                            |
|  * format / transform                                |
|  * UNLOAD record when done                           |
+------------------------------------------------------+
|  script_after --- runs ONCE                          |
|  * write totals / summary                            |
|  * format final output                               |
|  * send notifications                                |
|  * close streams                                     |
+------------------------------------------------------+
```

### Two Critical Rules

#### 1. Unload Records After Processing

Each record must be **unloaded** after `script_during` completes. The pattern:

```
load record -> process -> accumulate results -> unload record -> next
```

This applies to printing 10 invoices or processing 10,000 inventory adjustments. The discipline is the same.

#### 2. Read-Only Access When Records Are Not Changed

If `script_during` only reads data, the record must be accessed **read_only**. This prevents accidental writes, allows concurrent execution, and makes intent explicit.

### How Users Configure Report Scripts

1. **Alice Dashboard -> Reports tab** -- browse available reports per model
2. **databrowser detail view** -- edit script fields directly
3. **Report menu on any model page** -- run against current selection

#### Built-in vs. User Reports

Built-in reports can **lock** `script_before` and `script_after`. Users customize only `script_during`.

| Field | Built-in (locked) | User report |
|-------|--------------------|-------------|
| `script_before` | Protected -- setup logic | Fully editable |
| `script_during` | **Open to user** | Fully editable |
| `script_after` | Protected -- output logic | Fully editable |

### Examples

**Tally Report** (read-only):
```
script_before:  total = 0; count = 0; open output
script_during:  read_only; total += record.amount; count += 1; unload record
script_after:   write "Total: {total}, Count: {count}, Avg: {total/count}"; close output
```

**Batch Status Update** (read-write):
```
script_before:  updated = 0; errors = []
script_during:  record.status = 'archived'; save; updated += 1; unload record
script_after:   write "Updated {updated} records, {len(errors)} errors"; notify admin
```

**Statement of Account** (read-only, grouped):
```
script_before:  current_customer = None; page_break = False; open PDF
script_during:  read_only; if customer changed: write subtotal, page break;
                accumulate line; unload record
script_after:   write final subtotal; close PDF; return document
```

---

## Output Types

| output_type | What it produces | Common editor_types |
|-------------|-----------------|-------------------|
| `print` | PDF download or browser view | markdown, html, svg, (config.form JSON) |
| `email` | HTML body or PDF attachment -> Action record | markdown, html |
| `screen` | Interactive page (DynamicDetail form or custom .tsx) | -- (rendered by React) |
| `export` | CSV / Excel / JSON download | plain (scripts produce the data) |
| `json` | Function execution (split order, calculate commission) | -- (scripts only) |
| `label` | Avery / thermal / barcode / QR | html, svg |
| `merge` | Template + data mail merge | markdown, html |
| `api` | JSON payload to Connection endpoint | -- (scripts + config.endpoint_url) |

---

## Email & Letter Approach -- We Are Not a Formatting Tool

Users have Gmail, Word, Pages, Outlook. WC3 provides **data**, not formatting.

**The {{token}} clipboard** is the key feature:
1. User opens a report with `{{tokens}}` in the markdown editor
2. Preview resolves tokens against real data
3. User copies resolved text and pastes into Gmail, Word, Pages, or any tool
4. WC3 also exports data as CSV/JSON for mail merge

| Use case | How |
|----------|-----|
| Overdue notice | Copy resolved `{{tokens}}` -> paste into Gmail compose |
| Mail merge (100 customers) | Export CSV with resolved fields -> Gmail/Word merge |
| Thank you letter | Template path -> AppleScript opens Pages with data filled |
| Customer statement | SVG form (print path) or export PDF |
| Mailing labels | Export CSV -> Avery template in Word/Pages |

**Not installed (by design):** TinyMCE.

---

## SVG Form Workflow

1. **User selects fields** inside WebClerk -> PrintLayoutDesigner
2. **Export SVG** -> clean SVG with IDs on every element
3. **Design externally** -> Affinity Designer, Figma, Illustrator
4. **Import SVG back** -> designed template with IDs intact
5. **Populate with data** -> SvgFormGenerator resolves IDs -> record values

**Seeded SVG Form Reports:** Invoice, Order, Proposal, Purchase Order, Payment Receipt -- all staged. Set `is_active=True`, `purpose=svg-form`, `dt_approved=now` when print-ready.

---

## Custom .tsx Pages

| Path | Purpose |
|------|---------|
| `src/custom/pages/` | Custom .tsx page components |
| `src/custom/components/` | Custom reusable components |
| `src/custom/index.ts` | Registry -- one lazy import per page |
| `/custom/:page` | Route -- live at this URL |

**Registration:** Report record with `output_type=screen`, `purpose=custom-page`, `config.component=PageName`.

---

## Content Priority

When `render_report()` is called:

1. **Report.content** (non-empty) -> render using editor_type
2. **config.form** (PrintLayout JSON) -> UniversalPrint / SVG populate
3. **Built-in template** (template_key) -> Invoice, Pick List, etc.
4. **Generic fallback** -> auto-generated table from model fields

---

## Report Lifecycle

| Stage | purpose | is_active | dt_approved |
|-------|---------|-----------|-------------|
| Draft | `svg-form-staged` or blank | `False` | `0` |
| Review | unchanged | `False` | `0` |
| Approved | `svg-form` or `mvp` or `custom-page` | `True` | timestamp |
| Retired | unchanged | `False` | preserved |

`times_used` and `dt_last_used` track adoption. Alice monitors usage patterns.

---

## Standard Report Library

### Big5 Transaction Reports

#### Orders (8 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Sales Order -- Standard | customer_facing | print | Line items, pricing, delivery terms, signature |
| Sales Order -- Summary | report | print | Management view -- count, value, status |
| Packing Slip | warehouse | print | Package contents, weights, labels |
| Pick List | warehouse | print | Warehouse picking with bin locations |
| Order Acknowledgment | customer_facing | email | Customer confirmation |
| Delivery Note | warehouse | print | Shipping document for carrier |
| Open Orders Report | report | print | All open orders by customer, age, value |
| Backorder Report | report | print | Items ordered but not fulfilled |

#### Proposals (5 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Proposal/Quote -- Standard | customer_facing | print | Accept/Use columns, validity, signature |
| Proposal -- Summary | report | print | Open proposals by value, expiry |
| Proposal as Proforma Invoice | customer_facing | print | International/prepay format |
| Quote Follow-up List | report | print | Aging quotes needing follow-up |
| Quote Conversion Report | report | print | Win/loss analysis |

#### Invoices (9 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Invoice -- Standard | customer_facing | print | Line items, tax, totals, payment terms |
| Invoice -- Service | customer_facing | print | Labor hours, rates, project reference |
| Invoice -- Shipping | customer_facing | print | With tracking, carrier info |
| Credit Memo | customer_facing | print | Return/adjustment credit |
| Statement of Account | customer_facing | print | Multi-invoice with aging |
| AR Aging Report | accounting | print | Receivables by age bucket |
| Sales by Customer | sales_analysis | print | Revenue by customer for period |
| Sales by Rep | sales_analysis | print | Revenue by rep for period |
| Tax Report | accounting | print | Tax collected by jurisdiction |

#### Purchases (7 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Purchase Order -- Standard | vendor_facing | print | Quantities, prices, delivery terms |
| Purchase Order -- Summary | report | print | Open POs by vendor, value |
| Receiving Report (GRN) | warehouse | print | Arrived vs ordered |
| PO vs Receipt Variance | report | print | Quantity/price variance |
| AP Aging Report | accounting | print | Payables by age bucket |
| Vendor Scorecard | report | print | Delivery, quality, price, lead time |
| RFQ (Request for Quote) | vendor_facing | print | Pre-PO supplier request |

#### Payments (6 reports)
| Report | Category | Output | Purpose |
|--------|----------|--------|---------|
| Payment Receipt | customer_facing | print | Proof of payment with applied invoices |
| Payment Summary | report | print | By period, method, status |
| Bank Reconciliation | accounting | print | Payment vs bank matching |
| Commission Report | report | print | Commissions by rep, line-item detail |
| Refund Report | report | print | Refunds by period, reason |
| Cash Flow Report | accounting | print | Cash in/out with forecast |

---

## Dashboard Specifications

Each dashboard is a JSON structure that can be rendered on-screen, sent as JSON via sync, or printed as a PDF summary.

### 7 Standard Dashboards

| # | Dashboard | Audience | Key KPIs |
|---|-----------|----------|----------|
| 1 | Sales | Sales manager | Revenue vs quota, pipeline value, conversion rate, win/loss, deal size, cycle length, at-risk deals, rep attainment |
| 2 | Accounting | Bookkeeper/controller | Cash balance + forecast, DSO, AR/AP aging, cash conversion cycle, collection rate, close status |
| 3 | Inventory Control | Warehouse manager | Inventory value, turnover, stockouts, fill rate, days on hand, reorder alerts, dead stock |
| 4 | Purchasing | Purchasing agent | Open PO value, PO cycle time, supplier on-time %, cost savings, compliance, price variance |
| 5 | Rep Management | Sales director | Quota attainment, revenue/pipeline per rep, win rate, activity compliance |
| 6 | Vendor Management | Distributor | On-time delivery %, quality rate, cost trend, rebates, vendor rating, revenue dependency |
| 7 | Admin | System admin | Active users, response time, DB size, backup status, API errors, failed logins, Alice tasks, sync lag |

---

## Print Template System

### 1. PrintDocumentLayout (.tsx)
React components at `src/apps/transactions/components/print/`. Developers customize by editing .tsx. Uses Tailwind CSS + `@media print` rules.

### 2. pdfme (JSON templates)
Template-based PDF generation at `src/services/pdfme/`. Users customize via WYSIWYG designer (no code).

---

## Alice's Role

Alice should:
1. **Know** the standard reports per model and suggest missing ones
2. **Generate** report records with correct model_name, category, output_type
3. **Help users** customize templates
4. **Track usage** and auto-promote popular reports to quick-access
5. **Send dashboards** as JSON via sync app to external systems
6. **Create** visit checklists from QA Document records

The report is the last mile of data. If the user can't print it, email it, or hand it to someone, the data has no value outside the system.

---

## File Map

| What | Where |
|------|-------|
| Report model | `apps/core/models.py` (Report class) |
| Report renderer | `apps/core/services/report_renderer.py` |
| MarkdownEditor | `React2025/src/components/common/MarkdownEditor.tsx` |
| PrintLayoutDesigner | `React2025/src/components/print/PrintLayoutDesigner.tsx` |
| SvgFormGenerator | `React2025/src/components/print/SvgFormGenerator.ts` |
| UniversalPrint | `React2025/src/components/print/UniversalPrint.ts` |
| Print CSS | `React2025/src/apps/transactions/components/print/print.css` |
| PrintLayout types | `React2025/src/components/print/printLayoutTypes.ts` |
| ReportsDialog | `React2025/src/components/common/ReportsDialog.tsx` |
| ReportDesigner (pdfme) | `React2025/src/pages/admin/ReportDesigner.tsx` |
| Custom page loader | `React2025/src/routes/CustomPageLoader.tsx` |
| Custom page registry | `React2025/src/custom/index.ts` |
| Flowchart | `readmes/charts/flowcharts/wc3-report-system.dot` |
| Alice report parade | `apps/core/services/parade_of_reports.py` |
