# AI Integration Plan

> I have DeepSeek installed on my computer. Is it practical to integrate it or some other localized AI to watch, learn, and adapt to our writing and using the software to provide user support for both use and writing user functions in the future?

**Answer: Yes — practical and increasingly common.**

---

## What's Feasible Today

### Local AI for Code Assistance (high value, low effort)

- DeepSeek (or Ollama-hosted models like CodeLlama, Mistral) can already be used as a local coding copilot via VS Code extensions like Continue.dev or Ollama integrations
- Feed it codebase context (Django models, API patterns, 4D methods) to get project-aware suggestions

### Local AI for User Support (medium effort, high value)

- A **RAG (Retrieval-Augmented Generation)** pipeline is the practical path:
  - Index docs, readmes, and code comments into a vector store (ChromaDB, FAISS)
  - Query DeepSeek with relevant context at inference time
- This could power an in-app help chatbot in React2025 or vue2020 that answers questions like *"how do I create a price tier?"* using actual codebase as ground truth

---

## What's Hard (for now)

### "Watch, Learn, and Adapt" Continuously

True continuous learning from user behavior requires fine-tuning infrastructure. DeepSeek can be fine-tuned locally if you have a GPU with ~24GB+ VRAM, but:

- You'd need to collect and curate training data (user interactions, support tickets, code patterns)
- Fine-tuning cycles take time and expertise to get right
- **RAG-based approaches get you 80% of the benefit at 10% of the complexity**

### Key Complexities

| Complexity | Impact | Mitigation |
|---|---|---|
| Model size vs. hardware | Larger models need more VRAM/RAM | Use quantized models (GGUF) via Ollama |
| Context window limits | Models can only see ~8K-128K tokens at once | RAG retrieves only relevant chunks |
| Keeping index current | Code/docs change frequently | Automate re-indexing on git push or file save |
| Quality of answers | Local models are weaker than GPT-4/Claude | Compensate with better retrieval and prompt engineering |
| 4D language support | No local model is trained on 4D code | Include 4D method examples in RAG corpus; consider few-shot prompting |
| Multi-stack context | Project spans Django, React, Vue, 4D | Namespace documents by stack in vector store |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────┐
│  React2025 / vue2020  (Help Widget)         │
│         ↓  user question                    │
│  webClerk3 Django API  (/api/ai/ask/)       │
│         ↓                                   │
│  RAG Pipeline                               │
│  ┌──────────┐    ┌────────────────────┐     │
│  │ Vector DB │◄──│ Indexed docs/code  │     │
│  │ (Chroma)  │    │ readmes, models,   │     │
│  └─────┬─────┘    │ 4D methods         │     │
│        │ context   └────────────────────┘     │
│        ↓                                     │
│  Local DeepSeek / Ollama                     │
│        ↓                                     │
│  Contextual answer                           │
└─────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|---|---|---|
| LLM Runtime | Ollama + DeepSeek-Coder | Local inference, no API costs, full privacy |
| Vector Store | ChromaDB | Lightweight, Python-native, embeds in Django process |
| Embeddings | `sentence-transformers` (local) | Convert docs/code into vectors for similarity search |
| Django App | `apps/ai_assistant/` | API endpoint, RAG orchestration, conversation history |
| Frontend Widget | React component | Chat UI, streams responses, in-app contextual help |
| Indexer | Management command | Crawls readmes, docstrings, 4D methods; builds vector index |

---

## Implementation Plan

### Phase 1 — Foundation (scaffold) ✅ DONE

1. ✅ **Install Ollama** + load DeepSeek-Coder — local API endpoint (`localhost:11434`)
2. ✅ **Create Django app** `apps/ai_assistant/` in webClerk3 with:
   - `/wcapi/ai/ask/` endpoint (accepts question, returns streamed answer)
   - `/wcapi/ai/feedback/` endpoint (thumbs up/down)
   - `/wcapi/ai/health/` endpoint (system status)
   - `/wcapi/ai/history/` endpoint (conversation history)
   - RAG service class that queries ChromaDB and constructs prompts
   - Management commands: `index_docs`, `ai_health`
3. ✅ **Index documentation** — readmes, models, services, views, 4D methods, instructions, React types
4. ✅ **Automated setup** — `tools/setup_ai.sh` one-command setup for team members

### Phase 2 — Frontend Integration ✅ DONE

5. ✅ **Help widget** — `AiHelpWidget.tsx` floating chat in React2025
6. ✅ **Conversation history** — Conversation & Message models track Q&A per user
7. ✅ **Contextual awareness** — passes current page URL as context
8. ✅ **Feedback system** — thumbs up/down on each assistant response

