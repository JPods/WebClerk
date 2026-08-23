# Search & Smart Queries — Implementation Plan

> Universal search bar with fragment matching, keyword denormalization, and
> user-defined saved queries — all guided by Alice.

---

## Problem Statement

R25 list pages need search that matches what wc2 users already expect:

1. **Comma-separated fragments** — `acm, 102` finds records where any
   searchable field *begins with* one of the fragments.
2. **`@` contains modifier** — `@west` finds records that *contain* "west"
   anywhere (not just prefix).
3. **Keyword searching** — fragments also match against `refs.keywords`, a
   denormalized bag of strings pulled from the record and its related objects.
4. **Saved / complex queries** — "open orders > 30 days old in Western
   territory" should be definable without writing code.
5. **Alice-guided denorm rules** — users can ask Alice to adjust which
   fields (contact name, phone, email, org address, etc.) are denormalized
   into `refs.keywords` for a given model.

The existing `list-search-feature.md` documents a basic in-memory/DB search.
This plan supersedes and extends it with wc2-parity fragment semantics, the `@`
modifier, and saved queries.

---

## Existing Infrastructure Audit

> Comprehensive audit completed March 2026. Items marked ✅ are **already
> implemented** and should be reused, not rebuilt.

### R25 — Frontend

| Component | Status | Detail | Location |
|-----------|--------|--------|----------|
| **Search input (3-column)** | ✅ Built | `searchDraft` with 200 ms debounce → `setListSearch()` → `AdminWorkspaceProvider` → `wcapiDataSource.list()` | `RecordListColumn.tsx` L161–176 |
| **`parseSearchTerms()`** | ✅ Built | Splits on comma, trims, lowercases. AND logic. **No `@` modifier.** | `AdvancedDataTable.tsx` L21–27 |
| **`rowMatchesAllTerms()`** | ✅ Built | In-memory filter: all scalar fields + `refs.keywords` (string or array). Uses `includes()` (contains), not `startsWith()`. | `AdvancedDataTable.tsx` L615–646 |
| **Database search flow** | ✅ Built | `AdminWorkspaceProvider` → `wcapiDataSource.buildListParams()` → `getRecords(model, {search, q})` → `GET /wcapi/get/` | `wcapiDataSource.ts` L59–68 |
| **AdvancedDataTable DB toggle** | ✅ Built | `enableDatabaseSearch`, `searchDatabase`, `onDatabaseSearch` props. "Query DB" checkbox. | `AdvancedDataTable.tsx` props |
| **In-memory filter duplication** | ⚠️ Debt | `rowMatchesAllTerms()` logic duplicated in 7+ `*ListMob.tsx` files (Customer, Vendor, Contact, Email, Phone, Address, Domain) | various `*ListMob.tsx` |
| **`queryRecords()` SDK** | ❌ Missing | No POST to `/wcapi/query/`. Only GET via `getRecords()`. | `wcapi.ts` |
| **Saved Query UI** | ❌ Missing | No `SavedQuerySelector`, `QueryBuilder`, or related state | — |
| **OrgSearchDialog** | ✅ Built | Modal keyword search with 300 ms debounce, paginated, multi-org-type. Uses `getRecords(model, {search, limit:20})`. **No fragment support.** | `OrgSearchDialog.tsx` |

### wc3 — Backend

