# databrowser — Operations Guide
**Built:** 2026-07-03/04 | **Route:** `/admin-wb`

---

## Overview

databrowser is the universal record browser. Any model, one interface. List pane + detail pane. Every feature in WC3 is accessible through databrowser — it replaces 40+ admin pages.

---

## Key Features (built this session)

### doSafeSelect
After deleting a record, databrowser auto-selects the adjacent record. No blank detail pane.

### Reset Layout
Button restores the `initial` or `alice_guess` seeded layout. Users can experiment freely knowing they can get back.

### CSS Custom Properties
Zero inline styles. Theme via `data-theme="dark/light"` and `data-fontsize="S/M/L"` attributes on `.db-root`. All colors, borders, inputs use CSS custom properties (`--db-bg`, `--db-accent`, etc.).

### 16 Field Widgets
Standalone components in `components/fields/`:
- **Actionable labels** (blue): EmailField (mailto), PhoneField (tel), UrlField (link), AddressField (maps), JsonField (opens JSON viewer)
- **Selection** (green): SelectField
- **FK reference** (purple): LookupField
- **Standard**: TextField, NumberField, CurrencyField, BooleanField, DateField
- **Read-only** (dim): TimestampField, ReadonlyField
- **Expandable**: JsonField, TextareaField

Each accepts: `name, value, onChange, error, disabled, typeHint`. Direct use: `<CurrencyField name="total" value={x} onChange={fn} />`. Dynamic use: `getWidget('currency')` from the registry.

### typeHint Override
A layout can override the auto-detected field type. An IntegerField can display as a boolean checkbox if the layout says so.

### Client-Side Validation
`validateRecord.ts` accumulates ALL errors before showing. Required fields, email format, phone format, number type, select choices, max length. Field-keyed error dict displayed next to each field.

### Operator Vocabulary
Single source of truth: `filterOperators.ts` (React) + `filter_operators.py` (Django). Operators mapped by field type: text→contains/begins/ends, number→gt/lt, date→range, boolean→is/is_not.

### Widget Type Schema
`widgetTypes.ts` — 16 types with defaults (width, sizing, sortable, editable, filterType, actionable, labelColor). Adding a new type = one entry here + one render case in the field component.

---

## DataGrid Tree Mode

Three props turn any flat data into a tree:
```typescript
<DataGrid
  treeColumn="item_ida"        // which column gets indent + ▶/▼ chevron
  levelField="level"           // data field carrying depth number
  childFlag="is_subassembly"   // which rows are expandable
/>
```
Same columns at every depth. Expand/collapse is client-side filtering. Used for BOM display.

---

## JSON Viewer

Standalone window at `/json-viewer`. Zero npm dependencies.

- Collapsible tree with depth control (1/2/3/5/All)
- URLs render as clickable links (documents are URL pointers — click opens them)
- `_id` fields link back to databrowser (customer_id → opens contact)
- Epoch ms timestamps auto-formatted as dates
- Copy-to-clipboard
- Dark/light theme syncs with databrowser

JSON field labels are clickable (same pattern as email→mailto, phone→tel).

Spawned via: `window.open('/json-viewer?model=X&id=N&field=F')`

---

## Cross-Window Messaging

`windowChannel.ts` — BroadcastChannel API wrapper. Zero server load.

| Message | When | Effect |
|---|---|---|
| `record-selected` | User clicks a record in databrowser | JSON Viewer reloads |
| `record-saved` | Record saved | JSON Viewer refreshes |
| `theme-changed` | Theme toggled | All windows sync theme |

---

## BOM Panel

When viewing an Item with BOM children, the detail pane shows the BOM tree:
- Build qty input — recalculates on change
- Cost basis selector: Average / Last Receipt / Min / Landed
- Total cost displayed
- "Open BOM ↗" spawns full BOM databrowser
- Double-click sub-assembly opens that item in new window

---

## Spawn Links

When viewing complex records, a spawn bar shows related-window buttons:

| Model | Spawn Links |
|---|---|
| Serial | History, Q&A, Documents, Actions, Customer, Vendor |
| Item | Serials, XRefs, Org Items, Documents |
| Invoice | Lines, Payments, Customer, Documents |
| Order | Lines, Customer, Documents |
| Contact | Orders, Invoices, Payments, Serials, Actions, Documents |

Desktop: `window.open()` for side-by-side. Mobile (future): tabs within one view.

---

## Commerce Dashboard

Unified 5-tab view at `/commerce`: Sales | Purchasing | Inventory | Velocity | Accounting

Shared filter bar: period, salesperson, rep, customer, vendor, warehouse. Double-click any tab to spawn in separate window.

---

## Files

