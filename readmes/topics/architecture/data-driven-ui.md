# Data-Driven UI

**Domain:** datadrivenui.com
**Date:** 2026-08-03 (archive date) through 2026-08-06 (documentation)
**Principle:** The data defines the interface. The program bends to the user's perception. The trellis serves the rose.
**Xref:** Duplicate maintained at `~/Allie/readmes/data-driven-ui.md` — update both when either changes.

---

## What Happened

In one week, 45,091 lines of hand-coded React detail pages were replaced by ~1,759 lines of JSON-driven rendering. One component — `DynamicDetail` — reads a layout definition (JSON stored as a Setting) and renders any model's detail form. No per-model code required.

## The Numbers

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Detail page code | 45,091 lines (59 files) | 1,759 lines (6 files) | 96% |
| ContactDetail | 4,114 lines | 325 lines | 92% |
| ItemDetail | 2,968 lines | 291 lines | 90% |
| CommPanel | 1,704 lines | 65 lines | 96% |
| TransactionDetailBase | 3,404 lines | 373 lines (8 components) | 89% |
| New model cost | ~400 lines of custom .tsx | 0 lines (add a ui.json layout) | 100% |

## How It Works

### Three UI Paths

Every model uses exactly one rendering path:

| Path | Renderer | When to use |
|------|----------|-------------|
| **ui.json** | DynamicDetail + FieldRow + Design Mode | User-facing business forms |
| **db.json** | databrowser (db.list + db.detail) | Admin/config, structured data |
| **ui.tsx** | Custom React component | Complex interaction (drag, timeline, real-time) |

### The Layout Format

A layout is a JSON object stored as a Setting record. It defines rows of fields:

```json
{
  "rows": [
    { "fields": ["action"], "cols": 1 },
    { "fields": ["assigned_to", "status"], "cols": 2 },
    { "fields": ["priority", "difficulty", "percent_complete"], "cols": 3 },
    { "fields": ["dt_start", "dt_deadline", "dt_completed"], "cols": 3 }
  ]
}
```

### The Rendering Stack

```
Setting (detail_layout)     ← JSON layout definition, syncable, per-user overridable
    ↓
DynamicDetail (455 lines)   ← reads layout, renders form, handles arrange mode
    ↓
BehaviorField               ← field-level rendering based on field_behaviors Setting
    ↓
Widget Registry (10 widgets) ← text, select, date, number, json-tree, lookup, etc.
```

### Design Mode

Users toggle into Design Mode to visually edit layouts — drag rows, add/remove fields, change column counts. Changes save back to the Setting record. No code changes, no deployment.

### Settings Scope Hierarchy

Layouts resolve through four levels:

```
user → role → org → system
```

A user can override the system layout for their own view. An org can override for all its users. The system layout is the default.

## The Architecture Shift

### Before: Code-per-model

Each model had its own detail page — a .tsx file with hardcoded field lists, custom layouts, model-specific logic mixed with rendering logic. Adding a new model meant writing ~400 lines of boilerplate. Changing a field order required a code change, a build, and a deployment.

### After: Data-per-model

Each model has a layout definition — a JSON object that says which fields go where. One component renders all of them. Adding a new model means adding a Setting record with its layout JSON. Changing field order means editing the layout in Design Mode — no code, no build, no deployment.

### Why This Matters

1. **Velocity** — new models get detail pages for free
2. **User control** — non-developers can customize their own layouts
3. **Syncability** — layouts are Settings, Settings sync between instances
4. **Consistency** — one renderer means one set of behaviors, one dark mode implementation, one print mode
5. **Maintainability** — bug fixes in DynamicDetail fix every model at once

## The Archive

All replaced code lives in `React2025/src/archive/replaced-2026-08-03/`. This is not deleted — it is learning history. The archive contains:

- 59 files, 45,091 lines total
- 13 detail pages for core models (Contact, Customer, Order, Org, etc.)
- 44 detail pages for db-json models (GL, Invoice, Serial, etc.)
- 2 transaction components (TransactionDetailBase, TransactionToolbar)

The archive exists for research — to understand what the hand-coded pages did, what edge cases they handled, and what assumptions they encoded. It is not operational code.

### Key Archived Files

