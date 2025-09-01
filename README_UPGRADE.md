# Upgrade Roadmap (webClerk3)

Purpose: Shared, prioritized enhancement backlog for Core/BaseModel, Universal API, and related infrastructure. Focus on maintainability, performance, correctness, and developer velocity. Each item lists: Goal, Benefit, Acceptance Criteria, Effort (S/M/L), Priority (P1–P3).

---

## Changelog Consideration (Deferred)

During rapid iteration we defer a formal `CHANGELOG.md` to avoid high-noise, low-signal entries. Revisit once:

1. External clients rely on stable APIs (SDKs, integrations)
2. We enforce deprecation windows for breaking changes
3. We cut tagged releases (≥ weekly cadence)

Future format (Keep a Changelog compatible):

```markdown
## [0.4.0] - 2025-09-15
### Added
- Org aspect validation command
### Changed
- Optimistic concurrency returns 412 instead of 409
### Fixed
- JSON size telemetry off-by-one threshold
```

Comparison link style:
`[0.4.0]: https://github.com/JPods/webClerk3/compare/v0.3.2...v0.4.0`

Until adoption: this roadmap + commit history = authoritative change trace. Seed initial changelog from "Recently Completed" + phase completion notes when activated.

---

## 0. Legend

- Priority: P1 (next / high impact), P2 (important), P3 (nice-to-have)
- Effort: S (≤0.5d), M (0.5–2d), L (>2d / multi-step)
- Type Tags: [Concurrency] [Validation] [Perf] [DX] [Search] [Infra] [Security] [API] [Data] [Observability]

---

## 1. Concurrency & Data Integrity

### 1.1 Conditional Version Bump (P1 / M) [Concurrency]

Goal: Only increment `version` when meaningful persisted fields change (ignore pure touch/no-op updates).

Benefit: Reduces needless conflicts & diff noise.

Acceptance:

- Saving with no field changes does NOT increment version.
- Metadata-only history stamp without changed business fields still increments? (Decide & document.)
- Test: two consecutive saves with no changes keep same version.

### 1.2 Batch Atomic JSON Ops (P2 / M) [Concurrency]

Goal: Allow multi-path JSON updates in one SQL round trip.

Benefit: Fewer race windows & lower latency.

Acceptance:

- New helper: `atomic_json_multi(pk, operations=[('metadata', ['flags','x'], 1), ...])`.
- All paths updated atomically, single version bump.
- Conflict semantics identical to single op.

### 1.3 Change Hash Short-Circuit (P2 / S) [Concurrency]

Goal: Compute stable hash (xxhash / sha1) of tracked fields to skip version bump when unchanged.

Benefit: Micro-optimization + integrity assertion.

Acceptance:

- `_last_change_hash` stored (in memory or metadata.versioning).
- Save aborts early if hash unchanged (and no forced fields modified).

### 1.4 Retry Wrapper for Transient Conflicts (Optional) (P3 / S) [Concurrency]

Goal: Helper `with_conflict_retry(fn, attempts=3, backoff_ms=10)`.

Benefit: Smoother UX under modest contention.

Acceptance:

- Retries only on `VersionConflictError`.
- Jitter added.

---
 
## 2. Validation & Schema Governance

### 2.1 Pluggable JSON Schema Registry (P1 / M) [Validation]

Goal: Validate `metadata/refs/prefs/comments` structure against per-table schema.

Benefit: Prevent drift & junk accumulation.

Acceptance:

- Registry: `SCHEMA_REGISTRY = {'contacts.metadata': {jsonschema}, ...}`.
- Modes: warn (log), enforce (raise 400 / ValidationError).
- Tests: invalid key triggers warning/enforcement.

### 2.2 Normalization Layer (P2 / S) [Validation]

Goal: Centralized coercions (trim strings, lowercase emails, clamp ints, null→default).

Acceptance:

- Hook: `normalize_fields()` executed pre-save.
- Config: per-model override list.

### 2.3 Metadata Key Allow-List / Deprecation (P3 / S) [Validation]

Goal: Track allowed keys + mark deprecated ones.

Acceptance:

- `metadata['flags']['deprecated_keys']` auto-populated for removed keys.

---
 
## 3. Performance & Indexing

### 3.1 Partial Indexes on Active Rows (P1 / S) [Perf]

Goal: Create partial indexes: `WHERE is_deleted = false AND is_archived = false` for hot queries.

Acceptance:

- Migrations with partial indexes on key tables (contacts, documents, connections).
- Query plan shows usage.

### 3.2 Functional Contact Name Index (P2 / S) [Perf]

