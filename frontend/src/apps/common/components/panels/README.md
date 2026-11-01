# Panels — Architecture & Rules

> **Updated:** 2026-08-26
> **Rule:** All shared panels live here. One canonical path per component.

---

## How Panels Work

Every record in WC3 shows the same panel structure below its form fields. Panels are **self-discovering** — they appear automatically based on what's linked in the record's `refs.links` JSON.

### The Panel Stack (every record)

```
┌─────────────────────────────────┐
│  Form Fields (DynamicDetail)    │  ← data-driven from Report/Setting layout
├─────────────────────────────────┤
│  👤 Contacts (ContactPanel)     │  ← specialized: refs.links.contact
├─────────────────────────────────┤
│  📋 Actions (LinkedRecordsPanel)│  ← standard: always shown
│  📞 Touches (LinkedRecordsPanel)│  ← standard: always shown
│  📄 Documents (LinkedRecordsPanel)│ ← standard: always shown
├─────────────────────────────────┤
│  📦 Items (LinkedRecordsPanel)  │  ← discovered: refs.links.item exists
│  🛒 Orders (LinkedRecordsPanel) │  ← discovered: refs.links.order exists
│  ... any model ...              │  ← discovered from refs.links keys
├─────────────────────────────────┤
│  [+ Link...]                    │  ← user adds any model panel
├─────────────────────────────────┤
│  File Upload (FileUploadPanel)  │
│  Open in page                   │
└─────────────────────────────────┘
```

All panels are **collapsed by default**. Click to expand. Each panel has a hamburger for column configuration.

### Self-Discovery Rules

1. **Standard panels** (Actions, Touches, Documents) always appear, even if empty
2. **Contacts** always appears (uses specialized ContactPanel with purpose/role)
3. **Discovered panels** appear when `refs.links.{model}` has a key — even if the array is empty
4. **User-added panels** appear via "+ Link..." which creates an empty `refs.links.{model}: []` entry
5. **Same-model links** are allowed (order → order, contact → contact)
6. **Self-link guard**: clicking a linked record never navigates the current view — always opens in a new window. Clicking the current record's own ID does nothing.

### How a Panel Appears

```
User clicks "+ Link..." → selects "item"
  → refs.links.item: [] saved to record
  → DynamicDetail reads Object.keys(refs.links)
  → LinkedRecordsPanel for "item" renders
  → User searches and links specific items
  → Next load: refs.links.item has entries → panel auto-discovers
```

No configuration file. No registration. The data IS the configuration.

---

## Two Panel Components

### ContactPanel (specialized)

For `refs.links.contact` only. Adds purpose badges (billto, shipto, approver, cc, etc.), primary contact star, and contact-specific data resolution (fetches email/phone from contact record when inline data is missing).

Built on `DbColumns` — same hamburger, same column config, same behavior as all panels.

### LinkedRecordsPanel (universal)

For every other model. One component handles all of them:

```tsx
<LinkedRecordsPanel
  linkedModel="item"           // any model name
  parentModel="order"          // the record we're viewing
  parentId={42}
/>
```

Features:
- Reads `refs.links.{linkedModel}` from parent record
- Fetches linked records via wcapi
- Displays in DbColumns with smart default columns (ida, name, status, plus model-specific: sku for items, channel for touches, totals for transactions)
- Hamburger → FieldOrderDialog for column order, visibility, drag-reorder
- Columns from the linked model's `config.layout.panel`; the WC List Standard (`useListGestures`):
  click selects, double-click or Enter opens the record's card (or its window), Option-double-click
  opens a browser window
- "+ add" → the model's card.add (usePanelAdd); "assign" → type-ahead search; "×" → unlink
- storageKey: `panel:{parentModel}:{linkedModel}` — each context gets its own column config