| Component | Status | Detail | Location |
|-----------|--------|--------|----------|
| **`WCAPIGetView._apply_search()`** | ✅ Built | Single `search` string → Q with `icontains` across `search_fields` (registry or fallback). **No fragment parsing, no `istartswith`.** | `apps/core/views/wcapi.py` L432–468 |
| **`PrefixAndSearchView`** | ✅ Built | Multi-term AND with `istartswith` + `refs__keywords__icontains`. Settings-aware keyword fields (`purpose='keywords'`). **Only used by `RequisitionSearchView` — not wired into wcapi GET.** | `common/search_mixins.py` L8–165 |
| **Registry `search_fields`** | ✅ Built | `ModelConfig.search_fields` per model. Fallback auto-detects Char/Text/Email/URL fields. | `apps/core/utils/registry.py` |
| **Keyword builder** | ✅ Built | `build_keywords_for_record()` — processes `self_fields` + `related_keywords` from config. Extracts, dedupes, filters ignore words. | `apps/core/services/keywords.py` L65+ |
| **Keyword requirements loader** | ✅ Built | Reads Settings with `purpose='refs_setup'` (or `'ref_seup'` — typo fallback). Cached 3600 s. **No Settings records exist in DB yet.** | `apps/core/constants/keyword_requirements.py` |
| **`update_keywords` command** | ✅ Built | `python manage.py update_keywords [--model X] [--batch-size N] [--limit N] [--dry-run]`. Iterates models with `update_keywords()` method. | `apps/core/management/commands/update_keywords.py` |
| **Org link denormalization** | ✅ Built | `denormalize_org_links()` — snapshots customer/vendor/manufacturer onto transaction `refs.links`. **Also extracts keywords** from org fields into `refs.keywords`. | `apps/transactions/services/denormalize_org_links.py` |
| **Link templates** | ✅ Built | `link_defaults.py` — per-role `keyword_fields` and `link_template` dicts. Customer: `company, display_name, ida, email, phone`. | `apps/core/services/link_defaults.py` L20+ |
| **Denorm registry** | ✅ Built | `DENORM_REGISTRY` — 60+ models, controls which fields appear in `refs.links` snapshots. | `common/denorm_registry.py` |
| **`?kw=` keyword param** | ❌ Missing | Documented in `wcapi-queries.md` but not wired into `WCAPIGetView`. `PrefixAndSearchView` does keyword search but is a separate view. | — |
| **`/wcapi/query/` endpoint** | ❌ Missing | DSL with `where[]` designed in readme. No view, no URL route. | only in `readmes/topics/api/wcapi-queries.md` |
| **Saved queries** | ❌ Missing | No model, no endpoint, no CRUD. Settings infrastructure available but no `purpose='saved_query'` records. | only in `readmes/topics/api/wcapi-saved-sets.md` |
| **Alice keyword/query tools** | ❌ Missing | No `tools/` directory under `ai_assistant`. No keyword_config or query-building tools. | — |

### Key Findings

1. **`PrefixAndSearchView` is the hidden gem.** It already implements the
   exact wc2-style search we want: multi-term AND, `istartswith` per field,
   `refs__keywords__icontains`, and dynamic keyword fields from Settings.
   **But it's only used by `RequisitionSearchView`** — not by the main
   `WCAPIGetView` that R25 calls.

2. **`WCAPIGetView._apply_search()` is too simple.** It passes the entire
   search string as one `icontains` — no comma splitting, no prefix matching.
   This is why R25 search doesn't behave like wc2.

3. **Keyword infrastructure is complete but unconfigured.** The builder,
   loader, caching, and management command all exist. What's missing is
   the actual `purpose='refs_setup'` Settings in the database to tell the
   builder which fields to extract per model.

4. **Org denormalization already extracts keywords.** When
   `denormalize_org_links()` runs on a transaction save, it already pulls
   org keywords into `refs.keywords`. This covers the "search orders by
   customer name" case — **if the keyword requirements are seeded**.

5. **In-memory filtering uses `includes()` not `startsWith()`.** The R25
   `rowMatchesAllTerms()` always does substring matching. To match wc2
   behavior, this needs to be updated to use `startsWith()` by default
   and `includes()` only for `@`-prefixed terms.

6. **Search logic is duplicated** across 7+ `*ListMob.tsx` files. Phase 1
   should extract this into the shared `searchFragments.ts` utility.

---

## Architecture

### Fragment Search Flow

```
User types: "acm, @west, 102"
          ↓
  R25 parseFragments()
          ↓
  ┌─────────────────────────────────────────┐
  │  Fragment[]                              │
  │  [                                       │
  │    { value: "acm",  mode: "startswith" },│
  │    { value: "west", mode: "contains"   },│
  │    { value: "102",  mode: "startswith" } │
  │  ]                                       │
  └──────────┬──────────────────────────────┘
             │
    ┌────────┴────────┐
    │  In-memory mode  │  (selection search — existing records in table)
    │  Filter rows     │  ← fast, no API call
    │  in JS           │
    └─────────────────┘
             │
    ┌────────┴────────┐
    │  Database mode   │  (Query DB toggled on)
    │  GET /wcapi/get/ │  ← sends structured params
    │  ?fragments=...  │
    └────────┬────────┘
             ↓
  wc3: parse fragments, build Q objects
    - "startswith" fragments → Q(field__istartswith=val)
    - "contains" fragments  → Q(field__icontains=val)
    - Also search refs__keywords (JSONField) for matches
    - All fragments combined with AND
             ↓
  Return matching records
```

### Saved Query Flow

```
User opens Saved Queries panel → picks "Open Orders > 30 days (Western)"
          ↓
  R25 loads Setting where purpose=saved_query, model_name=order
          ↓
  Sends POST /wcapi/query/  { saved: "id_or_name" }
          ↓
  wc3 loads stored DSL:
    {
      "where": [
        { "field": "status",     "op": "eq",  "value": "open" },
        { "field": "dt_created", "op": "lte", "value": "$today_minus_30" },
        { "field": "territory",  "op": "eq",  "value": "Western" }
      ],
      "order_by": ["-dt_created"]
    }
          ↓
  Executes as ORM query, returns results
```

---

