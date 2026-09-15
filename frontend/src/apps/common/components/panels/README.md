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
- "+ add" → inline type-ahead search with debounce
- "×" per row → removes link, saves immediately
- Click row → opens in new floating window (never navigates current view)
- storageKey: `panel:{parentModel}:{linkedModel}` — each context gets its own column config

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

## Base Component: DbColumns

Every panel renders through `DbColumns` — the single source of truth for all tabular displays.

```tsx
<DbColumns<T>
  storageKey="panel:order:contacts"
  columns={columnDefs}
  data={records}
  rowKey={(r) => r.id}
  sectionLabel="Contacts"
  sectionIcon="👤"
  onAdd={() => handleAdd()}
  defaultCollapsed={true}
  compact
/>
```

DbColumns provides:
- Section header with collapse ▶/▼, count badge, "+ add" button
- Column headers with hamburger (FaSlidersH) → FieldOrderDialog
- Column persistence via `useListFieldConfig` (three-tier inheritance)
- Row rendering with selection highlighting
- Custom row rendering via `renderRow` prop
- Empty state message
- Children slot (e.g., inline search form)

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

### 5. New panels use DbColumns

Any new panel component must use `DbColumns` as its base. No custom table rendering. This ensures consistent column config, hamburger, and behavior across all panels.

---

## File Inventory

### Core infrastructure

| File | What |
|------|------|
| `DbColumns.tsx` | Base list component — all panels inherit from this |
| `PanelTable.tsx` | Re-export: `DbColumns as PanelTable` |
| `LinkedRecordsPanel.tsx` | Universal any-model-to-any-model linking panel |
| `ContactPanel.tsx` | Specialized contact panel with purpose/role |
| `getModelDetailPath.ts` | Model → detail route + window size mapping |
| `index.ts` | Barrel exports |
| `types.ts` | Shared types |
| `usePermissions.ts` | Role-based access hook |
| `documentUpload.ts` | Upload utilities |
| `qaUtils.ts` | Q&A helpers |

### Entity panels (specialized behavior beyond LinkedRecordsPanel)

| File | Why it's separate from LinkedRecordsPanel |
|------|------------------------------------------|
| `ActionsPanel.tsx` | Kanban columns, inline status updates, embedded task creation |
| `CommentsPanel.tsx` | Four-tab comment editor (Public/Process/Partner/Notes) |
| `DocumentsPanel.tsx` | File upload, preview, download, virus scan |
| `FinancialsPanel.tsx` | Margin calculation, aging summary, credit display |
| `LinkagesPanel.tsx` | Transaction flow visualization (Proposal→Order→Invoice→Payment) |
| `PaymentPanel.tsx` | Payment-specific actions (apply, refund) |
| `SerialPanel.tsx` | Serial lifecycle tracking |
| `ShippingPanel.tsx` | Carrier, tracking, freight |

These exist because they have domain-specific behavior that a generic linked-records list can't provide. They should still use `DbColumns` internally.

### Admin panels

| File | Visible to |
|------|-----------|
| `MetadataPanel.tsx` | admin — `.metadata` JSON editor |
| `RefsPanel.tsx` | admin — `.refs` JSON viewer |
| `PrefsPanel.tsx` | admin — `.prefs` JSON editor |
| `RawDataPanel.tsx` | admin — raw JSON viewer |
| `HistoryPanel.tsx` | admin — record history |

---

## Django Model Alignment

All panels read from `BaseModel` JSONB fields:

| Field | Panels |
|-------|--------|
| `.refs.links.contact` | ContactPanel |
| `.refs.links.{model}` | LinkedRecordsPanel (self-discovering) |
| `.refs.links.document` | LinkedRecordsPanel or DocumentsPanel |
| `.comments` | CommentsPanel |
| `.metadata` | MetadataPanel |
| `.prefs` | PrefsPanel |
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
// Universal panel
import { LinkedRecordsPanel } from '@/apps/common/components/panels';

// Specialized panels
import { ContactPanel } from '@/apps/common/components/panels';
import { ActionsPanel } from '@/apps/common/components/panels';
import { CommentsPanel } from '@/apps/common/components/panels';
import { DocumentsPanel } from '@/apps/common/components/panels';

// Base component (for building new panels)
import { DbColumns } from '@/apps/common/components/panels';
import type { DbColumnDef } from '@/apps/common/components/panels';

// Column config hook
import { useListFieldConfig } from '@/hooks/useListFieldConfig';

// Types
import type { RefContact } from '@/apps/common/components/panels';
```