Every panel list is this component (Bill, 2026-10-31: "all panels and lists have the same
inherited code and only very rare specialty behaviors"). A panel's speciality comes in as props:

| Prop | For | Used by |
|------|-----|---------|
| `byField` | rows are the records whose own field holds the parent's id; nothing is stored on the parent; no unlink | serials, xref, specs (`item_id`), BOM (`parent_item_id`), catalog lines (`catalog_id`) |
| `read` | rows from a service view | inventory layers (computed remaining) |
| `pick` | "+ add" picks a record of another model and makes the row with both ids | BOM component, catalog item line |
| `chipField` | count chips per value; a click filters | serial status |
| `groupBy` / `groupSummary` | a heading per group with its sums | layers by warehouse |
| `extraActions` / `children` | the panel's own buttons and content | Build from BOM, + scope line, upload |

Lists that are not records (an order's margin, commission and inventory views, the related
documents) are `DbColumns` with columns in code.

### Row order — one rule for every list (Bill, 2026-11-01)

No panel sorts its rows. The server's list endpoint orders every list, panel and report the same
way (`backend/apps/core/services/list_order.py`):

1. What was asked: a column click, `?ordering=a,-b`, a saved search.
2. The model's `config.orderby` on its wc:model Setting, such as `["parent_item_id", "sequence"]`.
3. `sequence`, when the model has one.
4. Newest first (`-dt_created`).

`id` ends every order, so tied rows keep their places from one read to the next. An unknown
field in an ordering is dropped, not obeyed.

**Why `config.orderby` leads `sequence`:** a bill of materials ordered by `sequence` alone lists
every parent's line 1, then every parent's line 2. What is wanted is each parent's lines
together, in sequence: `["parent_item_id", "sequence"]`. A sequence orders rows *within*
something, and only `orderby` can say within what.

The first guess for each model is `list_order.DEFAULT`, seeded into `config.orderby`. The
company changes it on the Setting; a reseed keeps the company's.

---

## Column Config — Three-Tier Inheritance

`useListFieldConfig` resolves column configuration with inheritance:

| Priority | Source | Who controls | Scope |
|----------|--------|-------------|-------|
| 1 (highest) | localStorage | User | Personal override per browser |
| 2 | Report config | Admin | Context-specific (e.g., a dashboard report) |
| 3 | Setting `wc:model` | Admin | System-wide default for this model |
| 4 (lowest) | Hardcoded columns | Developer | Fallback |

**User changes** save to localStorage automatically.
**"Reset to default"** clears localStorage, falls back to Report or Setting.
**"Save to Setting"** (admin) persists current layout as the new system default for all users.

Each panel gets its own `useListFieldConfig` instance with a unique `storageKey`:
- `panel:order:contacts` — contacts panel on an order
- `panel:order:action` — actions panel on an order
- `panel:action:touch` — touches panel on an action

The `configSource` property tells the UI where current config came from: `'local'`, `'report'`, `'setting'`, or `'default'`.

---

## One row engine: DbColumns, and what inherits from it (Bill, 2026-11-01)

Bill: "one set of code to manage rows of records/array elements with specialty features added as
needed"; "DbColumn is the parent that DataGrid inherits and expands on … relatively simple list
displays in panels and more complex in db.lists"; "cascade or tree list might inherit but not be
part of DbColumn".

| Layer | File | Adds | Used by |
|---|---|---|---|
| `DbColumnsTable` | `DbColumns.tsx` | the one `<table>`: labels, rows, alignment, group headings, slots | everything below |
| `DbColumns` | `DbColumns.tsx` | column dialog (storageKey), the WC List Standard gestures, the panel frame | every panel |
| `DataGrid` | `components/common/DataGrid.tsx` | column filters, sort, edit-in-list, Σ footer, dupes, color rules, column menu, toolbar | record lists, transaction lines |
| `TreeList` | `TreeList.tsx` | parent/child fold and indent | the BOM tree |

- **One look for a value:** cells format through `cellFormat.ts` (`formatCell`, `cellAlign`,
  `headerStyle`) — the same in a panel, a record list or a tree. Empty is blank.
- **One CSS:** `DbColumns.css` (`dg-*` classes on the `--db-*` theme variables).
- **The extension slots** (`DbColumnsTable` props): `headerCell` (an extension's own header
  cell), `headerRows` (a filter row), `footer` (Σ), `rowProps` / `cellProps` (classes, handlers),
  `renderCell` (an editor while editing), `cellPrefix` (a tree's chevron), `groupBy` /
  `groupLabel` / `groupSummary`.
- **Business numbers are the server's; summaries of the rows shown are the browser's** (Bill,
  2026-11-01). A BOM rollup, a line amount, tax, a balance: the server (`tree_calc.roll_up`,
  `bom_ops.expand_tree`, what-if by POST with unsaved values). The Σ row: the rows on screen —
  users show and omit records and the sums follow. Which columns total is `cellFormat.footerKind`:
  a behavior's `footer` (sum / average / count / none, set in the behavior dialog), else amounts
  and quantities sum and prices, rates and per-unit costs do not.
- **A tree's rows come depth-first from the server** (`bom_ops.expand_tree`): each parent
  followed by its children, with their level.

```tsx
<DbColumns<T> storageKey="panel:order:contacts" columns={columnDefs} data={records}
  rowKey={(r) => r.id} sectionLabel="Contacts" onAdd={(el) => add(el)} compact />
```

---

## Rules

### 1. One canonical path per component

Every panel has exactly one source file in `src/apps/common/components/panels/`. Import from here. Never create re-export shims.

### 2. Panel row clicks always open in a new window

Never navigate the current detail view from a panel click. Always use `windowManager.ensureWindow()`. This prevents data loss from replacing an unsaved record.

### 3. Self-link guard

If `linkedModel === parentModel && record.id === parentId`, the click does nothing. You cannot open yourself in yourself.

### 4. Panels don't duplicate features

With self-discovering panels, the old integration matrix (which model has which panel) is obsolete. Every model gets every panel through DynamicDetail. The data determines what appears, not a configuration matrix.

### 5. Every list of rows is DbColumns or inherits from it

A panel uses `DbColumns`; a heavier list uses `DataGrid`; a hierarchy uses `TreeList`. No
custom table rendering. A speciality is a prop or a slot, not a new table.

---

## File Inventory

### Core infrastructure

| File | What |
|------|------|
| `../CollapsiblePanel.tsx` | The one panel frame — header, count, actions, collapse, loading/error/empty; panels declare theirs with `usePanelFrame` |
| `@/hooks/usePanelRecords.ts` | The one panel read — records plus the status the frame shows |
| `DbColumns.tsx` | The row engine's base: `DbColumnsTable` (the one table) and `DbColumns` (a panel's list) |
| `DbColumns.css` | The one table's CSS |
| `cellFormat.ts` | How a value looks in any list cell |
| `TreeList.tsx` | DbColumns with parent/child fold and indent |
| `LinkedRecordsPanel.tsx` | Universal any-model-to-any-model linking panel |
| `ContactPanel.tsx` | Specialized contact panel with purpose/role |
| `getModelDetailPath.ts` | Model → detail route + window size mapping |
| `types.ts` | Shared types |
| `usePermissions.ts` | Role-based access hook |
| `documentUpload.ts` | Upload utilities |

### Entity panels (specialized behavior beyond LinkedRecordsPanel)

Actions are a LinkedRecordsPanel (refs.links.action, two-sided; Bill 2026-10-31): every list
inherits one code, and a specialty belongs in the record's .form. The two below are editors, not lists.

| File | Why it's separate from LinkedRecordsPanel |
|------|------------------------------------------|
| `CommentsPanel.tsx` | Four-tab comment editor (Public/Process/Partner/Notes) |
| `FinancialsPanel.tsx` | Margin calculation, aging summary, credit display |

A record's documents are a LinkedRecordsPanel (refs.links.document, two-sided) with
`FileUploadPanel` under the rows: an upload makes the Document and lists it on the record.

These exist because they have domain-specific behavior that a generic linked-records list can't provide. They still draw no header, loading or empty text of their own: the frame does (`usePanelFrame`), lists read through `usePanelRecords`, and tables are `DbColumns`.

### Admin panels

| File | Visible to |
|------|-----------|
| `RefsPanel.tsx` | admin — `.refs` JSON viewer |

---

## Django Model Alignment

All panels read from `BaseModel` JSONB fields:

| Field | Panels |
|-------|--------|
| `.refs.links.contact` | ContactPanel |
| `.refs.links.{model}` | LinkedRecordsPanel (self-discovering) |
| `.refs.links.document` | LinkedRecordsPanel (+ FileUploadPanel to upload) |
| `.comments` | CommentsPanel |
| `.config` | DynamicDetail form fields |

The `refs.links` pattern is the universal association mechanism:

```json
{
  "refs": {
    "links": {
      "contact": [{"id": 42, "purpose": "primary"}, {"id": 43, "purpose": "cc"}],
      "item": [{"id": 5}, {"id": 12}],
      "order": [{"id": 100}],
      "action": [{"id": 7}, {"id": 8}]
    }
  }
}
```

Any key in `refs.links` triggers a panel. The key is the model name. The value is an array of linked record references.

---

## Quick Import Reference

```tsx
// The frame, the read, the table
import CollapsiblePanel, { usePanelFrame } from '@/apps/common/components/CollapsiblePanel';
import { usePanelRecords } from '@/hooks/usePanelRecords';
import { DbColumns } from '@/apps/common/components/panels/DbColumns';
import type { DbColumnDef } from '@/apps/common/components/panels/DbColumns';

// Panels (default exports, imported by path — there is no barrel)
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';
import ContactPanel from '@/apps/common/components/panels/ContactPanel';
import type { RefContact } from '@/apps/common/components/panels/ContactPanel';
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';

// Column config hook
import { useListFieldConfig } from '@/hooks/useListFieldConfig';
```

---

## The panel read sweep

`npm run sweep:panels` (Playwright, `frontend/e2e/panel-reads.e2e.ts`) opens every record page —
the newest record of each model plus a few with linked data — clicks every tab, expands every
panel, selects a line and opens its Inventory / Spec / XRef. It fails on:

- a `/wcapi/` read the backend refuses or fails (the backend refuses filters it does not know)
- a panel showing its error line (`data-wc-panel-error`)
- an uncaught page error
- a write sent by merely opening a page (writes are blocked; read-only POSTs — the record
  channel's preview commands and `_manage` `get_*`/`check_*` — pass)
- one address read more than 10 times on one page

It runs against the dev servers already up (vite :5173, Django :8000), signs in as
claude@jpods.com, and paces itself under the backend's limits (sign-in 10/min, reads 1000/min).
Results: `frontend/e2e/results/panel-reads.json`. Run it before pushing panel or read changes.

The hooks it uses: `data-wc-panel`, `data-wc-panel-toggle`, `data-wc-collapsed`,
`data-wc-panel-error` (CollapsiblePanel), `data-wc-tab` (TabsRenderer),
`data-wc="line-cards"`, `data-wc-subpanel` (LineCardRenderer). Keep them when changing those.