## Phases

### Phase 1 — Fragment Search (wc2 parity) ✅ COMPLETE

**Goal:** The search bar on every ListPage supports comma-separated fragments
with `@` contains modifier. Works in both selection (in-memory) and database modes.

**Reuse:** `PrefixAndSearchView.build_query()` already implements the correct
ORM logic. We need to (a) port its fragment+keyword behavior into
`WCAPIGetView._apply_search()`, (b) add `@` contains support, and (c) update
the R25 in-memory filter.

#### 1A. R25 — Fragment Parser + Matcher (new shared utility)

**File:** `src/utils/searchFragments.ts` (new)

Replaces `parseSearchTerms()` and eliminates the duplicated logic in 7+
`*ListMob.tsx` files. Both `AdvancedDataTable` and the Mob pages import from here.

```typescript
export interface SearchFragment {
  value: string;        // lowercased, trimmed
  mode: "startswith" | "contains";
}

export function parseFragments(input: string): SearchFragment[] {
  return input
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((raw) => {
      if (raw.startsWith("@")) {
        return { value: raw.slice(1).toLowerCase(), mode: "contains" as const };
      }
      return { value: raw.toLowerCase(), mode: "startswith" as const };
    });
}
```

#### 1B. R25 — In-Memory Fragment Matching (refactor existing)

Update `AdvancedDataTable`'s `rowMatchesAllTerms()` to use `matchesFragments()`:

- For each fragment, check all scalar string fields + `refs.keywords`:
  - `startswith` → `fieldValue.toLowerCase().startsWith(frag.value)`
  - `contains` → `fieldValue.toLowerCase().includes(frag.value)`
- All fragments must match (AND across fragments; OR across fields within a fragment).

**Migration path:**
- Replace the inline `parseSearchTerms()` + `rowMatchesAllTerms()` in
  `AdvancedDataTable.tsx` with imports from `searchFragments.ts`
- Delete the duplicated logic from `CustomerListMob.tsx`, `VendorListMob.tsx`,
  `ContactListMob.tsx`, `EmailListMob.tsx`, `PhoneListMob.tsx`,
  `AddressListMob.tsx`, `DomainListMob.tsx` — import shared util instead
- Update `OrgSearchDialog` to use `parseFragments()` when sending to backend

#### 1C. wc3 — Backend Fragment Parsing (port existing mixin into wcapi)

**Existing code to reuse:** `PrefixAndSearchView.build_query()` in
`common/search_mixins.py` L141–158 already does:
- Multi-term AND with `istartswith` per field
- `refs__keywords__icontains` for keyword matching
- Dynamic keyword fields from Settings (`purpose='keywords'`)

**What to do:**

1. **Extract** `build_query()` logic from `PrefixAndSearchView` into a
   standalone function in `common/search_utils.py` (new):

   ```python
   def build_fragment_query(
       qs, search_string: str, search_fields: list[str],
       model_cls, include_refs_keywords: bool = True
   ):
       """Parse comma-separated fragments and build Q objects.
       
       Prefix `@` on a fragment → icontains (substring).
       No prefix → istartswith (prefix match, indexable).
       """
   ```

2. **Replace** `WCAPIGetView._apply_search()` (L432–468) to call
   `build_fragment_query()` instead of the current single-string
   `icontains` approach.

3. **Add `@` support** — detect `@` prefix on each fragment:
   - No `@` → `Q(**{f"{field}__istartswith": value})` per field
   - `@` prefix → `Q(**{f"{field}__icontains": value})` per field
   - Keywords always use `icontains` regardless of `@`

4. **Update `PrefixAndSearchView`** to call `build_fragment_query()` too,
   so the same logic is shared rather than duplicated.

5. **No new URL params needed.** The existing `?search=` / `?q=` param
   carries the raw comma-separated string. Backend parses it.

#### 1D. R25 — Wire Into List Pages (minimal changes)

- `RecordListColumn` and `AdvancedDataTable`: switch from `parseSearchTerms()`
  to `parseFragments()` before dispatching to in-memory filter or API call
- Database mode: send the raw search string as `?search=acm,@west,102`
  (backend parses fragments server-side)
- No UI changes to the text input itself — the `@` token is typed inline

#### 1E. Hint Text

Add placeholder text to the search input:  
`"Fragments: acm, 102  |  @west = contains"`

---

### Phase 2 — Keyword Denormalization for Search

**Goal:** `refs.keywords` on orgs and transactions includes denormalized
contact/communication/org data so fragment search finds records by contact
name, phone, email, address, etc.

**Reuse:** The keyword builder (`build_keywords_for_record()`), the keyword
requirements loader (`keyword_requirements.py`), the `update_keywords`
management command, and the org keyword extraction in
`denormalize_org_links.py` are **all already implemented**. What's missing
is the **Settings data** to configure them per model.