| File | Purpose |
|------|---------|
| `src/pages/admin/AdminWorkbench.tsx` | Main databrowser component |
| `src/pages/admin/AdminWorkbench.css` | CSS custom properties + all classes |
| `src/hooks/usedatabrowser.ts` | All state management |
| `src/components/fields/` | 16 field widgets + BaseField + registry |
| `src/components/fields/fields.css` | Field widget CSS |
| `src/components/common/DataGrid.tsx` | Grid with tree mode |
| `src/components/common/BehaviorField.tsx` | Legacy field renderer (delegates to widgets) |
| `src/constants/filterOperators.ts` | Operator vocabulary |
| `src/constants/widgetTypes.ts` | Widget type schema |
| `src/utils/validateRecord.ts` | Client-side validation |
| `src/utils/windowChannel.ts` | Cross-window BroadcastChannel |
| `src/pages/admin/JsonViewer.tsx` | Standalone JSON viewer |
| `src/pages/admin/CommerceDashboard.tsx` | 5-tab commerce dashboard |

---

## Initial Layouts & Seed Data

**Command:** `./bin/python manage.py seed_databrowser`

### Purpose

Every model in WebClerk3 gets a curated "initial" layout for the databrowser -- a default set of list columns and detail fields, chosen in a deliberate order. This serves three purposes:

1. **Users see useful data immediately** -- not raw field dumps. A new user opening the Customer model sees display_name, status, email, phone -- not id, uuid, dt_created, version.

2. **Alice has a baseline** -- when users submit their own layouts for bonus credit, Alice can compare against the initial layout to see what experienced users prioritize differently. Divergence from the initial layout is a signal about what matters in practice.

3. **Every table has at least one record** -- fake records (marked `metadata.health = "fake"`, prefixed with "zz") let users explore the databrowser without needing real data. They sort to the bottom, they're filterable, and they're deletable.

### Usage

```bash
# Seed both layouts and fake records
./bin/python manage.py seed_databrowser

# Layouts only
./bin/python manage.py seed_databrowser --layouts

# Fake records only
./bin/python manage.py seed_databrowser --fakes

# Overwrite existing layouts with fresh initial versions
./bin/python manage.py seed_databrowser --layouts --force
```

### How Layouts Are Stored

Each model gets one `Setting` record:
- `purpose = "workbench_fields"`
- `parent_model = "<model_key>"` (e.g., "customer", "gl_account")
- `data` contains:
  - `list: string[]` -- fields shown in the list table, in order
  - `detail: string[]` -- fields shown in the detail pane, in order
  - `views: [{ name, list, detail, listWidths }]` -- named saved layouts

The "initial" view is saved as a named layout inside `views[]` so it can always be loaded back even after a user customizes their current view.

### Layout Design Principles

**List view (5-8 fields):**
- Start with `id` -- always need a reference
- Then the most identifying field: `display_name`, `name`, `email`, `account_number`
- Then status -- users scan for active/inactive
- Then 2-3 business-critical fields per model type
- End with a date if space permits

**Detail view (12-20 fields):**
- All list fields plus deeper context
- Business fields before system fields
- JSON envelope fields (price, cost, totals) included for power users
- System fields (dt_created, dt_modified) at the end

**Field order matters:**
- Users scan left-to-right in lists, top-to-bottom in details
- The first field after `id` is the one they'll use to find what they need
- Group related fields (all contact info together, all financial together)

### Curated Layouts by Category

**Orgs** (Customer, Vendor, Manufacturer, Employee, Rep):
List: id, display_name, status, email, phone, address_full, price_level.
Rationale: Who are they, how do I reach them, what pricing tier.

**Transactions** (Invoice, Order, Proposal, Purchase, WorkOrder):
List: id, ida, status, total, balance, dt_created, priority.
Rationale: Where is it in the workflow, how much, when.

**Products** (Item):
List: id, ida, name, kind, status, uom, dt_created.

**Core** (Contact):
List: id, email, name_first, name_last, company, title, role, phone.

**Core** (Action):
List: id, ida, status, kanban_column, priority, percent_complete, project_name, dt_deadline.

**Accounts** (GL Account):
List: id, account_number, name, type, category, division, used_for.

**Accounts** (Ledger):
List: id, value_original, value_available, dt_due, is_settled, source, model_name.

### Fake Records

Fake records are created with:
- `ida` prefixed with `zz-fake-`
- `name` / `display_name` prefixed with `zz Fake`
- `metadata.health = "fake"`
- `email` using `@example.com` domain
- Minimal valid data (status=active, version=1, etc.)

The "zz" prefix ensures fakes sort to the bottom of alphabetical lists. Query `metadata__health='fake'` to find or delete them.

Line items (InvoiceLine, OrderLine, etc.) are skipped because they require parent FK references.

### Alice's Layout Learning Role

When users submit layouts via sync:
1. Alice compares the submitted layout against the "initial" layout for that model
2. Fields the user added that aren't in the initial layout -- things we may have undervalued
3. Fields the user removed -- things we may have overvalued
4. Field order changes -- what users actually scan for first
5. Adoption rate of submitted layouts -- democratic signal about what works

This is the same bottom-up signal loop as Small-Stings: users tell us what matters by what they choose, not by what they say.
