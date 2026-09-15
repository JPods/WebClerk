# WC2 Salvage Session — 2026-08-08

## What We Did

Analyzed 182 WC_ methods from WC2's 4D codebase. Bill assessed each pattern
against WC3. Three items became deliverables. Five more emerged during the work.

## Deliverables

### 1. Alice's Denormalize Stack
**Files:** `common/signals.py`, `apps/core/services/alice_denormalize.py`, `apps/sync/services/pending_processor.py`

One permanent Pending record (`alice.denormalize.stack`) that never closes.
`changes` JSON accumulates `{model, id}` pairs on every BaseModel save.
Processor pops 25/cycle, refreshes `refs.keywords` + propagates `refs.links`
snapshots to related records. Uses `select_for_update(skip_locked=True)`.

Replaces WC2's inline `RecordToObject` balance calculations.

### 2. RESTful Range Queries
**Files:** `apps/core/views/range_query_view.py`, `apps/core/urls.py`

`/wcapi/order/dt_created/2026-01-01/2026-01-31/` → converts path segments
to `__gte`/`__lte` filters, delegates to existing `WCAPIGetView`.

### 3. Three-Tier Search Architecture
**Files:** `common/schemas/envelopes.py`, `apps/core/views/wcapi.py`, `apps/core/views/save_search_view.py`, `apps/core/urls.py`

| Tier | Storage | Scope |
|------|---------|-------|
| Personal | `UserProfile.prefs.search[]` | User's favorites |
| Shared | Report (category=list, output_type=screen) | Role-visible |
| Delivered | Report (output_type=export/email) | Scheduled |

`SavedSearch` Pydantic schema in `envelopes.py`. `_resolve_saved_search()`
checks Report first, Setting fallback. POST `/wcapi/save-search/` creates either.

Setting `purpose='search'` is now legacy — searches graduate to Report records.

### 4. PostgreSQL Full-Text Search
**Files:** `common/search_utils.py`, `apps/core/migrations/0033_enable_fts_extensions.py`

`build_fragment_query()` now uses `SearchVector` + `SearchQuery` + `SearchRank`
for ranked results. Stemming, relevance ranking. `pg_trgm` + `unaccent` extensions
enabled for typo-tolerant fuzzy matching via `trigram_search()`.

Zero schema changes — FTS runs at query time on existing text fields.
`refs.keywords` stays for JSON/tag search coverage.

### 5. DocSection Component
**Files:** `React2025/src/pages/admin/AliceDashboard.tsx`

Reusable collapsible section that lazy-loads Document records by `ida` on expand.
Help content lives in Document records, not hardcoded JSX.

Seven sections: HELP-SEARCH, HELP-REPORTS, HELP-IMPORT, HELP-MCP, HELP-EXTEND,
HELP-AGENTS, HELP-WCHQ-SYNC.

### 6. WCHQ ida Prefix Convention
**Files:** `seed_model_definitions.py` (replaced `seed_all_schema_maps.py`), `seed_connections.py`, `seed_template_reports.py`

Records from WCHQ get `ida` prefix `wchq-*`. 80 schema_map Settings updated.
Full convention docs: `readmes/topics/sync/wchq-ida-convention.md`

### 7. Leftshoe Updates
**Files:** `scripts/leftshoe-mcp.py`, `readmes/leftshoe.md`

Future Claude sessions must report team-memory file creation and Allie/Alice
connectivity as first message. Fire-and-forget protocol for Allie/Alice calls.

## TFTS Principles

1. **Get it done first, then refine.** Built searches in Setting, recognized they
   belong in Report. The act of building reveals the right abstraction.

2. **Before adding a field, check if a convention on an existing field works.**
   `wchq-` prefix on `ida` beats `is_wchq` boolean — carries meaning, not just state.

3. **Point and move.** Allie and Alice are async — fire requests, don't block.
   Inclusion, not synchronization.

## WC2 Patterns Assessed

| WC2 Pattern | Bill's Assessment |
|---|---|
| Service/RMA | Handled by `refs.keywords` denormalization |
| CallReports | Replaced by Action records |
| KeyTags | `refs.tags` (user) + `refs.keywords` (denormalized) |
| contractDetail | `conditions_id` + `conditions_description` |
| Balance calculations | Alice's denormalize stack (built this session) |
| TallyMasterCall | Report records with payload + authority |
| Delete rule | Django `is_deleted` |
| Between queries | RESTful range query (built this session) |