#### 2A. Define Keyword Denorm Targets

| Parent Model | What to Denormalize | Source |
|---|---|---|
| `customer` | contact `name_first`, `name_last`, `phone`, `email` | `refs.links.contact` → Contact → comms |
| `vendor` | contact `name_first`, `name_last`, `phone`, `email` | same |
| `manufacturer` | contact `name_first`, `name_last`, `phone`, `email` | same |
| `order` | org `display_name`, `email`, `phone`, `address_full`; contact `name_first`, `name_last`, `email`, `phone` | FK customer/vendor + `refs.links.contact` |
| `invoice` | same as order | same |
| `proposal` | same as order | same |
| `purchase` | vendor `display_name`, `email`, `phone`, `address_full`; contact fields | FK vendor + `refs.links.contact` |

#### 2B. wc3 — Seed Keyword Config Settings (data, not code)

**No new code needed.** `build_keywords_for_record()` and
`load_keyword_requirements()` already read from Settings with
`purpose='refs_setup'`. We need to **create the Setting records**.

Create via fixture or management command:

```python
# Example Setting records to create
KEYWORD_CONFIGS = [
    {
        "name": "Order Keyword Config",
        "purpose": "refs_setup",
        "parent_model": "order",
        "data": {
            "self_fields": ["ida", "reference", "status", "notes"],
            "related_keywords": {
                "customer": ["display_name", "company", "email", "phone", "address_full"],
                "contact":  ["name_first", "name_last", "email", "phone"]
            }
        }
    },
    {
        "name": "Customer Keyword Config",
        "purpose": "refs_setup",
        "parent_model": "customer",
        "data": {
            "self_fields": ["ida", "display_name", "company", "status"],
            "related_keywords": {
                "contact": ["name_first", "name_last", "email", "phone"]
            }
        }
    },
    # ... invoice, proposal, purchase, vendor, manufacturer
]
```

`build_keywords_for_record()` already supports `related_keywords` — this is
primarily a **data seeding step**, not new code.

> **Note:** Fix the typo in `keyword_requirements.py` — it queries for both
> `purpose='refs_setup'` and `purpose='ref_seup'`. Keep the typo fallback
> for any existing data but standardize new records on `'refs_setup'`.

#### 2C. wc3 — Backfill Existing Records (command already exists)

**Existing command:** `python manage.py update_keywords --model order --model customer ...`

This command already:
- Finds models with `update_keywords()` method
- Iterates in batches with `--batch-size`
- Supports `--dry-run` and `--limit`

After seeding the Settings in 2B, run the backfill:
```bash
python manage.py update_keywords --model order --model invoice --model proposal \
  --model purchase --model customer --model vendor --model manufacturer
```

#### 2D. wc3 — Auto-Refresh on Related Save

When a Contact's name/email/phone changes, or a Communication record is
updated, queue a Celery task to refresh keywords on all parent records
(orgs/transactions linked via `refs.links`). Use signals or explicit calls
in the save path. Debounce with a 5-second Celery countdown to batch
multiple related saves.

---

### Phase 3 — Alice-Guided Denorm Configuration + Query Learning

**Goal:** Users can ask Alice "add vendor phone to order search keywords"
and Alice updates the keyword config Setting for that model. Alice also
learns from search patterns to proactively help users.

#### 3A. Query Logging for Alice

Log every search to give Alice a learning dataset:

**wc3 — `SearchLog` model or lightweight Setting append:**

```python
# Option A: Dedicated table (preferred for volume)
class SearchLog(models.Model):
    user        = ForeignKey(settings.AUTH_USER_MODEL, null=True)
    model_name  = CharField(max_length=100, db_index=True)
    raw_query   = CharField(max_length=500)      # "acm, @west"
    fragments   = JSONField(default=list)         # parsed fragments
    result_count = IntegerField(default=0)
    source      = CharField(max_length=20)        # "wcapi_get" | "query_dsl" | "saved"
    dt_created  = BigIntegerField()               # timestamp ms

    class Meta:
        indexes = [
            models.Index(fields=['model_name', 'dt_created']),
        ]
```

**Logged at:** end of `WCAPIGetView._apply_search()` and `QueryView.post()`.
Fire-and-forget via `transaction.on_commit()` + Celery task to avoid
slowing search responses.

**What Alice does with the logs:**

| Pattern | Alice Action |
|---|---|
| Repeated fragment across users | Suggest saving as a named query |
| Zero-result searches | Recommend keyword config changes ("users search for `@territory` but order keywords don't include territory") |
| High-frequency model searches | Prioritize keyword denorm and index optimization for that model |
| Natural language fragments | Suggest `@` modifier to users who seem to expect contains behavior |

