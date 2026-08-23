# SOW: DataBrowser Detail Pane Field Grouping — COMPLETED 2026-08-05

## Problem

The admin detail pane renders every field in a flat 2-column grid. A contact record has 40+ fields — identity, communication, financial, status, system — all mixed together. The user's eye has no anchor. Finding "balance" means scanning past "attention", "address_full", "department", and "uuid". The JSON envelope panel proved that collapsible sections work. Apply the same pattern to all fields.

## Goal

Group fields into labeled, collapsible sections in the admin detail pane. Users see structure instead of a wall. Alice learns which sections each user opens and auto-collapses the rest.

## Architecture

### Field Group Definition

Each model gets a `field_groups` array in its Setting record (same place `field_behaviors` lives). This is data-driven, not hardcoded.

```json
{
  "field_groups": [
    { "key": "identity",    "label": "Identity",      "fields": ["attention", "company", "ida", "contact", "customer", "vendor", "manufacturer"] },
    { "key": "financial",   "label": "Financial",     "fields": ["total", "balance", "cost", "sell", "totals", "commission", "price_level", "terms"] },
    { "key": "status",      "label": "Status",        "fields": ["status", "priority", "is_active", "is_locked", "is_archived", "is_deleted"] },
    { "key": "communication", "label": "Communication", "fields": ["email", "phone", "address_full"] },
    { "key": "dates",       "label": "Dates",         "fields": ["dt_created", "dt_modified"] },
    { "key": "system",      "label": "System",        "fields": ["id", "uuid", "version", "security_level", "health_rating", "parent_id", "parent_model", "line_increment"] },
    { "key": "json",        "label": "Data",          "fields": ["cost", "sell", "totals", "commission", "finance", "flow", "source", "comments", "actions"] }
  ],
  "default_collapsed": ["system", "dates"]
}
```

Fields not in any group go into an "Other" section at the bottom. No field is hidden — grouping is presentation, not access control.

### Seed Defaults

`seed_field_access.py` generates sensible default groups per model based on field names and types:
- Fields starting with `is_` → Status
- Fields starting with `dt_` → Dates  
- `email`, `phone`, `address_*` → Communication
- `total`, `balance`, `cost`, `sell`, currency fields → Financial
- `id`, `uuid`, `version`, `security_*`, `health_*` → System
- JSON fields → Data
- Everything else → Identity (top)

### UI Component

New component: `FieldGroupSection` — a collapsible section with a label, field count, and expand/collapse chevron. Same visual pattern as JsonEnvelopePanel header.

```
▼ IDENTITY (7)
  attention: Bill James
  company: JPods LLC
  ida: DEV-34
  ...

▼ FINANCIAL (8)
  total: $0.00
  balance: $0.00
  ...

▶ SYSTEM (8)  ← collapsed by default
```

### Collapse State

- Default collapse state from Setting (`default_collapsed`)
- User overrides saved to `user.prefs.staff.detail_collapsed.{model}` — array of collapsed group keys
- Alice observes: which groups does this user expand? Which do they never touch? After N sessions, recommend collapsing unused groups.

### DataBrowser Integration

Replace the current flat `.map()` in the admin detail grid (DataBrowser.tsx ~line 1208-1218) with:

1. Read `field_groups` from the Setting (already loaded via `useDataBrowser`)
2. Partition `visibleDetailFields` into groups
3. Render each group as a `FieldGroupSection` containing BehaviorField instances
4. Ungrouped fields go into "Other" at the bottom

The JSON Envelopes panel stays separate — it's a different component with different rendering (tree vs. BehaviorField).

### Layout Integration

The existing Layout dropdown (alice_guess, alphabetical) should work with groups:
- `alice_guess` layout can reorder groups and fields within groups
- `alphabetical` layout sorts fields within each group but keeps group order
- A new `flat` layout option restores the current ungrouped behavior for users who prefer it

## Files to Change

