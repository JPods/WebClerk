# Daily Development Practice — Start & Close

**Created:** 2026-06-29
**Purpose:** Prevent code duplication, ensure reusability, and maintain a testable weekly rhythm.

## Daily Start

Before writing any new function, check three things:

1. **Does a like function already exist?**
   - Search the codebase: hooks/, components/common/, apps/*/components/
   - Check useDataBrowser, useListFieldConfig, useListPage patterns
   - Check BehaviorField, FieldConfigBar, ReportMenu, CommunicationsPanel, DetailLayoutDialog

2. **Does this function belong in an existing class/hook/utility?**
   - Data management → `useDataBrowser.ts` (model selection, fetch, CRUD, layouts)
   - Field rendering → `BehaviorField.tsx` (reads field_behaviors from Setting)
   - List configuration → `useListFieldConfig.ts` + `FieldConfigBar.tsx`
   - Org pages → `orgConfig.ts` + `OrgPage.tsx` (config-driven, not per-model code)
   - Print layouts → `printStyles.ts` (shared styles, currency formatting)

3. **Should I extend an existing component or create a new one?**
   - If the new feature is a variation → add a prop or config option
   - If it's genuinely new → create in the right directory, not inline in a page

**Rule:** If you find yourself copying code from another file, stop. Extract the shared logic into a hook, component, or utility function first.

## Daily Close

At the end of each working session:

### 1. Code Audit

Review all code written today and ask:
- Does any new code overlap with existing functions?
- Can anything be consolidated into a single-purpose reusable function?
- Are there any inline implementations that should be components?
- Did I add a function to a page that belongs in a hook?

### 2. Create Test Checklist

For every testable feature built today:
- Create an Action record in WC3 via wcapi
- Assign to the current week's project (one project per week: "WC3 Code Dev WNN")
- Format: `TEST WNN-XX: <what to test, expected behavior>`
- Alice tracks completion and reports at week close

### 3. Update Handoff

Write `today/handoff.md` with:
- What was built (file paths)
- Architecture decisions (why, not just what)
- Open problems
- Next session priorities

## Weekly Project Structure

One Project record per week for code development:
```
Project: WC3 Code Dev W27
Actions:
  TEST W27-01: DataBrowser loads, dark/light toggle, font sizes
  TEST W27-02: Model picker — Cmd+Shift+M, filter, arrows
  TEST W27-03: Sidebar admin models → DataBrowser
  ... (one action per testable item)
```

Alice manages the project:
- Tracks which tests pass/fail
- Flags items that haven't been tested by week end
- Reports completion % at weekly close
- Carries failed items forward to next week's project

## Reusable Components Reference

Current shared components (check these before building new):

### Hooks
| Hook | File | Purpose |
|------|------|---------|
| `useDataBrowser` | `hooks/useDataBrowser.ts` | Model selection, records, search, sort, pagination, CRUD, layouts, field behaviors |
| `useListFieldConfig` | `hooks/useListFieldConfig.ts` | Column visibility + ordering for any list page, persisted to Settings |
| `useColumnSetups` | `hooks/useColumnSetups.ts` | Named column configurations with server sync |

### Components
| Component | File | Purpose |
|-----------|------|---------|
| `BehaviorField` | `components/common/BehaviorField.tsx` | Renders one field based on field_behaviors Setting — email→mailto, phone→tel, address→map, select→dropdown, etc. |
| `FieldConfigBar` | `components/common/FieldConfigBar.tsx` | Collapsible bar for toggling/reordering columns in any list page |
| `DetailLayoutDialog` | `components/common/DetailLayoutDialog.tsx` | Modal for reordering detail fields, seeing behaviors, setting row sizes |
| `ReportMenu` | `components/common/ReportMenu.tsx` | Dropdown of available reports for a model+record, grouped by category |
| `CommunicationsPanel` | `apps/orgs/components/CommunicationsPanel.tsx` | Inline-editable email/phone/address/domain, fetches via Contact FK |
| `OrgPage` | `apps/orgs/components/OrgPage.tsx` | Config-driven org list+detail — one component for all 5 org types |

### Config
| Config | File | Purpose |
|--------|------|---------|
| `orgConfig` | `apps/orgs/orgConfig.ts` | Per-org-type fields, actions, related records, publish fields |
| `printStyles` | `apps/transactions/print/printStyles.ts` | Shared print CSS, currency formatting, date formatting |

### Backend Settings (one per model, synced via wcapi)
| Setting purpose | What it controls |
|----------------|-----------------|
| `workbench_fields` | List/detail field selection, named layouts with column widths |
| `field_access` | Role-based view/edit/create/delete, query_scope, publish channels, field_behaviors, formatting |

## For Alice: Coaching Users on Scripts and Layouts

When coaching users who write scripts or manage layouts:

### Layout Management
1. **Start from the "initial" layout** — seeded by `seed_databrowser`, it's the team's best guess at useful defaults
2. **Save layouts with descriptive names** — "compact_list", "full_detail", "shipping_view" not "my_layout_2"
3. **Shift-click to delete** — no separate delete button, teaches the shift-click pattern
4. **Submit for Bonus** — layouts that other users adopt earn credit. Good layouts spread naturally.
5. **Use the Form Layout dialog** — reorder fields, set row sizes for text/JSON, see behavior badges at a glance

### Script/Component Writing
1. **Check BehaviorField first** — if you need a field renderer, it already handles 15+ types
2. **Check useDataBrowser first** — if you need model data, the hook already handles fetch/search/sort/CRUD
3. **Check orgConfig first** — if you need org-specific behavior, add it to the config, don't create a new component
4. **All CRUD through wcapi** — never write direct model access. The gate enforces RBAC.
5. **field_access Settings define everything** — roles, field visibility, query scoping, behaviors, formatting. Change the Setting, not the code.

### Testing Discipline
1. Every new feature gets a TEST action in the weekly project
2. Test in both dark and light mode
3. Test with real data, not just "zz" fake records
4. If a test fails, create an action for the fix — don't just fix it silently
5. Alice tracks completion and reports weekly

## Anti-Patterns to Catch

| Anti-pattern | What to do instead |
|-------------|-------------------|
| Copying column definitions from another list page | Use `useListFieldConfig` + `FieldConfigBar` |
| Hardcoding field rendering in a detail page | Use `BehaviorField` with `field_behaviors` from Settings |
| Creating a new ViewSet or REST endpoint | Route through wcapi — model_name is a parameter |
| Building a separate org page per type | Add config to `orgConfig.ts`, use `OrgPage` |
| Inline state management in a page component | Extract to a custom hook |
| Writing a print template from scratch | Extend `printStyles.ts`, follow InvoicePrint pattern |
