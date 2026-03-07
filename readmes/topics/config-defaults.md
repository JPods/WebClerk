# Config — Defaults by Table

> **Last updated:** 2026-03-07  
> **Location:** `src/config/`

---

## Overview

The `src/config/` module is r25's centralized default-value system.
It defines what field values a new record starts with, organized by
model (table) and by field type.

Static defaults ship with the build. At runtime, admin overrides
fetched from wc3 (`configSlice`) are merged on top, and changes
made in the r25 settings UI are synced back.

---

## File Index

| File | Purpose |
|------|---------|
| `modelDefaults.ts` | Per-model (per-table) default field values |
| `fieldDefaults.ts` | Cross-model field-level rules (datetime fallback, string defaults, JSON envelope shapes) |
| `selectLists.ts` | Typed picklist / select-option definitions |
| `index.ts` | Barrel re-export — import from `@/config` |

**Hook:**

| File | Purpose |
|------|---------|
| `src/hooks/useTransactionDefaults.ts` | React hook wrapping `modelDefaults` + store overrides for transaction forms |

---

## 1. Model Defaults (`modelDefaults.ts`)

Each entry in `MODEL_DEFAULTS` maps a model key to a label and a
`defaults` record applied when creating a new record of that type.

### Current entries

| Model Key | Label | Default Fields |
|-----------|-------|----------------|
| `order` | Sales Order | `terms`, `due_date_period`, `price_level`, `priority`, `status` |
| `invoice` | Invoice | `terms`, `due_date_period`, `price_level`, `priority`, `status` |
| `proposal` | Proposal | `terms`, `due_date_period`, `price_level`, `priority`, `status` |
| `purchase` | Purchase Order | `terms`, `due_date_period`, `price_level`, `priority`, `status` |
| `requisition` | Requisition | `terms`, `priority`, `status` |
| `work_order` | Work Order | `terms`, `priority`, `status` |
| `customer` | Customer | `terms`, `price_level`, `status` |
| `vendor` | Vendor | `terms`, `price_level`, `status` |
| `contact` | Contact | `status` |
| `item` | Item | `status`, `price_level` |

### Accessors

```ts
import { getModelDefaults, getModelDefault } from '@/config';

getModelDefaults('order');            // → { terms: 'On Order', ... }
getModelDefault('order', 'terms');    // → 'On Order'
modelKeysWithDefaults();              // → ['order', 'invoice', ...]
```

### Runtime override flow

```
modelDefaults.ts (static)
        ↓  merge
configSlice (wc3 overrides fetched on startup)
        ↓  merge
useTransactionDefaults(modelKey)  →  { terms, due_date_period, price_level, priority }
```

Admins can edit overrides in the r25 settings UI; changes sync back
to wc3 via `useAppConfig().syncToBackend()`.

---

## 2. Field Defaults (`fieldDefaults.ts`)

Cross-model rules that apply regardless of which table is being created.

### Datetime fallback

Any field prefixed `dt_` that is `null`, `undefined`, or `0` is
displayed as "now" via `applyDtFallback()`. The stored value is
**not** mutated — only the displayed value is substituted.

For record creation, `stampDtIfEmpty()` / `applyDtDefaults()` stamp
the actual value with `Date.now()`.

### String defaults

Fields in `STRING_DEFAULT_FIELDS` (`name`, `title`, `description`,
`ida`, etc.) default to `""` rather than `null`.

### JSON envelope defaults

`applyEnvelopeDefaults()` seeds missing JSON clusters:

| Envelope | Default Shape |
|----------|---------------|
| `metadata` | `{}` |
| `refs` | `{ keywords, tags, links, categories, related_ids }` |
| `prefs` | `{ userdefined: {} }` |
| `comments` | `{ public, process, partner, notes }` |
| `actions` | `{}` |

### Core record defaults

`coreRecordDefaults()` returns identity + timestamp fields for a
brand-new record:

```ts
{ id: null, uuid: null, ida: '', dt_created: now, dt_modified: now,
  version: 1, is_active: true, health_rating: 0 }
```

---

## 3. Select Lists (`selectLists.ts`)

Typed picklist definitions. Each list has a `key`, `label`, `options`
array, and an `editable` flag.

- **Static** (`editable: false`) — ship with the build, never change.
- **Dynamic** (`editable: true`) — can be overridden from wc3 setting
  records and synced back on save.

---

## 4. Integration Status

| Integration Point | Status |
|-------------------|--------|
| `useTransactionDefaults` hook | Wired — delegates to `modelDefaults` + store |
| Detail page consumption | Ready — not yet imported in most pages |
| `applyDtDefaults` / `applyEnvelopeDefaults` | Ready — exported from `@/config` |
| wc3 config sync (`configSlice`) | Designed — merges overrides at runtime |

---

## 5. wc3 Counterpart

wc3's canonical defaults live in the model layer itself:

| wc3 File | Defaults |
|----------|----------|
| `base_line_model.py` | `default_quantity()`, `default_cost()`, `default_price()`, `default_item()`, `default_physical()` |
| `base_transaction_model.py` | `default_tax()` |
| `common/models.py` | `default_metadata()`, `default_refs()`, `default_prefs()` |

r25's `fieldDefaults.ts` and `modelDefaults.ts` mirror these shapes
on the frontend so new-record creation produces JSON that passes
wc3 normalization without data loss.

---

## Related Documents

- [django-model-fields.md](../django-model-fields.md) — wc3 field definitions by table
- [wc3_r25_alignment.md](../wc3_r25_alignment.md) — wc3 ↔ r25 schema alignment
- [typescript_model_alignment.md](../typescript_model_alignment.md) — TS interface alignment guide
- [transactions-totals.md](../../webClerk3/readmes/topics/transactions/transactions-totals.md) — Quantity / cost / price defaults and normalization
