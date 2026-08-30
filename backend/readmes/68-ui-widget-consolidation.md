# UI Widget Consolidation — Remaining Items

**Created:** 2026-08-12
**Status:** Complete — all 4 items resolved (2026-08-12)
**Active codebase:** `/Users/williamjames/Documents/CommerceExpert/React2025/` — all `src/` paths below are relative to that project root.

## Context

Session 2026-08-12 established the master funnel pattern:
- `formatField(value, type)` — single entry point for all display formatting
- `formatDt(value, mode, field)` — canonical date formatter (local display, UTC storage)
- `.db-*` CSS variables — single theme system
- `dd_card:base` Setting — single config for all dashboard cards

All four items resolved:
- Items 2 (DropDown) and 3 (dateUtils) were already done in React2025 — neither file exists
- Item 1 (BehaviorField delegation) completed — BehaviorField is now a thin dispatcher to renderField()
- Item 4 (inline styles) resolved by Item 1 — all styling via .db-* CSS classes

## Item 1: BehaviorField → Field Widget Delegation

**What:** BehaviorField (495 lines, 76 inline styles) reimplements all 18 field types
that already exist as widget components in `components/fields/`. It should dispatch
to those widgets instead of duplicating.

**Why it matters:** Two parallel renderers for the same behavior. BehaviorField uses
inline styles; field widgets use `.db-*` CSS classes. Bug fixes in one don't propagate
to the other.

**Files:**
- `src/components/common/BehaviorField.tsx` — refactor to dispatch to widget registry
- `src/components/fields/index.tsx` — `WIDGET_REGISTRY` already maps type → component
- `src/components/fields/BaseField.tsx` — wrapper with label + CSS classes

**Approach:**
1. Map BehaviorField's `behType` values to WIDGET_REGISTRY keys
2. For each type, replace the inline JSX with `renderField()` from fields/index
3. Pass theme as CSS variables (already on parent `.db-root`) instead of inline style objects
4. Test each type in DataBrowser detail pane after migration
5. Delete the inline implementations one type at a time

**Risk:** High — BehaviorField is the DataBrowser detail pane renderer. Test each type.

**Effort:** Full session

## Item 2: DropDown.tsx → Select Migration

**What:** `components/form/input/DropDown.tsx` is used in exactly 2 places in
`SummaryCard.tsx`. Migrate those to the standard `Select` component and delete DropDown.

**Files:**
- `src/components/form/input/DropDown.tsx` — delete after migration
- `src/apps/transactions/components/SummaryCard.tsx` — lines 282, 385
- `src/components/wrapper.ts` — remove DropDown export

**Effort:** 15 minutes

## Item 3: dateUtils.ts Deprecation

**What:** `src/utils/dateUtils.ts` is now superseded by `fieldFormatters.ts` which has
the same functions (`formatDt`, `normalizeEpochMs`, `formatDtInput`, `parseDtInput`)
plus the master `formatField()`. Redirect all imports.

**Files:**
- `src/utils/dateUtils.ts` — add deprecation comment, re-export from fieldFormatters
- Any file importing from dateUtils → change to fieldFormatters

**Check imports:**
```bash
grep -r "from.*dateUtils" src/ --include="*.ts" --include="*.tsx"
```

**Effort:** 20 minutes

## Item 4: BehaviorField Inline Styles → CSS Classes

**What:** If Item 1 is deferred, at minimum convert BehaviorField's 76 inline style
blocks to use `.db-*` CSS classes from `fields.css`. This makes it theme-consistent
even without full widget delegation.

**Note:** This is automatically resolved if Item 1 is completed. Only do this as a
standalone fix if Item 1 is deferred to a later session.

**Effort:** 1 hour (standalone) or 0 (if Item 1 done)

## Priority Order

1. Item 2 (DropDown) — 15 min, safe, immediate cleanup
2. Item 3 (dateUtils) — 20 min, safe, eliminates confusion about which file to import
3. Item 1 (BehaviorField delegation) — full session, high impact, resolves Item 4
4. Item 4 (inline styles) — only if Item 1 deferred
