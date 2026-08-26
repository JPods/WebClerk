# Model Layout Map — Which Models Get What

**Terms:** list, detail, form, column, custom — established 2026-08-18. See `db-layout-schema.md`.
**Supersedes:** `ui-db-map.md` and `model-ui-map.md` (both retired).

---

## The Three Rendering Paths

| Path | What renders it | When to use |
|------|----------------|-------------|
| **form** | DynamicDetail / *DetailJson (cards, tabs, lines, edit rules) | User touches it during business |
| **custom** | Custom React component (.tsx) | Complex interaction (drag, timeline, real-time) |
| **detail** | GroupedDetailFields (all fields, collapsible groups) | Admin/config, structured data |

Every model gets **list** + **detail** automatically via DataBrowser. The question is:
does it ALSO get a **form** layout or a **custom** component?

If a model has no form or custom entry, it's **detail-only**.

---

## Form Models — Curated Business Forms

These get form layouts in `config.layout.form`, Design Mode, print templates, widget actions.

### Transactions (family: sell/exec)

| Model | Layout | Family | Status |
|-------|--------|--------|--------|
| order | 3-col: Customer \| Ship To \| Order | sell | Done |
| proposal | 3-col: Customer \| Ship To \| Proposal | sell | Done |
| invoice | 3-col: Customer \| Ship To \| Invoice | sell | Done |
| purchase | 3-col: Vendor \| Receive At \| Purchase | exec | Done |
| workorder | 3-col: Customer \| Location \| Work Order | exec | Pending |
| receipt | 2-col: Vendor \| Receipt | exec | Pending |
| requisition | 2-col: Requestor \| Requisition | exec | Pending |
| payment | 2-col: Payer \| Payment | special | Pending |

### Transaction Lines (rendered inside parent line card)

| Model | Parent | Family | Status |
|-------|--------|--------|--------|
| order_line | order | sell | Done |
| proposal_line | proposal | sell | Done |
| invoice_line | invoice | sell | Done |
| purchase_line | purchase | exec | Done |
| workorder_line | workorder | exec | Pending |
| receipt_line | receipt | exec | Pending |
| requisition_line | requisition | exec | Pending |

### Communications (family: comm)

| Model | Layout | Status |
|-------|--------|--------|
| email | single-col card | Seeded |
| phone | single-col card | Seeded |
| address | single-col card | Seeded |
| domain | single-col card | Seeded |

### Core (family: core)

| Model | Layout | Status |
|-------|--------|--------|
| contact | 3-col: Contact \| Address \| Profile + 7 tabs | Seeded |
| action | 2-col: Action \| Assignment | Seeded |
| document | 2-col: Document \| Attachment | Seeded |
| question_answer | single-col | Seeded |
| report | 2-col: Report \| Settings | Seeded |

### Organizations (family: org)

| Model | Layout | Status |
|-------|--------|--------|
| customer | 3-col: Company \| Primary Contact \| Account | Pending |
| vendor | 3-col: Company \| Primary Contact \| Account | Pending |
| manufacturer | 2-col: Company \| Contact | Pending |
| employee | 2-col: Person \| Employment | Pending |
| rep | 2-col: Person \| Territory | Pending |

### Products (family: product)

| Model | Layout | Status |
|-------|--------|--------|
| item | 3-col: Item \| Pricing \| Inventory + 8 tabs | Seeded |
| serial | 2-col: Serial \| Assignment | Seeded |
| specification | single-col | Seeded |

---

## Custom Models — Interactive React Components

These are interaction-heavy — drag, drop, timeline, real-time updates. JSON drives the data, .tsx owns the interaction.

| Component | What it does | Models involved |
|-----------|-------------|-----------------|
| KanbanBoardPage | Drag cards between columns | action, project |
| UnifiedGantt | Timeline with drag resize | action, project |
| ApplyPayments | Drag payments to invoices | payment, invoice |
| ShoppingCart | Cart with qty, checkout | item, order |
| InventoryDashboard | Receive, adjust, reconcile | item, warehouse, serial |
| Alice Dashboard | Observations, insights, coaching | alice_observation |

---

## Detail-Only Models — DataBrowser Administration

These use list + detail only. No form layout. No custom component.

### Accounts
| Model | Why detail-only |
|-------|-----------------|
| gl_account | Chart of accounts — admin setup |
| gl_journal | Journal entries — accounting |
| ledger | Ledger records — accounting |
| tax_jurisdiction | Tax rates — admin config |
| term | Payment terms — admin config |
| currency | Currency codes — admin config |
| exchange_rate | FX rates — admin config |
| exchange_transaction | FX transactions — accounting |
| audit | Audit log — system records |
| erosion | Write-downs — accounting |

