# Copilot Instructions — WebClerk3 (wc3)

These instructions govern AI-assisted development in the **WebClerk3** Django backend.
Read them fully before generating or modifying any code.

---

## 1. Project Identity

| Key | Value |
|-----|-------|
| Alias | **wc3** |
| Stack | Django 5 · Python 3.13 · PostgreSQL · Redis · Celery |
| Frontend | React2025 (**r25**) — separate repo in the same workspace |
| Legacy | 4D Sources (**wc2**) + Vue 2020 — migration targets, not active dev |
| Ports | wc3 → `localhost:8000`, r25 → `localhost:5173` |

**Legacy schema** — The full 4D/wc2 field catalog is at `readmes/topics/wc2/wc2_schema.json` (157 tables). Attach it when working on field migrations or metadata mapping.

---

## 2. Architecture at a Glance

### Composable Model Hierarchy

All models inherit from a layered mixin system in `common/models.py`:

```
CoreModel (identity + timestamps + version)
├── MetadataMixin      (historized metadata, flags)
├── RefsMixin          (keywords, tags, links — refs.links for denorm snapshots)
├── PrefsMixin         (user preferences)
├── CommentsMixin      (threaded notes)
├── ActionsMixin       (next-step tracking)
├── HealthMixin        (data quality scores)
├── KeywordsMixin      (async keyword extraction)
├── LifecycleMixin     (soft delete / archive — never hard-delete)
├── UniversalDictMixin (stable serialization)
└── AtomicJSONMixin    (partial JSON updates)
    └── BaseModel (full composition)
```

Transaction models extend `TransactionBaseModel` → `BaseModel` with totals, status, and flow fields.

### Unified API Gateway (wcapi)

