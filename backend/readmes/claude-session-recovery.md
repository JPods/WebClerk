# Claude Code Session Recovery — Read This After Compaction

**Last Updated:** 2026-06-29
**Purpose:** Everything Claude needs to know after context compaction wipes session memory. Read this before doing anything.

## The One Rule That Governs Everything

**ALL CRUD flows through wcapi.** No Django ViewSets. No per-model serializers. No per-model REST endpoints. `wcapi/get`, `wcapi/save`, `wcapi/delete`, `wcapi/manage` — model_name is a parameter. `inject_role_filters` runs in ONE place. Policy is data (Settings), not code.

## What WebClerk IS and IS NOT

**IS:** A commerce and operations platform. Sells, collects receivables, buys, manages inventory, produces GL journal entries.

**IS NOT:** An accounting program. Never build P&L, Balance Sheet, Trial Balance, Cash Flow. Those are the accounting program's job. WebClerk produces GL journal entries by account code — QuickBooks/Xero/Sage consumes them.

**AR collection is SALES finishing the job** (our domain). AP management is accounting (not our domain).

## Architecture — Non-Negotiable

| Principle | What it means |
|-----------|-------------|
| **wcapi is the single gate** | Every read/write goes through wcapi. RBAC, query scoping, field filtering, audit — all enforced there. |
| **field_access Settings** | One Setting per model (purpose='field_access'). Contains roles, query_scope, publish, field_behaviors, formatting. Syncable from WCHQ. |
| **field_behaviors in Settings** | UI rendering driven by data, not code. Email→mailto, phone→tel, address→map, select→dropdown, lookup→FK. Color-coded labels: blue=action, green=select, purple=lookup. |
| **Local + cloud dual storage** | Laptop is system of record. Cloud is backup/collaboration. Both stay synced via Connection + Bundle. |
| **Free platform, paid data services** | Platform is free/open source. WCHQ charges for catalog cleaning, tax/shipping APIs, proximity search indexing. |
| **Desktop Hosting lineage** | Bill's Wiley book (~2002). Your desktop is the server. Relationships determine access. Technology reinforces existing trusted relationships. |

## Key Identifiers

- `ida` = human readable (what you say on the phone)
- `id` = local FK (internal database key)
- `uuid` = cross-database unique identifier (sync join key)

## What Was Built (2026-06-28/29)

### React Frontend (React2025/src/)