### Phase 3 — Multi-Mode Intelligence ✅ DONE

9. ✅ **Mode system** — 6 specialized modes with tailored system prompts:
   - `general` — Conversational help about CommerceExpert
   - `developer` — Code-aware with file paths, conventions, import patterns
   - `debugger` — Error analysis: paste a traceback, get a diagnosis + fix
   - `user_support` — Plain-language help for end users (no jargon)
   - `code_review` — Review code against project conventions
   - `test_writer` — Generate tests following pytest/vitest patterns
10. ✅ **Specialized endpoints**:
    - `POST /wcapi/ai/debug/` — paste a traceback for instant diagnosis
    - `POST /wcapi/ai/review/` — submit code for convention review
    - `POST /wcapi/ai/generate/` — generate code or tests
    - `GET /wcapi/ai/modes/` — list available modes
    - `POST /wcapi/ai/reindex/` — trigger reindex (staff only)
11. ✅ **Enhanced indexing** — added settings, tasks, tests, common, React services/pages
12. ✅ **Auto-reindex** — git post-commit hook runs targeted reindex in background
13. ✅ **Mode-aware React widget** — mode selector dropdown, color-coded per mode

### Phase 4 — Continuous Improvement (next)

14. ✅ **Console capture** — `useConsoleCapture` hook auto-captures `console.error`, `window.onerror`, unhandled promise rejections; paste panel in debugger mode
15. ✅ **Developer tools documentation** — `readmes/topics/developer-tools.md` catalogues all dev tools (DevTools panel, AI widget, Whitelist Tester, Swagger UI)
16. ✅ **Copilot context system** — `.copilot-context/` directory with auto-generated reference files:
    - `models/model-reference.md` — every Django model's fields, types, relations (80 models, 3,400+ lines)
    - `models/model-hierarchy.md` — CoreModel → BaseModel mixin chain overview
    - `fixtures/*.json` — golden API response shapes for all 80 models
    - `imports/django-imports.md` — canonical import paths for models, services, views
    - `imports/react-imports.md` — canonical import paths for React services, hooks, pages, types
    - `maps/endpoint-map.md` — all 600+ URL patterns with view classes and names
    - `errors/error-patterns.md` — curated known error patterns with diagnosis and fixes
17. ✅ **Context generator command** — `python manage.py generate_context` generates all context files in 0.6s
18. **Feedback analytics** — track thumbs up/down patterns to improve prompts
19. **Server log access** — give debugger mode access to Django/Celery logs
20. **SSE streaming in widget** — real-time token output (backend ready, frontend TODO)
21. **Scheduled reindex** — Celery periodic task for full reindex overnight

> **Setup guide for team members:** see [setup-guide-Alice.md](setup-guide-Alice.md)

### Phase 5 — Autonomous Data Intelligence ✅ DONE

Ollama + Celery tasks that continuously analyze, clean, and optimize live data without manual intervention.

**Implementation files:**
- Services: `apps/ai_assistant/services/` — `health_scorer.py`, `schema_drift_detector.py`, `data_parser.py`, `json_optimizer.py`, `margin_tracker.py`, `sync_advisor.py`
- Celery tasks: `apps/ai_assistant/tasks.py` — 7 task functions + `full_intelligence_run()`
- Management command: `python manage.py ai_intelligence` — CLI entry point with `--task`, `--llm`, `--apply`, `--report`, `--limit`, `--model` flags
- User guide: `readmes/topics/ai/improving-tasks-Alice.md` — how to improve AI task results through data practices

#### 5A. Database Sync Conflict Advisor ✅

| Aspect | Detail |
|---|---|
| Goal | Keep wc3 (PostgreSQL) and wc2 (4D) databases in sync during migration period |
| AI Role | **Advisory only** — conflict resolution, not transport. Sync engine is deterministic (Celery + row versioning + change-data-capture). Ollama evaluates ambiguous merge conflicts (e.g., both sides edited `refs.links`) and proposes the smarter resolution. |
| Implementation | Celery periodic task compares `row_version` / checksums between databases. On conflict, serializes both versions and asks Ollama to score which is more complete/current. Human approval required initially. |
| Risk | Low — AI is suggestion layer, never writes without approval |
| Priority | Medium — needed while wc2 coexists |
| Service | `apps/ai_assistant/services/sync_advisor.py` — `SyncConflictAdvisor` class with `detect_conflicts()`, `auto_resolve()`, `resolve_all()`, `format_report()` |
| Task | `apps/ai_assistant/tasks.py` — not yet scheduled (requires 4D bridge) |

#### 5B. JSON Envelope Optimization (.refs, .prefs, .metadata) ✅

