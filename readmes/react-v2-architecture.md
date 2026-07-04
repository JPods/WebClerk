# React v2 — World-Class Face for WC3
**Status:** Architecture decision | **Source:** Bill 2026-07-04

---

## Approach

Current React stays as baseline on port 5174. New site on 5173. Start from scratch.

---

## Principles

1. **Dashboard-first** — start with the dashboards users need, not models
2. **Data-driven pages** — most pages built from data-templates, not hardcoded .tsx
3. **DataBrowser + JSON viewer** — link to these for data management, don't rebuild
4. **Print where expected** — convenient human-printable documents at natural points
5. **Blockchain audit** — every page/template has a blockchain_id; changes mandate update; Athena enforces

---

## Page Hierarchy

### Tier 1: Dashboards (what users open daily)

| Dashboard | What It Shows | Priority |
|---|---|---|
| **Commerce** | Sales / Purchasing / Inventory / Velocity / Accounting (5 tabs) | 1 |
| **My Work** | Actions assigned to me, calendar view, recent activity | 2 |
| **Customer 360** | One customer: orders, invoices, payments, aging, serials, actions, Q&A | 3 |
| **Item 360** | One item: BOM, serials, inventory layers, vendors, sales history, velocity | 4 |

### Tier 2: Data Management (DataBrowser + JSON viewer)

Not rebuilt — linked from dashboards:
- Click a customer name → DataBrowser opens for that contact
- Click a JSON field → JSON viewer opens in new window
- Spawn links → related records in new DataBrowser windows

### Tier 3: Documents (print-ready)

Convenient where users expect them:
- Invoice detail → [Print] button → StatementPrintDocument
- Customer detail → [Statement] button → generates and prints
- Order detail → [Packing Slip] button → no-price version

### Tier 4: Standard .tsx Pages (hardcoded where important)

- Login / authentication
- Settings / admin
- Report Designer (pdfme)
- Error pages

---

## Data-Template Pages

Most pages are NOT .tsx files. They are data-templates stored as Report/Setting records:

```json
Report (category='page_template') config = {
  "layout": "dashboard",
  "sections": [
    {"type": "metrics_row", "data_source": "get_sales_dashboard", "fields": [...]},
    {"type": "table", "data_source": "get_ar_aging", "columns": [...]},
    {"type": "chart", "data_source": "get_velocity_report", "chart_type": "bar"}
  ],
  "filters": ["period", "salesperson", "customer"],
  "blockchain_id": "abc123..."
}
```

A generic React renderer reads the template and builds the page. No .tsx per page. Template changes = page changes. No deploy needed.

---

## Blockchain Audit Trail

Every page and template carries a `blockchain_id` linked to a record in WC3:

```
Template saved/modified
  → hash(template_content) computed
  → blockchain record created: {hash, previous_hash, dt, modified_by}
  → blockchain_id stored on the template record
  → Athena verifies: if page renders with a template whose hash doesn't match → BLOCK

This is the tamper-evident audit trail for the UI itself.
```

Why: if someone modifies a page to show wrong prices, hide fields, or inject harmful content — the blockchain hash won't match and Athena rejects the render.

---

## Port Assignment — Multiple Experiments

Start from zero. Make several attempts. Ask people what they think. Same backend, different faces.

| Port | What | Purpose |
|---|---|---|
| 5173 | Experiment A | First attempt — dashboard-first, data-driven |
| 5174 | Current React (baseline) | Reference, comparison, fallback |
| 5175 | Experiment B | Different approach (maybe different framework/library) |
| 5176 | Experiment C | Another approach (maybe mobile-first) |
| 8000 | Django API | Backend — serves them all, unchanged |

Each experiment is a learning iteration. The best one wins — or the best pieces from each combine. Don't commit to one face. Real user feedback drives the decision. Start small, iterate relentlessly.

---

## Migration Strategy

1. All sites run simultaneously — users compare
2. Each experiment starts with dashboards only — links to 5174 for anything not yet built
3. User feedback determines which approach moves forward
4. Best pieces from multiple experiments can combine
5. When the winner covers everything, others become archive

---

## What Carries Forward from Current React

| Keep | Why |
|---|---|
| CSS custom properties pattern | Theme-aware, no inline styles |
| Field widgets (16 components) | Standalone, reusable |
| DataGrid with tree mode | Proven, feature-complete |
| JSON viewer | Zero-dependency, cross-window |
| windowChannel (BroadcastChannel) | Cross-window messaging |
| useAppBootstrap | Server-driven defaults |
| Print document components | Statement, Tax Report, Invoice, etc. |
| filterOperators + widgetTypes | Constants/schema |

| Rebuild | Why |
|---|---|
| Page structure | Data-template driven instead of .tsx per page |
| Navigation/routing | Dashboard-first, not model-list-first |
| Layout/styling | World-class design, not developer-functional |
| Component library | Consistent design system with proper tokens |

---

## Next Steps

1. List all dashboards users need (Bill defines)
2. Design the template renderer (reads Report config, builds page)
3. Set up Vite project on 5173
4. Build Commerce Dashboard first (already designed, has backend services)
5. Build My Work dashboard (Actions filtered by user + calendar)
6. Implement blockchain audit (cBlock pattern from WC2 mining)
