# Report System Overview — Editors, Scripts, Output, Forms

**Established:** 2026-08-13
**Flowchart:** `readmes/charts/flowcharts/wc3-report-system.dot` (.svg and .pdf rendered)
**Related:** `report-editor-types.md`, `report-script-pipeline.md`

---

## The Report Record

Every report, form, letter, export, and function in WC3 is a **Report record**. One model, many purposes.

| Field | What it controls |
|-------|-----------------|
| `editor_type` | Which editor renders the content field (plain, markdown, html, svg) |
| `content` | Document body template — interpreted by editor_type |
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

## Four Editor Types

### plain
- **Editor:** Textarea (12 rows)
- **Rendering:** `<pre>` with preserved whitespace
- **Use case:** Scripts, raw text, simple notes
- **Token support:** No

### markdown
- **Editor:** @uiw/react-md-editor with edit/preview split
- **Rendering:** Python `markdown` library → HTML → WeasyPrint → PDF
- **Use case:** Letters, internal reports, documentation, email templates
- **Token support:** Yes — `{{field.path}}`, `{{field.path|currency}}`, `{{#each lines}}...{{/each}}`
- **Component:** `src/components/common/MarkdownEditor.tsx`

### svg
- **Editor:** PrintLayoutDesigner (panel-based visual editor)
- **Rendering:** SVG populate (resolve IDs → data, clone line panels)
- **Use case:** Designed print forms — invoices, POs, proposals
- **SVG workflow:** Select fields → Export SVG → Design externally → Import back → Populate with data
- **Component:** `src/components/print/PrintLayoutDesigner.tsx`, `src/components/print/SvgFormGenerator.ts`

---

## The Script Pipeline

Scripts and content are **parallel layers**. Scripts compute the data. Content provides the layout. A report can have both, one, or neither.

```
┌──────────────────────────────────────────┐
│  script_before ─── runs ONCE             │
│  • initialize accumulators               │
│  • open connections / streams             │
│  • establish working set                 │
├──────────────────────────────────────────┤
│  script_during ─── runs per RECORD       │
│  • calculate / accumulate                │
│  • format / transform                    │
│  • UNLOAD record when done               │
├──────────────────────────────────────────┤
│  script_after ─── runs ONCE              │
│  • write totals / summary                │
│  • format final output                   │
│  • send notifications                    │
│  • close streams                         │
└──────────────────────────────────────────┘
```

**Two rules:**
1. **Unload records** after processing — never hold all in memory
2. **Read-only** when not modifying records — prevents accidental writes

**Scripts as part of other outputs:** Any output type (print, email, export, json) can have scripts. The scripts run first, producing data that the content template consumes. For email: `script_before` opens the connection, `script_during` builds the recipient list, `script_after` sends.

---

## Output Types

| output_type | What it produces | Common editor_types |
|-------------|-----------------|-------------------|
| `print` | PDF download or browser view | markdown, html, svg, (config.form JSON) |
| `email` | HTML body or PDF attachment → Action record | markdown, html |
| `screen` | Interactive page (DynamicDetail form or custom .tsx) | — (rendered by React) |
| `export` | CSV / Excel / JSON download | plain (scripts produce the data) |
| `json` | Function execution (split order, calculate commission) | — (scripts only) |
| `label` | Avery / thermal / barcode / QR | html, svg |
| `merge` | Template + data mail merge | markdown, html |
| `api` | JSON payload to Connection endpoint | — (scripts + config.endpoint_url) |

---

## Email & Letter Approach — We Are Not a Formatting Tool

Users have Gmail, Word, Pages, Outlook. WC3 provides **data**, not formatting.

**The {{token}} clipboard** is the key feature:
1. User opens a report with `{{tokens}}` in the markdown editor
2. Preview resolves tokens against real data — user sees what it looks like
3. User copies resolved text and pastes into Gmail, Word, Pages, or any tool
4. WC3 also exports data as CSV/JSON for mail merge in Gmail, Word, etc.

**Template path automation** for important templates:
- Store the file path in `Report.config.template_path` (e.g., `~/Documents/Templates/invoice_cover.docx`)
- WC3 opens it populated via AppleScript (Mac) or terminal commands (Windows/Linux)
- The template lives in the user's tool — they design it, we fill it

| Use case | How |
|----------|-----|
| Overdue notice | Copy resolved `{{tokens}}` → paste into Gmail compose |
| Mail merge (100 customers) | Export CSV with resolved fields → Gmail mail merge or Word merge |
| Thank you letter | Template path → AppleScript opens Pages with data filled |
| Customer statement | SVG form (print path) or export PDF |
| Mailing labels | Export CSV → Avery template in Word/Pages |

**Not installed (by design):** TinyMCE. Users already have better formatting tools. WC3 provides the data layer.

---

## SVG Form Workflow

1. **User selects fields** inside WebClerk → PrintLayoutDesigner
2. **Export SVG** → clean SVG with IDs on every element
3. **Design externally** → Affinity Designer, Figma, Illustrator — fonts, positions, styling
4. **Import SVG back** → designed template with IDs intact
5. **Populate with data** → SvgFormGenerator resolves IDs → record values

**JSON runtime config** (not design — design is in the SVG):
- `lines_page_1` / `lines_following` — line slots per page
- `max_description_lines` — wrap budget before truncation (default 2)
- `show_page_numbers` / `show_domain` — standard footer offerings
- `text_format` — markdown or plain for comments/conditions

**Seeded SVG Form Reports:** Invoice, Order, Proposal, Purchase Order, Payment Receipt — all staged (`is_active=False`, `purpose=svg-form-staged`). Set `is_active=True`, `purpose=svg-form`, `dt_approved=now` when print-ready.

---

## Custom .tsx Pages

Developers write React pages using WC3's component library. Separate from core code — survives updates.

| Path | Purpose |
|------|---------|
| `src/custom/pages/` | Custom .tsx page components |
| `src/custom/components/` | Custom reusable components |
| `src/custom/index.ts` | Registry — one lazy import per page |
| `/custom/:page` | Route — live at this URL |

**Available imports:** DataGrid, BaseField, DynamicDetail, wcapi (getRecords/saveRecord), hooks (useListFieldConfig, usePrintLayout), context (WindowManager), formatters.

**Registration:** Report record with `output_type=screen`, `purpose=custom-page`, `config.component=PageName`.

---

## Content Priority

When `render_report()` is called:

1. **Report.content** (non-empty) → render using editor_type
2. **config.form** (PrintLayout JSON) → UniversalPrint / SVG populate
3. **Built-in template** (template_key) → Invoice, Pick List, etc.
4. **Generic fallback** → auto-generated table from model fields

User-authored content overrides built-in templates.

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

## Flowchart

`readmes/charts/flowcharts/wc3-report-system.dot`

Rendered to `.svg` and `.pdf`. Shows: entry points → Report record → editor types → script pipeline → content rendering → output types → SVG form workflow → custom pages → audit trail.

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
