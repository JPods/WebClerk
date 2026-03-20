# Session Restart Notes — Saved-Search / Query Editor Feature

Last session: March 17, 2026.

---

## Status Check When Restarting

1. **Full build validation** — run `pnpm build` (or `pnpm dev`) from `React2025/` and fix any errors. All changes this session were validated with editor diagnostics only, not a full Vite build.

2. **Which models still need preset wiring** — presets are currently wired in these list pages:
   - `order`, `invoice`, `proposal`, `purchase`, `requisition`, `workorder`, `action`
   - Let us know if additional models need the toolbar bookmark / preset dropdown added.

3. **Real-use feedback** — if you run the app and exercise the saved-search editor or toolbar presets before restarting, note any rough edges. Alice note system is live so report issues with `#alice` if needed.

---

## What Was Completed This Session

| Area | Detail |
|------|--------|
| Keyword-first search contract | r25 normalizes `search`/`q` → `keyword`; wc3 accepts all three |
| wc3 saved-search runtime | `request_keyword`, `request_filters`, `relative_period` in `wcapi/get` |
| Preset listing endpoint | `GET /wcapi/search-presets/` |
| Standard preset seed | `python manage.py seed_search_presets` (21 presets, DEV DB) |
| r25 preset helpers | `getSearchPresets`, `buildSearchPresetParams`, `runSearchPreset` in `src/api/wcapi.ts` |
| Toolbar preset dropdown | `SearchPresetDropdown.tsx` with Refresh, New Search, Manage Searches, per-preset Edit |
| Preset summaries | Human-readable summary lines in dropdown (period, keyword, filters, ordering) |
| Saved-search editor | `SettingDetail.tsx` transformed into structured editor for `purpose=search` |
| Schema-aware parent model | Dropdown driven from `/wcapi/model_name/list/` |
| Schema-aware field pickers | `search_fields`, `filters.field`, `request_filters.field` use model metadata dropdowns |
| Date-only relative period field | Filtered to `DateField`/`DateTimeField` only |
| Type-aware filter value inputs | Boolean → dropdown, DateField → date input, DateTimeField → datetime-local, Numeric → number |
| Type-aware lookup options | Text/date/boolean/numeric each show only valid lookup operators |
| Alice agents | `.github/agents/Alice.agent.md` created in both `React2025/` and `webClerk3/` |
| Alice handoff notes | DEV DB Setting #200 (pending) and #201 (log) recorded |

---

## Immediate Next Steps

### 1. Schema-aware Ordering Control  
File: `React2025/src/apps/core/models/setting/pages/SettingDetail.tsx`  
Currently the `ordering` field is a plain text input (`-dt_created`). Replace with:
- A field selector dropdown driven by model schema (same source as filter field picker).
- A direction toggle (asc / desc) that prepends `-` on save.

### 2. Custom / Manual Field Fallback  
File: `React2025/src/apps/core/models/setting/pages/SettingDetail.tsx`  
Some wc3 fields are derived, annotated, or not exposed in model metadata. Add a small "Use custom field name" escape hatch to each row editor so users can type an arbitrary field name when the schema dropdown doesn't cover it.

### 3. Active Preset Indicator  
Files: `SearchPresetDropdown.tsx`, affected list pages  
After a saved search is applied from the toolbar, show which preset is currently active — e.g. a label or highlight on the bookmark button, or a chip in the search bar area. Clearing the search should deactivate the indicator.

### 4. pnpm Build Validation  
Run `pnpm build` from `React2025/` and resolve any TypeScript/bundle errors before  continuing new features.

---

## Key File Locations

### React2025 (r25)
| File | Purpose |
|------|---------|
| `src/api/wcapi.ts` | `getSearchPresets`, `runSearchPreset`, `getModelDetail`, `getModelNames` |
| `src/components/common/ButtonToolbar.tsx` | Shared list toolbar — includes `SearchPresetDropdown` |
| `src/components/common/SearchPresetDropdown.tsx` | Preset dropdown UI with summaries, refresh, edit, create |
| `src/apps/core/models/setting/pages/SettingDetail.tsx` | Saved-search editor (schema-aware) |
| `src/apps/core/models/setting/pages/SettingList.tsx` | Preset management list |
| `.github/agents/Alice.agent.md` | Alice agent definition for r25 |

### webClerk3 (wc3)
| File | Purpose |
|------|---------|
| `apps/core/views/wcapi.py` | Saved-search resolution, preset listing, request param mapping |
| `apps/core/management/commands/seed_search_presets.py` | Standard preset seed command |
| `apps/ai_assistant/services/alice_notes.py` | Alice note creation / reporting |
| `readmes/topics/architecture/keyword-denormalization-and-search.md` | Search architecture doc |
| `.github/agents/Alice.agent.md` | Alice agent definition for wc3 |

---

## Alice Support Handoff

Alice notes were created in the wc3 DEV database (March 17 2026):
- **Pending #200** — `action_required` — "Support users on saved-search editor and preset workflow"
- **Log #201** — `config_change` — "Saved-search UX and query-editor support shipped"

To review open items: `GET /wcapi/ai/report/?category=pending&parent_model=setting`
