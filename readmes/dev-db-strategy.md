# Development DB Strategy: SQLite Fast Path + Postgres Validation


<!-- TOC START -->

## Table of Contents

- [Development DB Strategy: SQLite Fast Path + Postgres Validation](#development-db-strategy-sqlite-fast-path-postgres-validation)
  - [Why SQLite (Right Now)](#why-sqlite-right-now)
  - [Guardrails / Caveats vs Postgres](#guardrails-caveats-vs-postgres)
  - [Workflow](#workflow)
  - [Quick Environment Switch](#quick-environment-switch)
- [SQLite fast path (default during churn)](#sqlite-fast-path-default-during-churn)
- [Switch to Postgres (assuming env vars or .env configured)](#switch-to-postgres-assuming-env-vars-or-env-configured)
  - [Recommended Make Targets (Future)](#recommended-make-targets-future)
  - [What Still NEEDS Postgres Early](#what-still-needs-postgres-early)
  - [Exit Criteria (Switch Team Back to Postgres by Default)](#exit-criteria-switch-team-back-to-postgres-by-default)
  - [Minimal Parity Checklist (Run on Postgres)](#minimal-parity-checklist-run-on-postgres)
  - [Risks if Postgres Lane Is Neglected](#risks-if-postgres-lane-is-neglected)
  - [Suggested CI Additions](#suggested-ci-additions)
  - [FAQ](#faq)
  - [Summary](#summary)

<!-- TOC END -->

This project is in a heavy schema churn phase ("massive changes"). For speed, we adopt a dual‑lane approach: **SQLite for rapid local iteration** and **Postgres for continuous validation**.

## Why SQLite (Right Now)

- Instant `makemigrations` + `migrate` cycles (especially after squashed baseline)
- Disposable data encourages fearless refactors
- Zero external service dependency (onboarding simplicity)

## Guardrails / Caveats vs Postgres

| Concern | SQLite Behavior | Postgres Behavior / Risk |
|---------|-----------------|---------------------------|
| Concurrency / Locks | Serialized writes; fine for single dev requests | Real row/page locks; subtle race conditions may hide under SQLite |
| JSON / JSONB | Basic JSON stored as text | JSONB operators, indexing, containment queries differ |
| Index / Query Plans | Limited optimizer features | Advanced GIN/GIST/partial indexes; performance assumptions can diverge |
| Constraints | Some deferred / advanced constraint edge cases not exercised | Full enforcement; may reveal migration or data issues |
| Data Types | More permissive coercions | Strict typing; mismatched casts can break queries |
| Case/Ordering | Collation differences can alter ordering | Production ordering may differ without explicit `order_by` |
| Performance Tuning | Not representative | Needed for realistic latency & locking behavior |

## Workflow

1. Local dev: export `USE_SQLITE_TEST=1` (already respected in `settings.py`).
2. Iterate: models, migrations, seed sample (`python manage.py seed_sample_products`).
3. Before push (or pre-PR hook): run full pytest suite against Postgres (Docker or local service).  
4. CI: Always uses Postgres to catch divergences early.
5. Nightly (or milestone): snapshot Postgres schema + run parity checks (schema integrity, key JSON queries, inventory scheduling logic).

## Quick Environment Switch

```bash
# SQLite fast path (default during churn)
export USE_SQLITE_TEST=1

# Switch to Postgres (assuming env vars or .env configured)
unset USE_SQLITE_TEST
python manage.py migrate
```

## Recommended Make Targets (Future)

```makefile
make dev-sqlite      # sets USE_SQLITE_TEST=1 and runs migrate
make dev-pg          # unsets flag, ensures postgres is up, migrate
make test-pg         # forces Postgres test run
```

## What Still NEEDS Postgres Early

- JSON containment / advanced filters
- Performance-sensitive aggregation queries
- Any GIN / partial index dependent feature (search, keyword stats)
- Concurrency features (reservation races, inventory adjustments)

## Exit Criteria (Switch Team Back to Postgres by Default)

- Schema stabilizes (few structural changes per day)
- Need to validate index performance or query plans
- Preparing staging / production parity rehearsal
- Onboarding non-core devs who should see production‑like behavior

## Minimal Parity Checklist (Run on Postgres)

- [ ] `python manage.py migrate` clean
- [ ] `pytest -q` green
- [ ] Catalog + OrgItem invariant test (no threshold inversions, metric drift < 5%)
- [ ] JSONField queries (sample) return identical logical results as on SQLite seed
- [ ] Inventory scheduling: at least one OrgItem gets computed `dt_next_check`

## Risks if Postgres Lane Is Neglected

| Risk | Outcome |
|------|---------|
| Drift in JSON query semantics | Production API filter failures |
| Missing index performance issues | Slow endpoints under real data volume |
| Undetected constraint differences | Migration failures at deploy time |
| Latent race conditions | Intermittent production bugs (double reservations, stale counts) |

## Suggested CI Additions

- Matrix: `{ DB=sqlite, DB=postgres }` for a small critical subset of tests.
- Postgres-only job: run invariants + performance smoke (threshold queries, reservation logic).

## FAQ

**Will React frontend behave differently?**  
No—front end hits the same API contract. Differences are server-side perf & query semantics (caught by Postgres lane).

**Can we ship while still on SQLite locally?**  
Yes, provided Postgres CI is green and parity checklist passes.

**What about data snapshots?**  
Use Postgres lane to generate realistic fixtures; avoid bloating rapid SQLite cycle.

## Summary

Use SQLite for speed *now*, but never lose a continuous Postgres validation path. This hybrid keeps iteration velocity high while containing risk.