| Aspect | Detail |
|---|---|
| Goal | Reduce bloat in denormalized JSON fields; promote high-value data, prune dead weight |
| AI Role | **Analysis + recommendation.** Celery task scans access patterns (which `refs.keywords` get searched, which `prefs` keys the frontend reads, which `metadata.flags` are checked). Ollama scores each key's utility and suggests: prune, keep, or promote to indexed field. |
| Targets | `refs.links` — orphaned foreign keys to deleted records; `refs.keywords` — duplicates, low-value terms; `prefs` — keys never read by r25; `metadata.history` — entries beyond retention window; `metadata.flags` — stale one-off flags |
| Implementation | Nightly Celery task → generates optimization report → optional auto-compact with `AtomicJSONMixin.atomic_json_set()` for safe partial updates |
| Risk | Low if advisory-first; medium if auto-pruning enabled without approval gate |
| Priority | High — directly improves query performance and storage |
| Service | `apps/ai_assistant/services/json_optimizer.py` — `JSONOptimizer` class with `analyze_refs()`, `analyze_prefs()`, `analyze_metadata()`, `compact_record()`, `compact_all()`, `format_report()` |
| Task | `json_optimize_task(limit, dry_run)` — nightly, advisory by default, `--apply` to compact |

#### 5C. Data Input Parsing (addresses, phones, vCards) ✅

| Aspect | Detail |
|---|---|
| Goal | Clean and normalize contact data on ingestion |
| AI Role | **Fuzzy fallback.** Deterministic libraries handle structured parsing: `vobject` (vCards), `phonenumbers` (phones), `usaddress`/`libpostal` (addresses). Ollama handles the 20% that rules can't: OCR-mangled addresses, partial input inference, international format normalization. |
| Integration Points | `Address.queue_verification()` stub (already exists), `Phone` model normalization, new `/wcapi/ai/parse/` endpoint for bulk import cleanup |
| Implementation | On save signal or bulk import: run deterministic parser → if confidence < threshold, pass to Ollama for best-guess normalization → flag for human review if still uncertain |
| Risk | Low — worst case falls back to original input |
| Priority | High — data quality at the gate prevents downstream problems |
| Service | `apps/ai_assistant/services/data_parser.py` — `DataParser` class with `parse_phone()`, `parse_address()`, `parse_vcard()`, `clean_address_record()`, `bulk_clean_addresses()`, `bulk_clean_phones()` |
| Task | `data_cleanup_task(limit, use_llm)` — nightly, deterministic-first with LLM fallback |

#### 5D. Schema ↔ TypeScript Drift Detection ✅

| Aspect | Detail |
|---|---|
| Goal | Detect mismatches between Django model fields and r25 TypeScript interfaces / Zod schemas |
| AI Role | **Structural comparison.** Celery task introspects Django model fields (type, required, default, choices) and compares against `.ts` interfaces in `src/apps/*/models/*/types/` and Zod schemas in `src/validations/`. Ollama reads both representations and flags: missing fields, wrong types (`number` vs `string`), required/optional mismatches, fields present in TS but removed from Django. |
| Output | Drift report (markdown or JSON) surfaced in AI widget developer mode; optionally auto-generates corrected `.ts` interface stubs |
| Implementation | Extend `generate_context` management command to emit field-type comparison; Ollama evaluates semantic equivalence (e.g., `BigIntegerField` → `number` vs `string`) |
| Risk | Low — read-only analysis; generated stubs require developer approval |
| Priority | Very High — prevents the #1 cause of runtime bugs (schema mismatch) |
| Service | `apps/ai_assistant/services/schema_drift_detector.py` — `SchemaDriftDetector` class with `detect_model()`, `detect_all()`, `llm_analyze_drift()`, `format_report()` |
| Task | `schema_drift_task(use_llm)` — weekly, read-only analysis |

#### 5E. Record Data Health Scoring ✅

| Aspect | Detail |
|---|---|
| Goal | Populate `HealthMixin.health_rating` (0-100) with meaningful per-record quality scores |
| AI Role | **Hybrid scoring.** Deterministic rules handle the 80% (field completeness, recency, link integrity). Ollama evaluates subjective quality: is the description meaningful, are keywords relevant, does the address look plausible? |
| Scoring Example (Contact) | Has email +10, has phone +10, has valid address +15, has org link +10, keywords populated +5, recent activity +20, verified address +15, description quality (AI) +15 |
| Implementation | Nightly Celery task iterates models with `HealthMixin`; applies model-specific rule config; writes `health_rating` via bulk update. AI evaluation sampled (not every record every night) to manage Ollama load. |
| Risk | Low — `health_rating` is informational, doesn't gate business logic |
| Priority | High — enables data quality dashboards and targeted cleanup campaigns |
| Service | `apps/ai_assistant/services/health_scorer.py` — `HealthScorer` class with `score_record()`, `score_model()`, `score_all()`, `generate_report()` |
| Task | `health_scoring_task(limit, use_llm)` — nightly, updates `health_rating` field on every BaseModel record |