### Core Config
| Model | Why detail-only |
|-------|-----------------|
| setting | System config — admin |
| template | Document templates — admin |
| notification | System notifications — admin |
| pending | Queue records — system |
| api_log | API audit — system |
| audit_log | Change audit — system |
| role_config | RBAC — admin |
| model_link_config | Model links — admin |
| model_role_config | Model RBAC — admin |
| user_profile | User accounts — admin |
| user_daily_log | Activity — system |
| soft_delete_ledger | Soft delete audit — system |
| refs_mismatch_log | Data quality — system |

### Docs Config
| Model | Why detail-only |
|-------|-----------------|
| linkage | Linkage entries — system |
| tag | Tags — admin |

### Products Config
| Model | Why detail-only |
|-------|-----------------|
| bill_of_material | BOM records — detail-only standalone, embedded as card in Item BOM tab |
| catalog | Catalog config — admin |
| catalog_line | Catalog entries — admin |
| item_xref | Cross-references — admin |
| org_item | Org-item links — admin |
| service | Service records — admin |
| variant | Variants — admin |
| warehouse | Warehouse config — admin |
| inventory_layer | FIFO/LIFO layers — system |
| inventory_movement | Stock flow — system |
| inventory_reservation | Holds — system |
| pending_inventory_adjustment | Queue — system |
| inventory_metrics_snapshot | Analytics — system |
| site_inventory | Per-location stock — system |
| item_usage | Usage tracking — system |
| serial_log | Serial audit — system |
| delivery_visit | Delivery tracking — system |
| delivery_line | Delivery items — system |

### AI Assistant
| Model | Why detail-only |
|-------|-----------------|
| alice_coaching_log | Alice training — system |
| alice_insight | Alice patterns — system |
| alice_preset | Alice config — admin |
| coding_session | Session records — system |
| conversation | Chat history — system |
| error_pattern | Error tracking — system |
| git_event | Git audit — system |
| inventory_event | Inventory tracking — system |
| message | Chat messages — system |
| schema_drift | Schema audit — system |

### Sync
| Model | Why detail-only |
|-------|-----------------|
| connection | Sync config — admin |
| bundle | Sync bundles — system |

### Transactions Config
| Model | Why detail-only |
|-------|-----------------|
| payment_application | Applied payments — system |
| payment_method | Payment methods — admin |
| payment_term | Payment terms — admin |
| pending_payment_application | Payment queue — system |
| statement_line | Statement entries — system |
| project | Projects — has custom Kanban/Gantt but no form layout |

---

## Dashboards

Dashboards are panel layouts stored as Settings. The panel renderer reads the config
and renders the right component for each panel type.

| Dashboard | Panels | Notes |
|-----------|--------|-------|
| Commerce | KPIs, orders, invoices, AR | list panels + sales chart |
| Forecast | Running balance, pipeline, AR/AP | list panels + area chart |
| Apply Payments | Customer search, invoice list, payment form | list + form + drag-apply |
| Inventory | Receive, adjust, reconcile, warehouse | list panels + count sheet |
| Script Editor | Prompt, code editor, output | form + code console |
| Alice | Observations, insights, coaching | list panels |
| Team | Activity, performance | list panels + chart |
| Accounting | GL, journals, aging | list panels |

## Printing

Print templates read from the same layout JSON as the working form.
The print renderer builds standalone HTML — no React, no app chrome.

| Output | Driven by | Notes |
|--------|-----------|-------|
| Standard document (order, invoice, etc.) | form layout + record data | TransactionPrint.tsx |
| Pick list | form layout + report config (no prices, show location) | Template variant |
| Packing slip | form layout + report config (no prices, show shipped qty) | Template variant |
| Labels/barcodes | Report config + pdfme | custom component (pdfme editor) |
| Statements | form layout + aging calculation | Template variant |
| Letters/email | Report config + template merge | Template-driven |
| EDI/export | Report config + format spec | External convention may force custom |
| Custom reports | Report model config | User-defined via Report records |

**The rule:** if the output follows the document layout, the **form** layout drives it.
If the output requires a specialized renderer (barcode layout, EDI format), **custom**.

## How to Add a New Model

1. Decide: business workflow or admin? (Does a user touch it during business?)
2. If workflow: add a **form** layout to the model's `wc:model` Setting (`config.layout.form`)
3. If admin: DataBrowser handles it — add to `config.layout.list` / `config.layout.detail` if custom column or field order needed
4. Add to this map

## Summary

- **All models**: list + detail (DataBrowser) for administration — universal
- **~35 models**: form — curated business forms for daily workflow
- **~8 models**: custom — interaction-heavy React components
- **~50 models**: detail-only — config, system, admin, accounting