| File | Lines | Replaced by |
|------|-------|-------------|
| ContactDetail.tsx | 4,114 | ContactDetailJson.tsx (325) |
| ContactDetail2.tsx | 3,095 | ContactDetailJson.tsx (325) |
| ContactDetail3.tsx | 3,110 | ContactDetailJson.tsx (325) |
| ItemDetail.tsx | 2,968 | ItemDetailJson.tsx (291) |
| TransactionDetailBase.tsx | 3,404 | TransactionDetail.tsx (373) |
| CommunicationsPanel.tsx | 1,704 | CommPanel.tsx (65) |
| CustomerDetail.tsx | 1,530 | OrgDetail.json.tsx |
| VendorDetail.tsx | 1,514 | OrgDetail.json.tsx |
| OrderDetail.tsx | 1,176 | TransactionDetail.tsx (373) |
| OrgDetail.tsx | 1,208 | OrgDetail.json.tsx |
| 44 db-json-models/ | 15,618 | databrowser db.detail |

## Lineage

This approach has roots in Bill James's 2002 book on Desktop Hosting (Wiley). The core idea: stop building message-based interfaces ("fill out this form"). Build published-based interfaces — the system publishes what you need based on who you are, what you're doing, and what the data says. Data-Driven UI is that idea implemented 24 years later, with JSON layouts, a widget registry, and a Settings hierarchy that lets every user see the interface that fits their work.

## Layout Library — Share, Credit, Check Out

Layouts are Settings. Settings sync. This means users can share their layouts with the network — and get credit for it.

### How It Works

1. **User builds a layout.** In Design Mode, a user arranges fields, adjusts columns, gets the form right for their workflow. The layout saves to their Setting record.

2. **User submits to library.** One click publishes the layout to WC_HQ via sync (Connection + Bundle — the same transport used for all WebClerk data exchange). The submission includes:
   - The layout JSON
   - The model it applies to (contact, order, invoice, etc.)
   - The creator's contact ID and installation
   - An optional description: "Wholesale order entry — ship-to prominent, payment terms visible"

3. **WC_HQ hosts the library.** Published layouts are browsable by model, by popularity, by industry tag. Alice at HQ curates — flags duplicates, groups variants, surfaces the most-adopted.

4. **Other users check out.** Browse the library, preview a layout, apply it. The layout installs as a Setting at the user's chosen scope (personal, role, org, or system default). The original is never modified — the user gets a copy they can customize further.

5. **Creators get credit.** Every layout tracks its creator. Adoption counts are visible — "This layout is used by 200 installations." Credit accrues to the creator's account:
   - Recognition: creator name and adoption count visible in the library
   - Financial: credit toward WebClerk subscription, or cash at threshold (same model as Small-Stings — the platform pays users for value created)
   - Reputation: consistent contributors build a track record that Alice surfaces when recommending layouts

### What Gets Shared

Both layout types participate:

| Layout type | Setting purpose | What the user built |
|-------------|----------------|---------------------|
| **Detail layout** (ui.json) | `detail_layout` | Form arrangement — which fields, what order, how many columns |
| **List layout** (databrowser) | `workbench_fields` | Column selection, order, widths, filters, sort |

A user who builds a great order entry form and a great order list view can submit both. They're separate Settings, separate library entries, independently adoptable.

### Why This Matters

The traditional approach: a vendor designs one layout per model, ships it, and every customer adapts. The WebClerk approach: users who do the work every day design the layouts that fit their work, the best layouts surface through adoption, and creators are rewarded.

This is the same pattern as the Pydantic schema evolution — bottom-up, not top-down. The difference: schemas are structural (Alice observes and proposes). Layouts are creative (users design and share). Both improve through the Wisdom of the Many. Both require user consent. Both reward contribution.

### Transport

Layouts move through the existing sync infrastructure:
- **Submit:** Layout Setting → Bundle → Connection → WC_HQ
- **Check out:** WC_HQ → Bundle → Connection → local Setting
- **Track:** Adoption count, creator attribution, and credit stored at WC_HQ
- No separate upload mechanism. No new API. The sync protocol handles it.

## Open Items

1. **JSON Schema validation** — layouts should validate against a formal schema at save time. Missing or misspelled field names should fail loudly, not render silently wrong.
2. **736 code standard violations** — mostly in untouched old code (no-dark-mode, missing-data-wc, raw-select). These resolve naturally as old pages are replaced.
3. **Pending models** — work_order, receipt, requisition, payment transactions still need ui.json layouts.
4. **Print templates** — layout-driven print is built; template library needs population.
5. **Layout library UI at WC_HQ** — browse, preview, install flow. Alice curation logic.
6. **Creator credit accounting** — threshold for cash payout, subscription credit rules.
