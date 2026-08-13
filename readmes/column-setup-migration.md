# ColumnSetupDialog → FieldOrderDialog Migration

**Created:** 2026-08-12
**Status:** Open — 6 consumers to migrate
**Rule:** One source of truth. FieldOrderDialog is the one. Delete the deprecated version when done.

## What Exists

**FieldOrderDialog** (`components/common/FieldOrderDialog.tsx`) — the replacement.
Used by DataBrowser. Supports list + detail modes, field behaviors, row sizes,
saved layouts with load/delete, CSS classes (fo-* prefix, no inline styles).

**ColumnSetupDialog_DEPRECATED** (`components/common/ColumnSetupDialog_DEPRECATED.tsx`) —
855 lines, inline styles, marked deprecated. Still works, still has 6 active consumers.

**ColumnSetupDialog** (`components/common/ColumnSetupDialog.tsx`) — 8-line wrapper
that re-exports the deprecated version. Delete this too.

## The 6 Consumers

| Consumer | File | What it configures |
|----------|------|--------------------|
| ButtonToolbar | `components/common/ButtonToolbar.tsx` | Column setup for any list view toolbar |
| DocumentsPanel | `apps/*/components/DocumentsPanel.tsx` | Document list columns |
| PaymentPanel | `apps/transactions/components/PaymentPanel.tsx` | Payment list columns |
| ContactPanel | `apps/core/components/ContactPanel.tsx` | Contact list columns |
| ActionsPanel | `apps/core/components/ActionsPanel.tsx` | Action list columns |
| PanelTable | `components/common/PanelTable.tsx` | Generic panel table columns |

## The Props Mismatch

The two dialogs have fundamentally different data models. This is not a rename —
each consumer needs its data plumbing reworked.

### Old (ColumnSetupDialog_DEPRECATED)

```typescript
// Data comes from useColumnSetups hook
columnMetas: ColumnMeta[]              // { key, label } objects
config: ColumnSetupEntry               // bundles order, visibility, widths, sort, jsonb
onSave: (config: ColumnSetupEntry) => void
onPreview?: (config: ColumnSetupEntry) => void
onSaveNamed?: (name, config) => void
namedSetups?: Array<{ name, config }>
columnSetupsApi?: any                  // upload/download (ButtonToolbar only)
```

### New (FieldOrderDialog)

```typescript
// Data is destructured — separate arrays/records
mode: 'list' | 'detail'               // required, no old equivalent
allFields: string[]                    // plain strings, not ColumnMeta objects
visibleFields: string[]                // replaces config.visibility
fieldBehaviors: Record<string, any>    // no old equivalent
colWidths?: Record<string, number>     // separate from config
rowSizes?: Record<string, number>      // detail mode only
savedLayouts: SavedLayout[]            // different shape from namedSetups
activeLayoutName: string | null
onApply: (fields, rowSizes, colWidths) => void  // different signature
onSaveLayout: (name, fields?, widths?) => void
onLoadLayout: (layout: SavedLayout) => void
onDeleteLayout: (name: string) => void
```

### Key Differences

1. **ColumnMeta → string[]**: Old uses `{ key, label }` objects. New uses plain field
   name strings. Labels come from fieldBehaviors.
2. **ColumnSetupEntry → separate props**: Old bundles everything in one config object.
   New destructures into visibleFields, colWidths, rowSizes.
3. **useColumnSetups hook**: Consumers use this hook for state. Either adapt the hook
   to produce FieldOrderDialog-shaped data, or replace it per consumer.
4. **onPreview / columnSetupsApi**: ButtonToolbar uses these for live preview and
   import/export. FieldOrderDialog doesn't have these yet — may need to add them
   or handle at the consumer level.
5. **mode prop**: FieldOrderDialog requires 'list' or 'detail'. All 6 consumers
   are list mode.

## Migration Strategy

One consumer at a time. Test after each. Order by complexity (simplest first):

1. **PanelTable** — generic, probably simplest wiring
2. **DocumentsPanel** — single-purpose panel
3. **ActionsPanel** — single-purpose panel
4. **ContactPanel** — single-purpose panel
5. **PaymentPanel** — single-purpose panel
6. **ButtonToolbar** — most complex (preview, import/export)

### For each consumer:

1. Read the consumer to understand how it calls ColumnSetupDialog
2. Read how it uses useColumnSetups to get/set config
3. Build an adapter or replace the hook call to produce FieldOrderDialog props:
   - `allFields` from columnMetas keys
   - `visibleFields` from config.visibility (true entries)
   - `colWidths` from config.widths
   - `onApply` wraps the old onSave, reassembling into whatever state the consumer needs
   - `savedLayouts` from namedSetups (reshape)
4. Replace the import and JSX
5. Verify `tsc --noEmit` passes
6. Test in browser — column dialog opens, fields reorder, widths save, layouts load

### After all 6 are migrated:

1. Delete `ColumnSetupDialog_DEPRECATED.tsx` (855 lines)
2. Delete `ColumnSetupDialog.tsx` (8-line wrapper)
3. Check if `useColumnSetups` hook is still used anywhere — delete if not
4. Run full build