| Component | File | Purpose |
|-----------|------|---------|
| `usedatabrowser` | hooks/usedatabrowser.ts | All state + data management for databrowser |
| `BehaviorField` | components/common/BehaviorField.tsx | Renders one field based on field_behaviors — reusable anywhere |
| `AdminWorkbench` | pages/admin/AdminWorkbench.tsx | databrowser at /admin-wb — two-pane, dark/light, JPods Console palette |
| `DetailLayoutDialog` | components/common/DetailLayoutDialog.tsx | Drag/reorder detail fields, behavior badges, row sizes |
| `FieldConfigBar` | components/common/FieldConfigBar.tsx | Collapsible column toggle/reorder bar for any list page |
| `useListFieldConfig` | hooks/useListFieldConfig.ts | Column visibility + ordering for list pages, persisted to Settings |
| `ReportMenu` | components/common/ReportMenu.tsx | Dropdown of available reports per model+record |
| `OrgPage` | apps/orgs/components/OrgPage.tsx | Config-driven org list+detail — one component for all 5 org types |
| `CommunicationsPanel` | apps/orgs/components/CommunicationsPanel.tsx | Inline-editable email/phone/address/domain |
| `orgConfig` | apps/orgs/orgConfig.ts | Per-org-type fields, actions, related records, publish fields |
| Print components | apps/transactions/print/*.tsx | Invoice, Order, Proposal, QA print pages + shared printStyles.ts |

### Backend (webClerk3/)

| What | File | Purpose |
|------|------|---------|
| Payment AR+AP | apps/transactions/models/payment.py | `type` field (received/disbursed) + `purchase` FK. Migration 0007. |
| field_access seeder | apps/core/management/commands/seed_field_access.py | 61 models × 8 roles with query_scope + field_behaviors + formatting |
| databrowser layout seeder | apps/core/management/commands/seed_databrowser.py | 61 initial layouts + 31 fake "zz" records |
| Report seeder | apps/core/management/commands/seed_reports.py | 59 reports across 15 models |
| Coaching seeder | apps/core/management/commands/seed_coaching.py | 9 coaching Settings + 3 Documents + 8 onboarding Actions |
| field_access + alice_coaching + seed | apps/core/choices.py | Added to SETTING_PURPOSE_CHOICES |

### Routes & Sidebar

- 40+ admin model routes redirect to `/admin-wb?model=X`
- Sidebar links go directly to databrowser for admin models
- **Shift-click any sidebar model → opens in databrowser** (power user)
- **Cmd/Ctrl+Shift+M** → model picker in databrowser
- 5 org pages at `/org/{customer,vendor,employee,rep,manufacturer}`
- Print pages at `/transactions/{invoice,order,proposal}/print/:id`

### Documents Created (in database)

- 6 WC Training documents (data setup, admin, order processing, inventory, sales, rep quickstart)
- 8 WC3 Flow Chart documents (master, order-to-invoice, purchase-to-inventory, inventory impact, sales/CRM, requisition/sync, report routing, territory)
- 3 system guides (Getting Started, databrowser Guide, wcapi Reference)

## Don't Do List

| Never do this | Do this instead |
|-------------|----------------|
| Create per-model ViewSets or REST endpoints | Route through wcapi — model_name is a parameter |
| Build P&L, Balance Sheet, Trial Balance | Produce GL journal entries for accounting programs |
| Hardcode field rendering in page components | Use BehaviorField with field_behaviors from Settings |
| Create separate org pages per type | Add config to orgConfig.ts, use OrgPage |
| Copy column definitions between list pages | Use useListFieldConfig + FieldConfigBar |
| Write inline state management in pages | Extract to custom hooks |
| Bypass wcapi for any data operation | wcapi enforces RBAC, scoping, field filtering, audit |
| Start writing a function without searching first | Check existing hooks, components, utilities |

## Daily Practice

**Start:** Before writing any function, search for existing like functions. Check if it belongs in an existing hook/component.

**Close:** Audit today's code for overlap. Create test Action records in weekly project (W27). Update handoff.

## WC2→WC3 Gaps (15 items in Alice's queue, GAP-01 through GAP-15)

Critical: Order Production (GAP-01), Backorder Management (GAP-02), Serial Lifecycle (GAP-03), Inventory Stacks FIFO/LIFO (GAP-04), Forecast→Auto PO (GAP-05).

Sales/CRM: Pipeline/Leads (GAP-07), Territories (GAP-09), Campaigns (GAP-10), Commissions (GAP-11).

Time capture (GAP-13): external API integration (Toggl/Harvest/Clockify), not built-in.

## Key Readmes

| Readme | What it covers |
|--------|---------------|
| `readmes/wcapi-query-scoping.md` | How external users see only their data — the full RBAC chain |
| `readmes/databrowser-initial-layouts.md` | Layout design principles, seeding, Alice's baseline comparison |
| `readmes/daily-development-practice.md` | Start/close checklist, reusable components reference, anti-patterns |
| `readmes/alice-coaching.md` | Alice's coaching system — Setting-driven, tips/field_help/actions/warnings/code/API |

## WC3 Value Proposition (for context on WHY)

- Free platform, paid data services (catalog cleaning, tax/shipping APIs)
- WCHQ proximity search — merchants publish inventory, buyers search by distance (kills Amazon's findability advantage)
- Cross-company order→PO→SO linking via sync bundles (EDI for small business at zero cost)
- Vendor blessed list — curated projection, not open access (sovereignty principle)
- JPods Middle Mile cargo delivery integrated into commerce loop
- Layout/template marketplace — users submit via sync for bonus credit

## Bill's Foundation Document

"Desktop Hosting: A Developer's Guide to Unattended Communications" (Wiley, ~2002). The intellectual origin of everything WebClerk is. Core thesis: put communications at the point of action. Your desktop is the server. Relationships determine what each person sees.

Location: Allie's inbox. Also referenced in `readmes/topics/architecture/desktop-hosting-lineage.md`.

## Allie and Alice

- **Allie** holds cross-domain context. Consult her (`ask_allie`) on every significant decision.
- **Alice** manages coaching, training, action tracking. Notes via `wc_add_note`. She needs her own LLM (not built yet).
- All agents go through wcapi. No shortcuts.