**Alice tool:**
```python
def get_search_analytics(model_name: str, days: int = 30) -> dict:
    """Return search frequency, zero-result queries, common fragments."""
```

**Privacy:** Log user_id for per-user suggestions but never expose one
user's searches to another. Alice aggregates anonymously for model-level
recommendations.

#### 3B. Alice Notes — Persistent Memory Layer ✅ COMPLETE

Alice can create Setting records with `purpose = "alice_pending"` or
`purpose = "alice_log"` to build a persistent memory accessible via the
admin, wcapi, and dedicated reporting endpoints.

**Two categories:**

| Category | Purpose | Lifecycle |
|---|---|---|
| `pending` | Short-term action items (keyword gaps, zero-result flags, data quality) | `is_active=True` → resolve → `is_active=False` |
| `log` | Longer-term audit trail (searches, config changes, health checks) | Write-once, query for patterns |

**Allowed roles per category:**

| Pending roles | Log roles |
|---|---|
| `keyword_gap`, `zero_result`, `data_quality`, `config_suggestion`, `action_required` | `search`, `config_change`, `health_check`, `user_interaction`, `system` |

**Files:**

| File | What |
|---|---|
| `apps/core/choices.py` | Added `alice_pending`, `alice_log` to `SETTING_PURPOSE_CHOICES` |
| `apps/ai_assistant/services/alice_notes.py` | `create_note()`, `resolve_pending()`, `get_report()` |
| `apps/ai_assistant/views.py` | `NoteView` (POST create, PATCH resolve), `ReportView` (GET) |
| `apps/ai_assistant/urls.py` | `POST /wcapi/ai/note/`, `PATCH /wcapi/ai/note/`, `GET /wcapi/ai/report/` |
| `src/apps/support/services/aiApi.ts` | `createAliceNote()`, `resolveAliceNote()`, `getAliceReport()` |

**Backend usage from any service:**
```python
from apps.ai_assistant.services.alice_notes import create_note, get_report

create_note("pending", role="keyword_gap", parent_model="customer",
            name="Missing keyword: phone",
            details={"field": "phone", "suggestion": "add to refs_setup"})

report = get_report(category="pending", days=30, parent_model="customer")
```

**R25 usage:**
```typescript
import { createAliceNote, getAliceReport } from "@/apps/support/services/aiApi";

await createAliceNote({
  category: "log", role: "search", name: "User searched acm,@west",
  parent_model: "customer", details: { query: "acm, @west", results: 3 },
});

const report = await getAliceReport({ category: "pending", days: 7 });
```

#### 3C. Search Feedback Loop ✅ COMPLETE

Lightweight, optional UI that lets users rate search results and coach Alice
on what they expected to find. Most users will never use it — the UI only
appears while a search is active and disappears when the query clears.

**Flow:**

```
User searches → results load → "Did you find what you needed?" row appears
                                    👍  →  alice_log (search_feedback, rating=1)
                                    👎  →  alice_log (search_feedback, rating=-1)
                                         + alice_pending (keyword_gap, auto-created)
                                         + coaching input slides in:
                                           "What were you looking for?"  [Send] [Skip]
                                           → second alice_log with coaching text
```

Feedback resets automatically when the search query changes.

**Backend:**

| File | What |
|------|------|
| `apps/ai_assistant/services/alice_notes.py` | `log_search_feedback()` — creates log + auto-creates `keyword_gap` pending on negative |
| `apps/ai_assistant/views.py` | `SearchFeedbackView` — POST validates rating (1 / -1), query, parent_model |
| `apps/ai_assistant/urls.py` | `POST /wcapi/ai/search-feedback/` |
| `apps/core/choices.py` | `search_feedback` added to `LOG_ROLES` |

**Frontend:**

| File | What |
|------|------|
| `src/apps/support/services/aiApi.ts` | `submitSearchFeedback()` + `SearchFeedbackRequest` / `SearchFeedbackResponse` types |
| `src/apps/utils/3column/components/RecordListColumn.tsx` | Thumbs up/down row, coaching text input, state + handlers |

**Design choices:**

- **Intentionally minimal** — a single row of text + two emoji buttons.
  No modal, no multi-step wizard. Users who don't care never notice it.
- **Auto-reset on query change** — `feedbackSent` clears when
  `list.search` changes, so the prompt reappears naturally for new searches.
- **Coaching is optional** — negative feedback creates the `keyword_gap`
  pending even if the user clicks Skip. The coaching text just enriches it.
- **No blocking** — API call is fire-and-forget from the UI perspective.
  The user never waits for it to complete.

#### 3D. Alice Tool — `manage_keyword_config`

Add a tool/function Alice can call:

```python
# apps/ai_assistant/tools/keyword_config.py

def get_keyword_config(model_name: str) -> dict:
    """Return current refs_setup Setting for model."""

def update_keyword_config(model_name: str, self_fields: list, related_keywords: dict) -> dict:
    """Update the refs_setup Setting. Returns the new config."""
```

Expose via the existing Alice tool-use / function-calling framework.

#### 3E. Alice Prompt Enhancement

Add to Alice's system prompt (developer / general modes):

> When users ask about search or keyword configuration, use the
> `manage_keyword_config` tool. Show them the current config, explain
> what fields are indexed, and apply changes when asked. After changes,
> remind them to run `python manage.py refresh_keywords --model <model>`
> to backfill existing records.

#### 3F. R25 — Admin Keyword Config UI (optional)

A simple admin page at `/settings/keyword-config` that lists models and
their keyword extraction rules. For power users who prefer UI over Alice chat.
Lower priority — Alice chat covers this adequately.

---

### Phase 4 — Open Query DSL (Backend Implementation)

**Goal:** Implement the `POST /wcapi/query/` endpoint documented in
`wcapi-queries.md` so R25 can submit structured filter conditions.

#### 4A. wc3 — Query View

**File:** `apps/core/views/query_view.py` (new)

- Accept POST body: `{ where: [], order_by: [], limit, offset }`
- Validate `where[].field` against `__meta__.query.allow_fields` (or
  model fields + sensible defaults)
- Validate `where[].op` against allowed operators
- Build Django Q objects from conditions
- Support date macros: `$today`, `$today_minus_N`, `$month_start`, etc.
- Clamp limit to `max_rows` from registry config
- Reuse existing serialization from `WCAPIGetView`

#### 4B. wc3 — Date Macro Resolver

```python
MACROS = {
    "$today":          lambda: date.today(),
    "$today_minus_30": lambda: date.today() - timedelta(days=30),
    "$month_start":    lambda: date.today().replace(day=1),
    "$year_start":     lambda: date(date.today().year, 1, 1),
}

def resolve_value(value):
    """If value matches $today_minus_N pattern, compute date."""
    if isinstance(value, str) and value.startswith("$today_minus_"):
        days = int(value.split("_")[-1])
        return date.today() - timedelta(days=days)
    return MACROS.get(value, lambda: value)()
```

#### 4C. R25 — Query SDK Function

**File:** `src/api/wcapi.ts` (extend)

```typescript
export interface QueryCondition {
  field: string;
  op: "eq" | "ne" | "lt" | "lte" | "gt" | "gte"
    | "contains" | "icontains" | "startswith" | "istartswith"
    | "in" | "isnull";
  value: any;
}

export async function queryRecords(
  model_name: string,
  conditions: QueryCondition[],
  options?: { orderBy?: string[]; limit?: number; offset?: number; saved?: string }
) {
  const resolved = resolveModelName(model_name);
  const res = await apiClient.post<ApiEnvelope<GetListPayload>>(
    "/wcapi/query/",
    {
      model_name: resolved,
      where: conditions,
      order_by: options?.orderBy,
      limit: options?.limit,
      offset: options?.offset,
      saved: options?.saved,
    }
  );
  return res.data.data;
}
```

---

### Phase 5 — Saved Queries (Persist & Reuse)

**Goal:** Users define complex, repeating queries, save them, and re-run
them from a dropdown in the list page.

#### 5A. wc3 — Saved Query CRUD

Implement the endpoints from `wcapi-saved-sets.md`:

- `POST /wcapi/query/save/` — creates a Setting with `purpose=saved_query`
- `GET /wcapi/query/list/?model_name=order` — list saved queries for a model
- `POST /wcapi/query/` with `{ saved: "<id_or_name>" }` — run a saved query
- `DELETE /wcapi/query/<id>/` — soft-delete a saved query

Setting `data` shape:

```json
{
  "name": "Open Orders > 30 Days (Western)",
  "dsl": {
    "where": [
      { "field": "status",     "op": "eq",  "value": "open" },
      { "field": "dt_created", "op": "lte", "value": "$today_minus_30" },
      { "field": "refs__links__customer__state", "op": "eq", "value": "Western" }
    ],
    "order_by": ["-dt_created"]
  },
  "scope": { "type": "person", "value": "user_id" },
  "labels": ["aging", "territory"],
  "comment": "Weekly review of stale western orders"
}
```

#### 5B. R25 — Saved Query Selector UI

Add to the list page header (next to the search bar):

```
[🔎 acm, @west          ] ☐ Query DB   [▾ Saved Queries]
                                         ├─ Open Orders > 30 Days (Western)
                                         ├─ High-Value Proposals This Month
                                         ├─ Invoices Pending Payment
                                         ├─ ──────────────
                                         └─ + Save Current Search...
```