Goal: Index on lower(concat(name_first,' ',name_last)).

Acceptance:

- Search using ILIKE on combined name hits index (EXPLAIN validates).

### 3.3 JSON Keywords GIN Optimization (P2 / M) [Search]

Goal: Add `GIN (refs jsonb_path_ops)` or expression index on refs->'keywords'.

Acceptance:

- Keyword filter query uses index (EXPLAIN).

### 3.4 Lazy Keyword Regeneration (P2 / M) [Perf]

Goal: Only regenerate keywords if any text field changed.

Acceptance:

- Save with no text changes leaves `keywords_pending` False.

### 3.5 Envelope Size Telemetry (P3 / S) [Observability]

Goal: Metric for average / p95 JSON size per model.

Acceptance:

- Prometheus metrics: `wcapi_metadata_bytes{model=...}`.

---
 
## 4. Search & Content

### 4.1 Async Keyword Refresh Queue (P1 / M) [Search]

Goal: Offload heavy keyword recompute to Celery worker.

Acceptance:

- Save sets `keywords_pending=True`.
- Worker task processes and resets flag.
- Test with delayed refresh.

### 4.2 Materialized Searchable Text Column (P2 / M) [Search]

Goal: Denormalized `search_text` (all key tokens) for cheap trigram/ILIKE.

Acceptance: Column populated on keyword refresh; index added.

---
 
## 5. Caching & Projection

### 5.1 Projection LRU Cache (P2 / S) [Perf]

Goal: Cache frequently used projection field sets per model.

Acceptance:

- Simple LRU (size configurable) invalidated on model save/version bump.

### 5.2 ETag / Checksum Support (P2 / M) [API]

Goal: Generate `ETag` as hash(model, version, projection_fields) for conditional GET.

Acceptance:

- GET returns ETag header; If-None-Match yields 304.

---
 
## 6. Observability & Auditing

### 6.1 Structured Change Events (P1 / M) [Observability]

Goal: Emit event (model, pk, version, changed_fields, ts) to message channel.

Acceptance: Signal or hook writes JSON to logging or queue; test asserts structure.

### 6.2 Diff Log (Last N) (P2 / M) [Auditing]

Goal: Maintain bounded list metadata.versioning.diffs (e.g., last 10).

Acceptance: Each update appends concise diff {added, removed, changed}; truncated beyond N.

### 6.3 Audit Table (Optional) (P3 / L) [Auditing]

Goal: Separate `model_audit` table for high-trust historical queries.

Acceptance: Row per change; index on (model, pk).

---
 
## 7. Comments & Notes Lifecycle

### 7.1 Note ID & Operations (P1 / S) [Data]

Goal: Each note gets UUID; enable targeted delete/update.

Acceptance: New notes include `id`; patch endpoint removes by id.

### 7.2 Note Pruning Task (P2 / S) [Data]

Goal: Limit notes to N recent entries (configurable).

Acceptance: Management command + scheduled Celery beat.

### 7.3 Max Note Size Enforcement (P2 / S) [Validation]

Goal: Truncate or reject notes > configured length.

Acceptance: Oversized note raises ValidationError or truncates (document behavior).

---
 
## 8. Security & Privacy

### 8.1 Encrypted JSON Paths (P2 / L) [Security]

Goal: Declarative encryption for selected metadata keys.

Acceptance: Transparent decrypt on access, encrypt on save; keys in env KMS wrapper.

### 8.2 Redaction Layer in to_universal_dict (P2 / M) [Security]

Goal: Remove/redact sensitive keys by role.

Acceptance: Provide `to_universal_dict(redact_for=user)`; tests for role differences.

---
 
## 9. API & DX Enhancements

### 9.1 Bulk Save / Patch Endpoint (P1 / M) [API]

Goal: Accept list of objects with version checks; return successes + conflicts.

Acceptance: 207 Multi-Status style payload or aggregated structure documented.

### 9.2 No-Op PATCH 204 Response (P2 / S) [API]

Goal: Return 204 when request results in no changes.

Acceptance: Concurrency test proves version unchanged, response 204.

### 9.3 Unified Error Codes (P2 / S) [DX]

Goal: Standardize wcapi error `code` (e.g., VERSION_CONFLICT, INVALID_FILTER).

Acceptance: All error responses include `code` field; tests updated.

### 9.4 Factory / Fixture Utilities (P2 / S) [DX]

Goal: Centralized test record builders enforcing envelope shape.

Acceptance: `tests/factories.py` with `make_contact(**overrides)` etc.

### 9.5 Snapshot Tests for Universal Dict (P3 / S) [DX]