All CRUD routes through **four** centralized endpoints — do **not** create per-model REST views:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wcapi/get/` | GET | Fetch records (list or single) |
| `/wcapi/save/` | POST | Create or update records |
| `/wcapi/query/` | POST | Complex queries with filters |
| `/wcapi/manage/` | POST | Administrative operations |

Models must be registered in `apps/core/services/wcapi_registry.py` to be accessible.

### Folder Structure

```
apps/
├── accounts/        # GL, ledgers, currencies, tax, terms, audits
├── communications/  # email, phone, address, domain + verification
├── core/            # contact, action, setting, template, notification, report
├── docs/            # document, linkage, tag, question_answer
├── orgs/            # OrgBase (customer/vendor/manufacturer roles)
├── products/        # item, catalog, inventory, warehouse, BOM, delivery
├── support/         # shared support utilities
├── sync/            # connections, bundles, external integrations
└── transactions/    # proposal, order, invoice, purchase, requisition, work_order + lines
```

Business logic lives in each app's `services/` package. Shared logic goes in `common/`.

---

## 3. Naming Conventions (STRICT)

### Model Names vs Table Keys

| Context | Convention | Example |
|---------|-----------|---------|
| API requests (`model_name`) | **singular** snake_case | `invoice`, `order_line` |
| Registry table keys / collections | **plural** snake_case ending in 's' | `invoices`, `order_lines` |
| Python class | PascalCase singular | `Invoice`, `OrderLine` |
| Related data buckets in responses | **plural** under `data.related` | `data.related.invoice_lines` |

### Canonical Renames (ENFORCED)

Legacy names are **banned** in new code — the rename guard script checks for violations:

| Banned Legacy Name | Canonical Name |
|-------------------|---------------|
| `sales_order` / `SalesOrder` | `order` / `Order` |
| `sales_order_line` / `SalesOrderLine` | `order_line` / `OrderLine` |
| `purchase_order` / `PurchaseOrder` | `purchase` / `Purchase` |
| `purchase_order_line` / `PurchaseOrderLine` | `purchase_line` / `PurchaseLine` |
| `location` (as model name) | `address` / `Address` |

Legitimate uses of "location" (warehouse position, DRF param, display fields) are not affected.

### General Casing

- Python: `snake_case` for variables, functions, fields; `PascalCase` for classes
- TypeScript / React: `camelCase` for variables / functions; `PascalCase` for components / types
- File naming: `{Model}Detail.tsx`, `{Model}List.tsx`, `{model}Api.ts`
- Date/time fields: prefix `dt_` (e.g., `dt_created`, `dt_modified`)
- FK columns: `{model_name}_id` format in database/API (e.g., `invoice_id`, `org_id`)

### Label Rendering Policy (STRICT)

- For admin, list, detail, and table labels: use the **exact schema field name and exact case**.
- Never title-case, capitalize, prettify, humanize, or auto-transform schema labels.
- Scalar fields must render as exact schema names (example: `dt_modified`, `invoice_id`).
- Object/JSON-derived keys must render with a leading dot and exact key name (example: `.on_hand`, `.margin_pc`, `.exact_name`).

### ForeignKey Naming — `_id_id` Prevention (CRITICAL)

Django auto-appends `_id` to the Python field name to create the DB column.
If you name a field `invoice_id = models.ForeignKey(...)`, the DB column becomes `invoice_id_id`.

| Python field name | DB column (auto) | Correct? |
|-------------------|-------------------|----------|
| `invoice` | `invoice_id` | **YES** |
| `org` | `org_id` | **YES** |
| `invoice_id` | `invoice_id_id` | **NO — BANNED** |

**Rules:**
- Name FK fields **without** the `_id` suffix: `invoice`, `term`, `org`, `gl_account`
- Django auto-creates `invoice_id` as the raw-ID accessor and DB column
- Use `db_column='invoice_id'` only when renaming an existing column (it's redundant but safe for documentation)
- In queryset filters: `Ledger.objects.filter(invoice_id=val)` is correct — this references the DB column, not the field name
- In constructors: `Ledger(invoice=obj)` (object) or `Ledger(invoice_id=pk)` (raw ID) — both correct

---

## 4. API Response Envelope (MANDATORY)

Every JSON response **must** use this envelope. Never return bare data.

```jsonc
{
  "status": "success" | "error",      // REQUIRED
  "message": "",                        // optional human-readable
  "data": { ... } | null,              // payload on success
  "error": {                            // present when status == "error"
    "code": "machine_code",            // stable snake_case identifier
    "details": { ... } | null
  },
  "meta": {                             // pagination & diagnostics
    "total": 123,
    "page_size": 50,
    "next": "?page=3",
    "previous": null
  }
}
```

Key rules:
- HTTP 2xx → `status: "success"`, `error: null`
- HTTP 4xx → `status: "fail"` for client/validation errors (never "error")
- HTTP 5xx → `status: "error"`
- Version conflicts → HTTP 412, `error.code: "version_conflict"`
- Related/nested data → always under `data.related`

Use `common/api_responses.api_response()` to construct responses.

---

## 5. JSONB Fields & Deep Merge

Models have JSONB columns for schema-less extension: `metadata`, `refs`, `prefs`, `comments`.

- **Deep merge on save** — do not overwrite entire JSONB; use `AtomicJSONMixin` helpers (`atomic_json_set`, `atomic_list_append`)
- **Size limit** — `MAX_METADATA_SIZE = 32000` (enforced in `common/models.py`)
- **Relationships** → store in `refs.links` as `{"related_model": [id1, id2, ...]}`
- **Denormalization** — `refs.links` entries are hydrated to dicts on save via `common/denorm_registry.py`; never hard-code field lists elsewhere
- **Display metadata** → persist computed labels under `metadata.display.*`

---

## 6. Transaction System

### Document Types

| Type | Direction | Lines Model | Flow |
|------|-----------|------------|------|
| Proposal | Sell | `ProposalLine` | proposal → order |
| Order | Sell | `OrderLine` | order → invoice |
| Invoice | Sell | `InvoiceLine` | terminal |
| Purchase | Buy | `PurchaseLine` | purchase → receipt |
| Work Order | Exec | `WorkOrderLine` | standalone |
| Requisition | Internal | `RequisitionLine` | requisition → purchase |

### Calculation Authority

- **Backend is authoritative** for all saved totals
- Frontend shows optimistic estimates; syncs on save
- Line changes trigger header recalc atomically
- Rounding: 2-decimal precision for currency, percentage fields

### Key Data Structures

Lines carry `quantity`, `price`, `cost`, `tax` as JSONB dicts with sub-fields (`unit`, `extended`, `discount_percent`, etc.).
Headers carry `totals` and `finance` JSONB dicts aggregated from lines.

### Line Identity — `line_number` / `line_increment`

- **`line_number`** — `IntegerField(default=0, db_index=True)` on `BaseLineCore`. A stable, non-PK line identifier assigned in increments of 10.
- **`line_increment`** — `IntegerField(default=10)` on `TransactionBaseModel`. Tracks the next value to assign.

Auto-assignment (two paths):
1. **`transaction_save.py`** — reads `header.line_increment` before the line loop; assigns to new lines with `line_number == 0`; persists the bumped counter after the loop.
2. **`BaseLineCore.save()`** fallback — if `line_number == 0` on save, reads `parent.line_increment`, assigns, bumps, and saves the parent.

R25 uses `lineKey(line, idx)` → `line.line_number ?? line.id ?? idx` for stable React state identity. Never use bare `line.id ?? idx`.

---

## 7. Testing Requirements

### Running Tests

```bash
pytest -q                        # full suite (SQLite fast path)
pytest -q -m fast                # fast subset
pytest -x                        # stop on first failure
pytest -k "test_name"            # single test by name
pytest -q -m "integration"       # integration tests (needs Postgres)
```

### Environment

- Tests auto-switch to in-memory SQLite via `PYTEST_CURRENT_TEST`
- Force Postgres: `PYTEST_FORCE_DB=1`
- Settings module: `DJANGO_SETTINGS_MODULE=webclerk3_api.settings`

### Test Conventions

- Place test files under `tests/` prefixed with `test_`
- Favor focused unit tests; integration tests only when necessary
- Always assert the response envelope contract
- Use optimistic concurrency pattern: fetch → note version → update with `If-Match` → expect 412 if stale
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.fast`
- Coverage threshold: ≥20% (`--cov-fail-under=20`)
- **Always add/adjust tests alongside code changes** before pushing