- Dropdown lists saved queries for the current model
- Selecting one replaces the current list results
- "Save Current Search" opens a dialog to name the current fragment
  search + any active filters as a saved query
- Badge on the dropdown shows count of available saved queries

#### 5C. R25 — Query Builder Dialog

For creating/editing saved queries beyond simple fragment searches:

- Modal with condition rows: `[field ▾] [op ▾] [value]`
- Field dropdown populated from model metadata (`getModelDetail()`)
- Op dropdown filtered to valid ops for the field type
- Date fields show date-macro suggestions (`$today_minus_30`, etc.)
- Preview button runs the query and shows result count
- Save button calls `/wcapi/query/save/`

#### 5D. Alice-Assisted Query Building

Alice can help users build queries via natural language:

> **User:** "Show me open orders over 30 days old in Western territory"  
> **Alice:** I'll create a saved query for that:
> ```json
> { "where": [
>   { "field": "status", "op": "eq", "value": "open" },
>   { "field": "dt_created", "op": "lte", "value": "$today_minus_30" },
>   { "field": "territory", "op": "eq", "value": "Western" }
> ]}
> ```
> Want me to save this as "Open Orders > 30 Days (Western)"?

Alice already has access to model metadata via the Copilot context system.
Add a `create_saved_query` tool function.

---

## Design Decisions & Opinions

### 1. `@` for Contains — Keep It

The `@` prefix from wc2 is a good user convention. It's concise, discoverable via
placeholder text, and avoids adding a separate UI toggle for match mode. Default
to `startswith` because it's far more common in day-to-day use (looking up by
account number, name prefix) and `startswith` can use database indexes.

### 2. AND Across Fragments, OR Across Fields

This matches how users actually think: "find something that matches *all* of
these hints." Each hint is tested against *all* searchable fields (OR), but
all hints must match *somewhere* on the record (AND). This is the existing
behavior in `list-search-feature.md` and should be preserved.

### 3. Keywords as the Denorm Search Layer

Rather than adding scalar search columns to every model, the `refs.keywords`
approach keeps the schema clean. Keywords are a flat list of strings extracted
from the record and its related objects. The keyword builder is already
configurable per model via Settings. This is the right abstraction.

The alternative — adding `contact_name`, `contact_email`, etc. as dedicated
columns — creates schema bloat and migration churn every time search
requirements change. Keywords avoid this.

### 4. Settings-Based Config Over Code

Keyword extraction rules live in Setting records, not hardcoded in Python.
This means:
- Alice can modify them at runtime
- Users can tune without deploys
- Different tenants could have different keyword configs (future)

### 5. Fragment Search on GET, Complex Queries on POST

Fragment search is a natural extension of the existing `?search=` GET param.
Complex/saved queries use POST because they carry structured bodies. Don't
conflate the two — they serve different user workflows:
- Fragments = quick lookup (typist at a keyboard)
- Saved queries = analytical/reporting use case

### 6. Saved Queries Scoped Per User

By default, saved queries are `scope.type=person` (private). Users can
choose to share with `role` or `job` scope. This prevents clutter while
allowing team-wide useful queries to be shared.

### 7. Date Macros Are Essential

Saved queries with hardcoded dates go stale immediately. `$today_minus_30`
makes "open orders over 30 days" perpetually current. Keep the macro set
small and well-documented.

### 8. Phase Sequencing

Fragment search (Phase 1) delivers the most immediate user value — it's the
thing wc2 users will miss most. Keyword denormalization (Phase 2) amplifies
it. Saved queries (Phases 4–5) are a separate workstream that can proceed
in parallel once the query DSL backend is built.

---

## File Inventory (New & Modified)

### New Files

| File | Project | Purpose |
|------|---------|---------|
| `src/utils/searchFragments.ts` | r25 | Fragment parser + matcher (replaces inline `parseSearchTerms`) |
| `src/components/common/SavedQuerySelector.tsx` | r25 | Dropdown for saved queries (Phase 5) |
| `src/components/common/QueryBuilderDialog.tsx` | r25 | Visual condition builder (Phase 5) |
| `common/search_utils.py` | wc3 | Shared fragment → Q builder (extracted from `PrefixAndSearchView`) |
| `apps/core/views/query_view.py` | wc3 | POST `/wcapi/query/` endpoint (Phase 4) |
| `apps/ai_assistant/services/alice_notes.py` | wc3 | Alice notes service: `create_note`, `resolve_pending`, `get_report`, `log_search_feedback` (Phase 3B–C) |
| `apps/ai_assistant/tools/keyword_config.py` | wc3 | Alice tool for keyword config (Phase 3D) |
| `apps/ai_assistant/tools/saved_queries.py` | wc3 | Alice tool for query building (Phase 5) |

### Modified Files