#### 5F. Margin & Profitability Tracking ✅

| Aspect | Detail |
|---|---|
| Goal | Continuous margin analysis across transactions, items, customers, and reps |
| AI Role | **Anomaly detection + narrative.** The math is deterministic (margin = (price - cost) / price, using `Item.price`, `Item.cost`, and line-level data). Ollama adds: anomaly alerts (margin suddenly dropped — why?), trend forecasting (predict next quarter from `ItemUsage` history), and natural-language summaries for dashboards. |
| Data Sources | `Item.cost` / `Item.price` JSON fields, `ItemUsage.metrics` (`margin.factor`, `sales.actual`, `cost.actual`), transaction line `unit_cost` / `unit_price` from Pending `data` |
| Implementation | Celery task aggregates margin data into `ItemUsage` monthly snapshots (already structured for this). Ollama generates plain-English margin reports per item/customer/period. Alert thresholds configurable in `Setting` model. |
| Risk | Low — read-only analytics layer |
| Priority | Medium-High — direct business value but requires clean cost data first |
| Service | `apps/ai_assistant/services/margin_tracker.py` — `MarginTracker` class with `compute_item_margins()`, `compute_usage_margins()`, `llm_margin_analysis()`, `format_report()` |
| Task | `margin_tracking_task(limit, use_llm)` — weekly, writes margin stats to `ItemUsage` |

#### 5G. Inventory Velocity & Investment Efficiency ✅

| Aspect | Detail |
|---|---|
| Goal | Measure margin earned per unit of time capital is tied up in inventory: `velocity = margin / carrying_time` |
| AI Role | **Predictive analytics.** Calculates velocity from `ItemUsage.metrics` (`turns.actual`, `turns.target`) combined with `Item.cost` and transaction timing. Ollama ranks items by investment efficiency, identifies slow-movers burning carrying cost, recommends reorder adjustments, and flags items where velocity is declining. |
| Data Sources | `ItemUsage` monthly snapshots (`turns.*`, `inventory.*`, `sales.*`), `Item.quantity` (on_hand, on_po, on_so), `Item.cost` (average, landed), transaction dates for carrying-time calculation |
| Metrics | Inventory turns ratio, days-of-supply, carrying cost per item, margin velocity ($/day/item), dead stock identification |
| Implementation | Weekly Celery task computes velocity metrics → stores in `ItemUsage.metrics` (new keys: `velocity.margin_per_day`, `velocity.carrying_days`, `velocity.rank`). Ollama generates investment-efficiency report with actionable recommendations. |
| Risk | Medium — recommendations could influence purchasing decisions; require human review |
| Priority | High — strongest differentiator; directly impacts capital efficiency |
| Service | `apps/ai_assistant/services/margin_tracker.py` — `MarginTracker.compute_velocity()`, `update_usage_velocity()`, `llm_velocity_analysis()` |
| Task | `velocity_task(limit, use_llm)` — weekly, stores `velocity.margin_per_day`, `velocity.carrying_days`, `velocity.rank`, `velocity.investment` in `ItemUsage.metrics` |

#### 5H. Layout ↔ Schema Drift Detection ✅