---

## 8. Code Generation Rules

When generating or modifying code, follow these rules:

### Do

- Route all data operations through wcapi endpoints — never create per-model REST views
- Use `model_name` (singular) in API calls, never table names or plurals
- Check `wcapi_registry.py` before referencing a model — it must be registered
- Use the composable mixin system — inherit from `BaseModel` or `TransactionBaseModel`
- Place business logic in `apps/{app}/services/`; shared logic in `common/`
- Use Celery for async side-effects (keyword refresh, email sends, sync)
- Use `refs.links` for cross-model relationships
- Import denorm field lists from `common.denorm_registry` — never hard-code
- Use `LifecycleMixin` soft deletes — never hard-delete records
- Store all times in UTC; use ISO 8601 in JSON; prefix date fields with `dt_`
- Return all API responses through the standard envelope
- Use `select_related` / `prefetch_related` for query optimization
- Always paginate list endpoints with `limit`/`offset`
- Include version bumps on save (optimistic concurrency)

### Don't

- Don't duplicate the `/wcapi` prefix (check `VITE_API_URL` in r25)
- Don't use legacy model names (`sales_order`, `purchase_order`, `location` as model)
- Don't store large documents in the database — save file paths instead
- Don't overwrite entire JSONB fields — use deep merge / atomic operations
- Don't bypass `model.save()` for bulk updates without scheduling a backfill
- Don't add top-level keys outside the response envelope
- Don't use UUIDs except for sync records between databases
- Don't return HTML from API endpoints (JSON only, except explicitly whitelisted pages)
- Don't create sandbox experiments without a dated cleanup note

---

## 9. Save Hooks & Transaction Save Flow

