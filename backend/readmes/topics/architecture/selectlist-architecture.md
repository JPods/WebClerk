# Select List Architecture

**Created:** 2026-08-18
**Status:** Active

## What It Is

Every dropdown, radio group, and status picker in WC3 draws from a select list — an array of `{value, label}` pairs stored in a Setting record's `config.selectlists`. Each model's Setting owns its own select lists. There is no centralized registry — the SelectListBrowser provides the consolidated view.

## Canonical Structure

```json
// Setting: wc-model-order (purpose: wc:model, parent_model: order)
{
  "config": {
    "selectlists": {
      "status": [
        { "value": "draft", "label": "Draft" },
        { "value": "open", "label": "Open" },
        { "value": "in_progress", "label": "In Progress" },
        { "value": "completed", "label": "Completed" },
        { "value": "cancelled", "label": "Cancelled" },
        { "value": "void", "label": "Void" }
      ],
      "price_level": [
        { "value": "retail", "label": "Retail" },
        { "value": "wholesale", "label": "Wholesale" },
        { "value": "distributor", "label": "Distributor" },
        { "value": "employee", "label": "Employee" }
      ]
    }
  }
}
```

### Rules

1. **Path:** `config.selectlists.<field_name>` — always
2. **Shape:** `[{value: string, label: string}]` — no extra fields (legacy had `sequence`, `alternate` — dropped)
3. **Ownership:** Each select list lives in the Setting that governs its model (`wc-model-order` for order fields, `company-profile` for company-wide lists)
4. **No centralization:** ida-114 (legacy admin lists) has been emptied and distributed
5. **Field name is the key:** `selectlists.status` means "the status field's options"

## Where Select Lists Live

| Setting pattern | Purpose | Example |
|----------------|---------|---------|
| `wc-model-<model>` | Model-specific field options | `wc-model-order` → status, price_level, fob |
| `company-profile` | Company-wide lists shared across models | hold, need, job_type, priority |
| `wc:field_access` (DEV-*) | RBAC + field behaviors per model | May contain legacy options — migrate to selectlists |

## How the UI Reads Select Lists

```typescript
// React: fetch select list for a field
const { getRecords } = await import('@/api/wcapi');
const res = await getRecords('setting', { ida: `wc-model-${modelName}` });
const setting = res?.results?.[0];
const options = setting?.config?.selectlists?.[fieldName] || [];
```

## SelectListBrowser — Consolidated View

**Route:** `/selectlists`

**Backend:** `GET /wcapi/selectlists/` — scans all active Settings, returns flat index of every select list found.

**Left pane:** Sortable list — Field | IDA | Name | Model | Purpose | # (count) | × (shared count)

**Right pane:** Selected row's options editable at top (Save in header). Below: sibling panels for same-field lists in other Settings (expandable, editable).

**Purpose:** See all select lists in one place. Notice overlaps (status appears in 6 models). Harmonize choices across models. Alice scans this data for pattern recognition.

## Scanner Priority

The backend scanner reads select lists in this order, skipping duplicates:

1. `config.selectlists.<field>` — **canonical** (preferred)
2. `config.behaviors.<field>.options` — legacy (wc:model)
3. `config.field_behaviors.<field>.options` — legacy (wc:field_access)
4. `config.lists.<name>.choices` — legacy (wc:admin, ida-114)
5. `config.select_lists.<name>.options` — legacy (wc:company_profile)

If a field exists in `selectlists`, the legacy paths are skipped for that field.

## Migration History

| Date | What |
|------|------|
| Pre-2026 | ida-114 held all select lists (116 arrays, legacy DMS) |
| 2026-08-18 | `config.selectlists` standardized across all 48 Settings |
| 2026-08-18 | ida-114 emptied — 63 lists distributed to model Settings |
| 2026-08-18 | SelectListBrowser tool page built at `/selectlists` |

## Alice Integration

Alice should:
- Watch for new select lists added to model Settings
- Flag when the same field name has different options across models (e.g., `status` in order vs invoice)
- Recommend harmonization when overlapping lists diverge
- Track option usage: which values are actually used in records vs. defined but never chosen

## Files

| File | What |
|------|------|
| `apps/core/views/selectlist_view.py` | Backend scanner + API endpoint |
| `apps/core/urls.py` | Route registration |
| `React2025/src/pages/tools/SelectListBrowser.tsx` | Frontend tool page |
| `React2025/src/routes/Routes.ts` | Route `/selectlists` |
| `React2025/src/routes/protectedRoutesConfig.tsx` | Route registration |