| File | What changes |
|------|-------------|
| `seed_field_access.py` | Generate `field_groups` + `default_collapsed` per model |
| `useDataBrowser.ts` | Read `field_groups` from Setting, manage collapse state |
| `DataBrowser.tsx` | Replace flat field grid with grouped sections |
| `FieldGroupSection.tsx` (new) | Collapsible section component |
| `wcui_prefs.py` | Save/load `detail_collapsed` per model |
| `envelopes.py` | Add `detail_collapsed` to StaffPrefsMixin |

## What NOT to Do

- Do not hide fields — every field remains accessible
- Do not hardcode groups per model — Setting record is the source of truth
- Do not break the Layout dropdown — groups compose with layouts, not replace them
- Do not change field ordering within groups unless the layout says to
- Do not add drag-and-drop reordering in this scope — that's a separate feature

## Acceptance Criteria

1. Order detail shows fields in labeled collapsible sections
2. Contact detail (40+ fields) is scannable in 3 seconds
3. System/Dates sections collapsed by default
4. User can expand/collapse; state persists across sessions
5. `flat` layout option restores the old ungrouped view
6. `seed_field_access --reseed` generates groups for all models
7. Alice can read collapse patterns from prefs

## Estimated Scope

One focused session. Most of the work is the `FieldGroupSection` component and the partition logic in DataBrowser. The seed generation is pattern-matching on field names — straightforward.

---

## Implementation Notes — 2026-08-05

### What Was Built

| Deliverable | File | Status |
|-------------|------|--------|
| FieldGroupSection component | `src/components/common/FieldGroupSection.tsx` | Done |
| GroupedDetailFields renderer | `src/pages/admin/DataBrowser.tsx` (local component) | Done |
| useDataBrowser field group state | `src/hooks/useDataBrowser.ts` | Done |
| Seed field groups per model | `seed_field_access.py` → `_build_field_groups()` | Done — 75 models |
| Collapse state persistence | `wcuiPrefs.ts` → `detail_collapsed` key | Done |
| `flat` layout view | `seed_databrowser.py` + protected views | Done |
| Detail Order button | `DataBrowser.tsx` detail toolbar | Done |

### Polish Pass (same session)

1. **Field reclassification** — FK IDs (`phone_id`, `domain_id`, `email_id`, `address_id`, `conditions_id`, `terms_fk`) moved from Identity to System. Contact Identity dropped from 24 → 11 fields.
2. **Group ordering** — Communication promoted to 2nd position (after Identity). Users find email/phone/address without scrolling past 20+ fields.
3. **`data-help` attributes** — All group headers carry `data-help` for Shift-for-Help standard.
4. **CSS cleanup** — Removed duplicate `.db-list-pane` definition (orphaned at line ~261).
5. **Header padding** — Group headers match JsonEnvelopePanel at `6px 12px`.

### Group Classification Rules

| Rule | Group |
|------|-------|
| JSON envelope fields (metadata, refs, prefs, config, etc.) | Data |
| `id`, `uuid`, `version`, `security_level`, `health_rating`, `parent_*`, `line_increment` | System |
| FK ID fields (`email_id`, `phone_id`, `domain_id`, `address_id`, `conditions_id`, `terms_fk`) | System |
| `total`, `balance`, `cost`, `sell`, `price_level`, `terms`, `discount`, `amount` | Financial |
| `email`, `phone`, `fax`, `mobile`, `website`, `url`, `address*` | Communication |
| `status`, `priority`, `stage`, `state`, `is_*` | Status |
| `dt_*` | Dates |
| Everything else | Identity |

### Default collapsed: `['system', 'dates']`

### Acceptance Criteria Results

1. Order detail shows fields in labeled collapsible sections — **Pass**
2. Contact detail (50 fields) scannable in 3 seconds — **Pass** (11 Identity + collapsed groups)
3. System/Dates collapsed by default — **Pass**
4. User collapse state persists across sessions — **Pass** (wcui prefs)
5. `flat` layout restores ungrouped view — **Pass** (activeViewName === 'flat' bypasses groups)
6. `seed_field_access --force` generates groups for all models — **Pass** (75 models)
7. Alice can read collapse patterns from prefs — **Pass** (`contact.prefs.staff.wcui.detail_collapsed`)