### Save Hooks

Pre/post save logic is defined in `Setting` records with `purpose: "save_pre_post"` and matching `parent_model`:

- `data.save_pre` — synchronous, runs before save (validation, normalization)
- `data.save_post` — synchronous, runs after save (logging, side-effects)
- `data.save_async` — asynchronous via Celery (email, sync, expensive operations)

This allows customization without code deployment. Check existing hooks before adding inline logic.

### Two Save Paths

| Endpoint | Handler | Pending Strategy | Used By |
|----------|---------|------------------|---------|
| `/wcapi/save/` | `save_view.py` `post()` | Per-line via `LineItemService._create_pending_for_new_line()` | Generic saves, order deactivation |
| `/wcapi/transaction/save/` | `transaction_save.py` `save_transaction_with_lines()` | **Collect-then-create** via `_create_pending_from_deltas()` | R25 transaction saves with lines |

### Transaction Save Flow — Collect-then-Create (2026-02-21)

```
POST /wcapi/transaction/save/  { model_name: "invoice", record: { lines: [...] } }
  │
  ├── Phase 1 — Atomic save (signals suppressed)
  │   ├── transaction.atomic() begins
  │   │     ├── Verify R25 calculations against WC3 math
  │   │     ├── Save header (create or update)
  │   │     ├── Read current_line_increment from header
  │   │     ├── For each dirty line:
  │   │     │     ├── Assign line_number from current_line_increment if == 0
  │   │     │     ├── Save line (create or update)
  │   │     │     ├── Set line._pending_created = True (suppresses signal)
  │   │     │     └── Collect pending delta into pending_deltas[]
  │   │     ├── Persist bumped line_increment back to header
  │   │     └── (No Pending records created yet)
  │   └── transaction.atomic() commits
  │
  ├── Phase 2 — Create Pending records from collected deltas
  │   └── _create_pending_from_deltas() — backend-authoritative:
  │         ├── Derives type from model_key (not front-end data)
  │         ├── Detects transfers from header.parent_id/parent_model
  │         ├── Stores (invoice_line_id, order_line_id) pair in each record
  │         ├── In-memory seen_pairs + DB duplicate guard
  │         └── For IN-from-order: on_in=+qty, on_so=-qty, on_hand=-qty
  │
  ├── Phase 3 — Update source lines (transfer only)
  │   └── Bumps actioned, sets remaining, marks transferred
  │
  └── Phase 4 — Single dispatch_pending_processing() call
      └── Celery applies pending deltas to Item.quantity
```

### Generic Save Flow (`/wcapi/save/`)

```
POST /wcapi/save/  { model_name: "order", record: { lines: [...] } }
  │
  ├── save_pre hooks — validation, normalization
  │
  ├── transaction.atomic() begins
  │     ├── Save parent record
  │     ├── For each line:
  │     │     ├── Set _pending_created = True
  │     │     ├── Save line record
  │     │     └── Call _create_pending_for_new_line() (one Pending per line)
  │     └── Dispatch Celery task
  │
  ├── transaction.atomic() commits
  │
  └── save_post / save_async hooks
```

### Pending Record Rules (Inventory)

- **One pending per line operation** — duplicate pairs are forbidden
- **Backend is authoritative** — pending type, transfer detection, and quantity buckets are derived server-side, not from front-end data
- **Collect-then-create** (transaction save): lines saved first with signals suppressed, then all Pending records created from the collected deltas array
- **Single dispatch** — one `dispatch_pending_processing()` call after all Pending records exist, not per-line
- The `_pending_created` flag on line instances prevents the signal safety net from duplicating
- Celery only **applies** pending deltas to `Item.quantity` fields — it does not create them
- Pending type codes: SO, PO, PP, IN, WO — mapped via `_PENDING_TYPE_MAP` in `transaction_save.py`
- For transfers (e.g. order→invoice), each Pending captures both the add and the release in one record (e.g. `on_in=+qty, on_so=-qty, on_hand=-qty`)
- `(invoice_line_id, order_line_id)` pair stored in every Pending record; duplicates blocked in-memory and at DB level