| Aspect | Detail |
|---|---|
| Goal | Detect mismatches between Django model fields and the field references actually used in React page components (Detail forms, List columns, Display views) |
| AI Role | **Static analysis + optional LLM triage.** Scans R25 page files for `register()`, `Controller`, `ScalarCard`, `JsonCard`, `handleFieldChange`, `valueFrom`, and `selector` patterns. Compares extracted field names against Django model introspection. Ollama classifies issues as real problems vs. intentional omissions. **Learns from corrections** — tracks what was fixed between runs and feeds correction history into LLM prompts for smarter recommendations. |
| Data Sources | Django `_meta.get_fields()`, R25 `src/apps/**/pages/*Detail.tsx`, `*List.tsx`, `*Display.tsx` |
| Detection Types | **phantom_field** (layout references non-existent field, HIGH), **unrendered_field** (Django field absent from all layouts, MEDIUM/LOW), **unrendered_json** (JSONField with no sub-field inputs or JsonCard, LOW), **detail_only** (field in Detail but not List, INFO) |
| Implementation | Regex-based extraction from page files, JSON sub-field prefix resolution (e.g., `price_base` → `price` JSONField), BaseModelCards fields auto-excluded. Weekly Celery task. |
| Features | **Dismissals** — mark intentional mismatches so they stop recurring. **Correction history** — diffs between runs track what was fixed and when. **LLM learning** — past corrections + dismissals fed into prompts for smarter analysis. **Persistent report** — saves full markdown report to `readmes/topics/ai/layout-drift-Alice.md`. |
| CLI | `--task layout` (scan), `--report-file` (save report), `--dismiss model:field:type --reason '...'` (dismiss), `--undismiss model:field:type` (undo), `--history` (view corrections) |
| Risk | Low — read-only static analysis, no data modification |
| Priority | Medium — catches stale field references and missing form inputs before they hit production |
| Service | `apps/ai_assistant/services/layout_drift_detector.py` — `LayoutDriftDetector` class with `detect_model()`, `detect_all()`, `dismiss_issue()`, `get_correction_history()`, `generate_full_report()`, `llm_analyze_drift()` |
| Task | `layout_drift_task(use_llm)` — weekly, scans all models with R25 pages, saves report and records history |
| Data Files | `apps/ai_assistant/data/layout_dismissals.json` (dismissed issues), `apps/ai_assistant/data/layout_history.json` (run snapshots + corrections) |

#### 5I. Calculation Audit (r25 vs wc3 Discrepancy Detection) ✅

| Aspect | Detail |
|---|---|
| Goal | Detect when r25 frontend calculations diverge from wc3 backend authoritative recalculations |
| AI Role | **Observational audit.** wc3 is always authoritative for dollar amounts. On every sell-side line save, the service snapshots r25-submitted `price.extended` and `cost.extended` before `_calculate_extended_price()` runs, then compares against wc3's recalculated values. Quantity envelope consistency is also validated after `normalize_quantity_map()`. |
| Checks | **price.extended** (qty × unit − discount, tolerance $0.02), **cost.extended** (same formula, tolerance $0.02), **quantity.remaining** (standalone = staged, transferred = staged − active, tolerance 0.001), **quantity.staged mirroring** (standalone: staged = active) |
| Data Sources | Line model JSON fields (`price`, `cost`, `quantity`) before and after wc3 normalization |
| Implementation | `check_extended_prices()` called at end of `_calculate_extended_price()`. `check_quantity()` called at end of `ensure_json_defaults()`. Both wrapped in try/except — never blocks the save path. Discrepancies logged via Python `ai_audit` logger AND persisted to `accounts.Audit` model. |
| Risk | Zero — purely observational, auto-resolved (wc3 applies its value regardless) |
| Priority | High — prevents silent frontend calculation bugs from reaching production undetected |
| Service | `apps/accounts/services/ai_audit.py` — `check_extended_prices()`, `check_quantity()`, `_log_and_persist()`, `_create_audit_record()` |
| Task | Runs inline on every line save (no Celery task — latency-critical path) |
| Documentation | [calculation-audit-Alice.md](calculation-audit-Alice.md) — full details, query examples, configuration |

#### Phase 5 Sequencing

| Order | Task | Status | Service File |
|---|---|---|---|
| 1 | 5E Health Scoring | ✅ Done | `health_scorer.py` |
| 2 | 5D Schema Drift Detection | ✅ Done | `schema_drift_detector.py` |
| 3 | 5C Data Input Parsing | ✅ Done | `data_parser.py` |
| 4 | 5B JSON Envelope Optimization | ✅ Done | `json_optimizer.py` |
| 5 | 5F Margin Tracking | ✅ Done | `margin_tracker.py` |
| 6 | 5G Inventory Velocity | ✅ Done | `margin_tracker.py` |
| 7 | 5A Sync Conflict Advisor | ✅ Done | `sync_advisor.py` |
| 8 | 5H Layout Drift Detection | ✅ Done | `layout_drift_detector.py` |
| 9 | 5I Calculation Audit | ✅ Done | `ai_audit.py` (in `apps/accounts/services/`) |

> **User guide:** see [improving-tasks-Alice.md](improving-tasks-Alice.md) for how users can improve LLM task results through data practices.

---

## Key Design Decisions

- **RAG over fine-tuning**: Documents change frequently; re-indexing a vector store takes seconds, while re-training a model takes hours
- **Local-first**: No data leaves the machine, no API costs, works offline
- **Ollama as runtime**: Standard API interface means we can swap models (DeepSeek → Mistral → Llama) without code changes
- **ChromaDB**: Zero-config, embeds in Django, good enough for our corpus size (~thousands of documents, not millions)


