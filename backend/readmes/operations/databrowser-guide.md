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