### Pending as Compensating Transactions (ARCHITECTURAL PATTERN)

The `Pending` model is used as a **compensating transaction mechanism** across the system — not just for inventory. When immediate consistency is blocked by record contention, user locks, or transient failures, a Pending record captures the intended operation as a command object that Celery retries until convergence.

**Core principle**: In the happy path the Pending is created AND marked processed in the same request cycle. It only becomes a retry command on failure. Either way it persists as an audit trail.

**When to use Pending**:
- Hot row contention (many writers to same record)
- Record locked by a user in read-write mode
- Cross-record consistency (two+ records must stay in sync)
- Transient failures (network blips, database timeouts)

**Design rules for new Pending domains**:
1. Define a `PURPOSE_*` constant for the purpose string
2. Create the Pending with full context in `data` JSON (command, not message)
3. Attempt immediate execution; mark processed on success
4. On failure, leave unprocessed for Celery to retry
5. Write an idempotent processor (running twice = same result)
6. When possible, stamp the source record with sync metadata so readers can detect drift without querying the Pending table
7. Never delete processed Pendings — they're lightweight audit records
8. One Pending per event, not per retry attempt

**Active domains**:

| Purpose | Domain | Processor |
|---------|--------|-----------|
| `inventory_line_add` | Item quantity | `pending_inventory_processor.py` |
| `inventory_qty_change` | Item quantity | `pending_inventory_processor.py` |
| `inventory_line_delete` | Item quantity | `pending_inventory_processor.py` |
| `ledger_sync` | Invoice ↔ Ledger ↔ Org balance | `ledger_sync_processor.py` |

**Long-tail risk detection**: Unprocessed Pendings older than a threshold are signals. Query `Pending.objects.filter(dt_processed=0, dt_created__lt=threshold)` to surface stuck operations, contention hotspots, and systemic issues.

**Deep-dive**: `readmes/topics/architecture/pending-compensating-transactions.md`

### Ledger Sync Pipeline (Phase 5)

Every invoice save creates a `ledger_sync` Pending and stamps `invoice.metadata.ledger`:

```
Invoice Save (Phase 5)
    │
    ├── Create/replace Ledger records from payment terms
    ├── Stamp invoice.metadata.ledger (entries + dt_sync=0)
    ├── Create Pending (purpose='ledger_sync')
    ├── Attempt update_org_balances(org)
    │       │
    │       ├── Success → stamp dt_sync=now, mark Pending processed
    │       └── Failure → both stay unprocessed for Celery
    │
    └── On total Phase 5 exception → create retry Pending with reason
```

**Self-diagnosing metadata** (`invoice.metadata.ledger`):
- `dt_sync > 0` → fully synced, no action needed
- `dt_sync = 0` → ledger records written but org balance unconfirmed
- Key absent → ledger write itself may have failed

**Files**: `ledger_balance.py` (creation), `ledger_sync_processor.py` (retry), `transaction_save.py` (Phase 5 wiring)

---

## 10. Key File Locations

| Purpose | Path |
|---------|------|
| Base models & mixins | `common/models.py` |
| Denorm field registry | `common/denorm_registry.py` |
| API response helper | `common/api_responses.py` |
| Envelope middleware | `common/middleware/` |
| Exception handlers | `common/exception_handlers.py` |
| Model registry | `apps/core/services/wcapi_registry.py` |
| WCAPI views | `apps/core/views/wcapi.py`, `apps/core/views/save_view.py` |
| Transaction save (collect-then-create) | `apps/transactions/services/transaction_save.py` |
| Transaction save view | `apps/transactions/views/wcapi.py` |
| Line item service (generic pending) | `apps/transactions/services/line_item_service.py` |
| Pending dispatch helper | `apps/products/dispatch_pending.py` |
| Ledger sync processor | `apps/accounts/services/ledger_sync_processor.py` |
| Ledger balance + on_invoice_save | `apps/accounts/services/ledger_balance.py` |
| Signal safety net | `apps/transactions/signals.py` |
| URL routing | `webclerk3_api/urls.py` |
| Settings | `webclerk3_api/settings.py` |
| Tests | `tests/` (root) and `apps/*/tests/` |
| Readmes | `readmes/` (numbered 00–09 for onboarding, topics/ for deep-dives) |
| Copilot context (committed) | `.copilot-context/` (models, fixtures, imports, errors, maps) |
| Context generator | `apps/ai_assistant/management/commands/generate_context.py` |
| AI vector store (gitignored) | `.chroma_db/` (rebuild with `index_docs`) |
| Instruction sync check | `common/checks.py` (Django system check: copilot.W001/W002) |