Goal: Guard against shape regressions of to_universal_dict.

Acceptance: Failing diff when unexpected keys disappear/appear.

---
 
## 10. Resilience & Housekeeping

### 10.1 Size Threshold Escalation (P2 / S) [Observability]

Goal: Additional log levels: 75% warn (done), 90% error, >100% block.

Acceptance: Logging verified by test injecting large JSON.

### 10.2 Soft Delete Retention Policy (P3 / M) [Data]

Goal: Purge soft-deleted rows older than N days.

Acceptance: Management command + dry run flag.

### 10.3 Keyword Refresh Backpressure (P3 / M) [Perf]

Goal: Skip refresh if queue length > threshold; mark for retry.

Acceptance: Simulated queue length test.

---
 
## 11. Multi-Tenancy (Future / Exploratory)

### 11.1 Tenant Key Integration (P3 / L) [Architecture]

Goal: Add `tenant_id` FK plus composite unique constraints.

Acceptance: Queries scoped by tenant in middleware.

### 11.2 Tenant-Aware Index Strategy (P3 / M)

Goal: Covering indexes considering tenant distribution.

Acceptance: Benchmarks confirm improved planner choices.

---
 
## 12. Implementation Order (Recommended 3-Phase)

Phase 1 (Stabilize Core): 1.1, 2.1, 3.1, 4.1, 6.1, 7.1, 9.1
Phase 2 (Optimize & Harden): 1.2, 3.3, 3.4, 5.2, 6.2, 7.2, 9.2, 10.1
Phase 3 (Advanced & Optional): 1.3, 2.2, 3.2, 5.1, 6.3, 7.3, 8.x, 9.3–9.5, 10.2–10.3, 11.x

---
 
## 13. Cross-Cutting Guidelines

- Keep migrations granular (one logical concern each).
- For new endpoints: add tests (happy path + conflict + boundary) before implementation where reasonable (TDD-lite).
- Record performance deltas (simple timestamp diff) for any optimization PR.
- Document new feature flags / env vars in README + CHANGELOG.
- Maintain backward compatibility; deprecate with warnings before removal.

---
 
## 14. Open Questions (Team Decision Needed)

1. Should metadata-only history updates bump version? (Current behavior: yes.)
2. Strategy for diff storage: JSON array vs separate audit table? (Space vs query speed.)
3. Naming for bulk endpoint: `/wcapi/bulk/save` vs `/wcapi/batch`.
4. Encryption scope: app-level or per-field policy object?

---
 
## 15. Tracking Template (Copy For Each Ticket)

```markdown
Title:
Context:
Goal:
Scope (In / Out):
Design Notes:
Acceptance Criteria:
Tests:
Migration Impact:
Monitoring / Metrics:
Rollout Plan:
Docs Update:
Risk & Mitigation:
```

---
 
## 16. Recently Completed (Reference)

- Optimistic concurrency (412) + If-Match wildcard.
- Strict filter opt-in + metrics + projection cache.
- dt_created / dt_modified aliases.
- changed_fields tracking & size warnings.
- Instance atomic_set / atomic_append helpers.
- Layered CI pipeline: smoke gate (marker=smoke), multi-Python matrix (fast subset then full), Postgres integration stage with Newman/Postman minimal contract test, coverage & JUnit XML artifacts per stage.
- Expanded Postman contract suite: signup/login, create via wcapi/save, get, query, version conflict attempt, allowed-fields, models metadata, metrics, negative auth (missing token), pagination & filtered query, schema baseline field presence, response time guard.
- Database configuration hardening: default dev/runtime now uses Postgres; in‑memory SQLite restricted to pytest (or explicit `USE_SQLITE_TEST=1` override) with safety warning to prevent accidental data loss / missing table errors.

---
 
## 17. Next Steps

1. Team review & adjust priorities (add owners, target sprint).
2. CI refinements:
	- (DONE) Aggregate multi-version coverage (coverage combine + single XML output).
	- (DONE) Codecov upload & badge activated (threshold 70% - ratchet later).
	- Enforce higher coverage threshold over time (currently 70%).
	- Expand Postman collection (auth flows, CRUD, error schema assertions).
	- Add Codecov (or Coveralls) upload & repository badge.
	- Consider caching Django migration state if startup time grows.
	- Postman future: expired token scenario, persisted schema snapshot file (diff on change), formal performance thresholds env-driven, negative error schema assertions, pagination cursor tests (if added), bulk save once implemented.
3. Create tickets referencing section + item number (e.g., UPG-1.1).
4. Establish weekly checkpoint reviewing Phase 1 items until complete.

---
*End of document.*