| File | Project | Change |
|------|---------|--------|
| `src/components/common/AdvancedDataTable.tsx` | r25 | Import `parseFragments` + `matchesFragments` from `searchFragments.ts`; remove inline `parseSearchTerms` + `rowMatchesAllTerms` |
| `src/apps/*/models/*/pages/*ListMob.tsx` (7 files) | r25 | Remove duplicated search logic; import from `searchFragments.ts` |
| `src/apps/common/components/OrgSearchDialog.tsx` | r25 | Use `parseFragments()` for search input |
| `src/apps/utils/3column/components/RecordListColumn.tsx` | r25 | Search placeholder text, feedback UI (Phase 3C), saved query dropdown (Phase 5) |
| `src/apps/support/services/aiApi.ts` | r25 | Alice notes + search feedback API client (Phase 3B–C) |
| `src/apps/utils/3column/AdminWorkspaceProvider.tsx` | r25 | Add `savedQueryId` to list state (Phase 5) |
| `src/api/wcapi.ts` | r25 | Add `queryRecords()` SDK function (Phase 4) |
| `apps/core/views/wcapi.py` | wc3 | Replace `_apply_search()` with fragment-aware logic from `search_utils.py` |
| `common/search_mixins.py` | wc3 | Refactor `build_query()` to call shared `search_utils.py` |
| `apps/core/choices.py` | wc3 | Added `alice_pending`, `alice_log` purposes (Phase 3B); `search_feedback` log role (Phase 3C) |
| `apps/ai_assistant/views.py` | wc3 | `NoteView`, `ReportView` (Phase 3B), `SearchFeedbackView` (Phase 3C) |
| `apps/ai_assistant/urls.py` | wc3 | `note/`, `report/`, `search-feedback/` routes (Phase 3B–C) |
| `apps/core/urls.py` | wc3 | Add route for `/wcapi/query/` (Phase 4) |

### Existing Files — Reused As-Is

| File | Project | Status |
|------|---------|--------|
| `apps/core/services/keywords.py` | wc3 | ✅ `build_keywords_for_record()` — no changes needed |
| `apps/core/constants/keyword_requirements.py` | wc3 | ✅ Settings loader + cache — minor typo fix only |
| `apps/core/management/commands/update_keywords.py` | wc3 | ✅ Batch keyword refresh — no changes needed |
| `apps/transactions/services/denormalize_org_links.py` | wc3 | ✅ Org snapshot + keyword extraction — no changes needed |
| `apps/core/services/link_defaults.py` | wc3 | ✅ Per-role keyword_fields config — no changes needed |
| `common/denorm_registry.py` | wc3 | ✅ 60+ model denorm configs — no changes needed |

---

## Testing Strategy

| Test | Type | Covers |
|------|------|--------|
| `parseFragments()` unit tests | vitest | `@` modifier, comma splitting, edge cases |
| `matchesFragments()` unit tests | vitest | In-memory AND/OR logic |
| Fragment API tests | pytest | Backend Q-object building, `startswith` vs `contains` |
| Keyword search tests | pytest | `refs.keywords` matching with fragments |
| Query DSL tests | pytest | Condition parsing, date macros, operator validation |
| Saved query CRUD tests | pytest | Create, list, run, delete saved queries |
| Keyword refresh tests | pytest | Management command, related-save refresh |
| Integration (E2E) | manual/playwright | Full search → results flow in R25 |

---

## Open Questions

1. **Nested JSON field querying** — should `refs__links__customer__state`
   be allowed in saved query conditions? Postgres JSONB supports it, but
   it complicates validation. Recommendation: allow it for `refs` paths only,
   validate the first key is `refs`.

2. **Full-text search index** — for large datasets, `istartswith` on
   `refs.keywords` (a JSONField list) won't use indexes well. Should we add
   a generated `tsvector` column from keywords? Phase 2 can start without
   it; monitor query performance and add if needed.

3. **Maximum fragments** — should we cap the number of comma-separated
   fragments? Suggestion: 10, matching wc2 behavior.

4. **Search history** — should R25 remember recent searches per user?
   Low priority but nice UX. Could store in localStorage or as Settings.

---

## References

- [list-search-feature.md](../list-search-feature.md) — existing search doc (superseded by Phase 1)
- [wcapi-queries.md](../../webClerk3/readmes/topics/api/wcapi-queries.md) — query DSL design
- [wcapi-saved-sets.md](../../webClerk3/readmes/topics/api/wcapi-saved-sets.md) — saved sets design
- [plan-Alice.md](../../webClerk3/readmes/topics/ai/plan-Alice.md) — Alice integration plan
- [common/denorm_registry.py](../../webClerk3/common/denorm_registry.py) — denormalization field registry
- [apps/core/services/keywords.py](../../webClerk3/apps/core/services/keywords.py) — keyword builder