---

## 11. Documentation Practice

- **Readmes are essential** — update `readmes/` when architecture decisions change
- Files `00-` through `09-` are the core onboarding sequence
- Topic deep-dives go in `readmes/topics/{category}/`
- Machine-readable model data: `readmes/model-registry.json`, `readmes/model-fields.json`
- Regenerate docs with scripts in `Scripts/` (e.g., `gen_model_registry_readme.py`, `gen_readmes_toc.py`)
- Run pre-commit hooks to enforce docs layout and TOC consistency

---

## 12. Copilot Context System

The `.copilot-context/` directory contains **auto-generated, machine-readable reference files** committed to git for the whole team. These are indexed by the AI assistant (ChromaDB) and directly readable by Copilot.

### Structure

```
.copilot-context/
├── models/
│   ├── model-reference.md     ← every Django model's fields, types, relations (80 models)
│   └── model-hierarchy.md     ← CoreModel → BaseModel mixin chain overview
├── fixtures/
│   └── *.json                 ← golden API response shapes (one per model)
├── imports/
│   ├── django-imports.md      ← canonical Python import paths
│   └── react-imports.md       ← canonical TypeScript import paths
├── errors/
│   └── error-patterns.md      ← curated known errors with diagnosis + fixes
└── maps/
    └── endpoint-map.md        ← all URL patterns with view classes
```

### Regeneration Rules (MANDATORY)

Run `python manage.py generate_context` after **any** of the following:

| Trigger | Why |
|---------|-----|
| `python manage.py makemigrations` | Model fields changed — reference & fixtures are stale |
| Adding/removing a Django model | Model reference and hierarchy need updating |
| Adding/changing URL patterns | Endpoint map is stale |
| Adding new React services/hooks/pages | React import paths need updating |
| Changing API response shapes | Fixtures need updating |

