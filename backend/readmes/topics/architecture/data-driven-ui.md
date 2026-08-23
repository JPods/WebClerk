# Data-Driven UI

**Domain:** datadrivenui.com
**Date:** 2026-08-03 (archive date) through 2026-08-06 (documentation)
**Terms updated:** 2026-08-18 — canonical layout names established (list, detail, form, column)
**Principle:** The data defines the interface. The program bends to the user's perception. The trellis serves the rose.
**Schema:** `db-layout-schema.md` — the canonical layout schema definition.

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
| New model cost | ~400 lines of custom .tsx | 0 lines (add a form layout) | 100% |

## How It Works

### Three Rendering Paths

Every model uses exactly one rendering path:

| Path | Renderer | When to use |
|------|----------|-------------|
| **form** | DynamicDetail + FieldRow + Design Mode | User-facing business forms (App mode) |
| **detail** | GroupedDetailFields + BehaviorField | Admin/config, all fields in groups (Admin mode) |
| **custom** | Custom React component (.tsx) | Complex interaction (drag, timeline, real-time) |

Every model also gets **list** (DataBrowser grid) and **detail** (admin field grid) automatically. The **form** path is what makes a model feel like a business application. The **custom** path is reserved for interaction that JSON can't express.

### The Layout Format

Layouts live in `config.layout` on `wc:model` Setting records. See `db-layout-schema.md` for the full schema. Four paired layout types:

| Type | What it stores |
|------|---------------|
| `layout.list` | Grid columns, widths, sort — scanning many records |
| `layout.detail` | All fields, one record, collapsible groups — Admin mode |
| `layout.form` | Curated business form — cards, tabs, lines — App mode |
| `layout.column` | Panel grid inside a detail view |

### The Rendering Stack

```
Setting (config.layout)        ← JSON layout definition, syncable, per-user overridable
    ↓
useDataBrowser hook            ← loads Setting, resolves active layouts, computes field specs
    ↓
DataBrowser.tsx                ← left panel (list), right panel (detail or form)
    ↓ (Admin mode)                              ↓ (App mode)
GroupedDetailFields            ← detail layout   DynamicDetail / *DetailJson  ← form layout
    ↓                                           ↓
FieldGroupSection              ← collapsible     Cards + Lines + Tabs
    ↓                                           ↓
BehaviorField                  ← field-level rendering based on field_behaviors
    ↓
Widget Registry (20 widgets)   ← text, select, date, currency, lookup, json-tree, geo, etc.
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

All layout types participate:

| Layout type | What the user built |
|-------------|---------------------|
| **List** | Column selection, order, widths — how to scan records |
| **Detail** | Field arrangement, groups, visibility — how to inspect a record |
| **Form** | Cards, tabs, lines, edit rules — how to do business with a record |

A user who builds a great order entry form and a great order list can submit both. They're separate named layouts, separate library entries, independently adoptable.

### Transport

Layouts move through the existing sync infrastructure:
- **Submit:** Layout Setting → Bundle → Connection → WC_HQ
- **Check out:** WC_HQ → Bundle → Connection → local Setting
- **Track:** Adoption count, creator attribution, and credit stored at WC_HQ
- No separate upload mechanism. No new API. The sync protocol handles it.

## Open Items

1. **Pending models** — work_order, receipt, requisition, payment transactions still need form layouts.
2. **Print templates** — layout-driven print is built; template library needs population.
3. **Layout library UI at WC_HQ** — browse, preview, install flow. Alice curation logic.
4. **Creator credit accounting** — threshold for cash payout, subscription credit rules.