**Shorthand — always pair migrations with context:**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py generate_context
```

After regenerating, reindex for the AI assistant:
```bash
python manage.py index_docs --source copilot_context
```

### Error Patterns

When you encounter a new recurring error, add it to `.copilot-context/errors/error-patterns.md` with:
- The error text
- The cause
- The fix

This lets the AI debugger recognize the pattern immediately.

---

## 13. Instruction File Sync (MANDATORY)

Copilot instructions exist in **two locations** in wc3 because `.github/` is gitignored:

| File | Role |
|------|------|
| `git_bypass/copilot.instructions.md` | **Source of truth** — committed to git, shared with the team |
| `.github/instructions/copilot.instructions.md` | **Active copy** — read by VS Code / Copilot (local only, not committed) |

### Rules

1. **Always edit `git_bypass/copilot.instructions.md` first** — it's the canonical version.
2. **Immediately copy to the active location:**
   ```bash
   cp git_bypass/copilot.instructions.md .github/instructions/copilot.instructions.md
   ```
3. **After pulling**, if `git_bypass/` was updated, copy to `.github/instructions/`.
4. **Django startup check** (`common/checks.py`) will warn you if the files are out of sync.
5. **Both repos must stay aligned** — when instructions change, update both:
   - `webClerk3/git_bypass/copilot.instructions.md` (wc3 source of truth)
   - `React2025/git_bypass/copilot.instructions.md` (r25 source of truth)
   - Then copy each to its `.github/instructions/` counterpart.

### System Check

Django runs `copilot.W001` / `copilot.W002` on every `runserver` / `manage.py check`:
- **W001**: Active file missing entirely — copy from `git_bypass/`.
- **W002**: Files differ — `git_bypass/` has been updated, copy it over.

---

## 14. AI Inventory Observer & AGT Integration

The wc3 backend includes an **LLM-powered inventory observational learning system** that captures user actions, generates natural language summaries, detects patterns, and answers questions about inventory history.

### Core Components

| File | Purpose |
|------|---------|
| `apps/ai_assistant/models.py` | `InventoryEvent` model — 30+ fields capturing events |
| `apps/ai_assistant/services/event_emitter.py` | `InventoryEventEmitter` — emits events from signals |
| `apps/ai_assistant/services/llm_observer.py` | `LLMInventoryObserver` — summarization, patterns, Q&A |
| `apps/transactions/signals.py` | Signal hooks via `_emit_line_event()` |

### Event Logging

All 5 transaction line types automatically emit `InventoryEvent` records:

```python
# Event types per transaction type:
# order_line_add, order_line_update, order_line_delete, order_line_item_change
# invoice_line_add, invoice_line_update, invoice_line_delete, ...
# proposal_line_add, purchase_line_add, workorder_line_add, ...
```

### Observer Capabilities (4 Phases)

| Phase | Method | Purpose |
|-------|--------|---------|
| 1 | Silent logging | Events stored in `InventoryEvent` table |
| 2 | `summarize_event()` | LLM generates human-readable summary |
| 2 | `get_item_narrative()` | Multi-paragraph item history |
| 3 | `detect_patterns()` | Trend analysis, anomaly detection |
| 4 | `answer_question()` | Natural language Q&A about inventory |

### AGT Patent Integration (Future)

The system architecture aligns with **U.S. Patent Application 19/356,062** — *Automated Guideways Facilitating 3-Tiered Cargo Shipments*:

| Patent Concept | Implementation |
|----------------|----------------|
| LLM-defined load/unload windows (Claim 4) | `detect_patterns()` learns optimal scheduling |
| Sensor suite event logging (Claims 6-7) | `InventoryEvent.payload` captures sensor data |
| Blockchain chain-of-custody (Claim 3) | Events form audit trail; hashable to blockchain |
| Predictive shipment forecasts (Claim 9) | Pattern detection feeds LLM scheduling |
| Routing-control modules (Claim 8) | Alerts (`below_reorder`) trigger AGT routing |

Future AGT event types (not yet implemented):
- `shipment_arrived`, `container_scanned`, `temp_excursion`, `tamper_detected`
- `subcontainer_loaded`, `subcontainer_unloaded`, `tier_transfer`

### Configuration

```python
# settings.py
INVENTORY_EVENTS_ENABLED = True  # Set to False to disable event logging
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "deepseek-r1:8b"
```

### Documentation

- Architecture & usage: `readmes/llm-inventory-observer.md`
- Patent reference: `readmes/topics/ai/patent.md`

---

## 15. Coding Journal — Developer Learning

The wc3 backend captures **coding sessions** for LLM learning from our development efforts. This builds institutional knowledge over time.

### Core Components

| File | Purpose |
|------|---------|
| `apps/ai_assistant/models.py` | `CodingSession`, `ErrorPattern` models |
| `apps/ai_assistant/services/coding_journal.py` | `CodingJournal` service |
| `apps/ai_assistant/management/commands/log_session.py` | `log_session` CLI |
| `apps/ai_assistant/management/commands/journal.py` | `journal` CLI (Q&A, search, stats) |

### Logging Sessions

After completing work, log a session:

```bash
# Interactive mode
python manage.py log_session

# Quick log
python manage.py log_session --type bugfix \
  --problem "Order totals not updating" \
  --solution "Added post_delete signal" \
  --learnings "Always wire both post_save and post_delete" \
  --apps transactions \
  --tags "signals,totals"
```

### Querying the Journal

```bash
# Ask a question about coding history
python manage.py journal ask "How did we fix the order totals issue?"

# Find similar sessions
python manage.py journal find "signal post_delete"

# Show recent sessions
python manage.py journal recent --days 7

# Show session statistics
python manage.py journal stats

# Log an error pattern
python manage.py journal error "TypeError: cannot unpack" \
  --cause "Function returning None" \
  --fix "Added default return value"
```

### Session Types

| Type | Use For |
|------|---------|
| `feature` | New functionality |
| `bugfix` | Bug fixes |
| `refactor` | Code restructuring |
| `test` | Test additions |
| `docs` | Documentation |
| `devops` | Infrastructure |
| `debug` | Debugging sessions |
| `exploration` | Code exploration |
| `review` | Code reviews |

### Best Practice

**End each significant work session with a log entry** — this captures learnings while they're fresh and builds the knowledge base.

---

## 16. Git Observer — Schema Drift Detection

The wc3 backend includes a **Git Observer** that watches commits for schema drift and outdated code patterns. This catches when team members push code using deprecated field names or banned patterns.

### Core Components

| File | Purpose |
|------|---------|
| `apps/ai_assistant/models.py` | `GitEvent`, `SchemaDrift` models |
| `apps/ai_assistant/services/git_observer.py` | `GitObserver` service |
| `apps/ai_assistant/management/commands/analyze_commits.py` | `analyze_commits` CLI |
| `tools/git-hooks/post-commit` | Auto-analysis hook |

### Analyzing Commits

```bash
# Scan recent commits (last 7 days)
python manage.py analyze_commits

# Analyze a specific commit
python manage.py analyze_commits --commit abc123

# Scan last 30 days
python manage.py analyze_commits --days 30

# Check staged files before commit
python manage.py analyze_commits --check-staged

# Show only commits with drift issues
python manage.py analyze_commits --drift-only
```

### Detected Drift Types

| Type | Severity | Example |
|------|----------|---------|
| `deprecated_field` | error | Using `quantity.placed` instead of `quantity.staged` |
| `banned_pattern` | warning | Using `print()` instead of logging |
| `old_api_shape` | error | Using outdated API response structure |
| `stale_import` | warning | Importing from moved/deleted module |

### Deprecated Field Mappings

The observer automatically flags these patterns:

| Old (Flagged) | Current (Expected) |
|---------------|-------------------|
| `quantity.placed` | `quantity.staged` |
| `qty_placed` | `qty_staged` |
| `placed_qty` | `staged_qty` |

### Installing Post-Commit Hook

```bash
# Link the hook to your local .git/hooks
ln -sf ../../tools/git-hooks/post-commit .git/hooks/post-commit
```

### Co-Change Patterns

The observer tracks which files frequently change together:

```python
from apps.ai_assistant.services.git_observer import GitObserver

observer = GitObserver()
patterns = observer.get_cochange_patterns('apps/inventory/models.py')
# Returns: [{'file': 'apps/inventory/serializers.py', 'count': 15, 'pct': 75.0}, ...]
```

---

## 17. Session Context

When starting a coding session, establish:

1. **Which app/model?** (e.g., `transactions/invoice`, `products/item`)
2. **What task?** (new feature, bug fix, refactor, test)
3. **Which layer?** (model, service, view, serializer, test)

This helps scope changes correctly and avoid unintended side-effects across the modular architecture.

---

## 18. AI Agent Roles

| Agent | Identity | Role |
|-------|----------|------|
| **Copilot** | GitHub Copilot (primary) | Inline code generation, edits, terminal commands, orchestration |
| **Alice** | Subagent (research & multi-step) | Deep codebase search, complex analysis, autonomous multi-file research |

Alice is invoked via the subagent tool for tasks requiring broad codebase exploration
or multi-step research. She returns a single report. Use her when:
- Searching for a pattern across many files
- Auditing naming conventions, FK usage, or field consistency
- Investigating bugs that span multiple services
- Gathering context before a complex refactor
