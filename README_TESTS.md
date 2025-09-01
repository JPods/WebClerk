# Test & Verification Guide

This document explains how to run and extend the automated + manual (API/Postman) test suites for the Universal API / BaseModel platform.

## 1. Quick Start (most common)

Run the full Python test suite (quiet mode):

```bash
./bin/pytest -q
```

Verbose (see individual test names):

```bash
./bin/pytest -vv
```

Single test file:

```bash
./bin/pytest tests/test_universal_api.py::test_basic_get
```

Stop on first failure:

```bash
./bin/pytest -x
```

Coverage (if `coverage` installed):

```bash
coverage run -m pytest && coverage report -m
```

## 2. Environment Assumptions

- Local virtualenv already activated via `source bin/activate` (repo ships a venv layout).
- By default test runs auto-switch to an in‑memory SQLite database for speed/isolation. This requires **no** local Postgres for unit tests.
- To force Postgres for integration testing set `PYTEST_FORCE_DB=1` or `USE_SQLITE_TEST=0` in the environment before invoking pytest.
- Redis / Celery only required if you explicitly run tasks tests (none are mandatory for core model suite right now).

Example forcing Postgres:

```bash
PYTEST_FORCE_DB=1 ./bin/pytest -q
```

Or explicitly disabling SQLite shortcut:

```bash
USE_SQLITE_TEST=0 ./bin/pytest -q
```

## 3. Test Categories Overview

| Category | Files | Purpose |
|----------|-------|---------|
| Core model behavior | `test_base_model_enhancements.py` | Versioning, timestamps, changed_fields, size thresholds |
| Pydantic / schema | `test_base_model_pydantic.py` | Optional typed representation behavior |
| Atomic JSON ops | `test_atomic_json_updates.py` | `atomic_json_set`, `atomic_list_append`, concurrency guard |
| Universal API endpoints | `test_universal_api*.py` | Generic list/get/patch semantics & filter rules |
| Filters / validation | `test_wcapi_invalid_filters.py`, `test_wcapi_strict_filters.py` | Ensures only allowed filters & strict mode behavior |
| Concurrency & If-Match | `test_wcapi_if_match.py`, `test_wcapi_concurrency.py` | Optimistic locking / version conflict handling |
| Errors & edge cases | `test_wcapi_errors.py` | Error payload shape & codes |
| Keywords / refs | `test_keywords_property.py` | Keyword extraction & flags |
| Capabilities API | `test_capabilities.py` | `model_capabilities()` discovery |
| Transactions / line items | `test_transaction_lines.py` | Domain specific integrity checks |
| BOM integrity & cost | `test_bom_cycle_and_rollup.py` | Cycle prevention & component cost roll‑up |

## 4. Size Telemetry & JSON Envelope Checks

Recent additions introduce progressive size logging at 30%, 60%, 75% of the configured caps (see `common/models.py` constants). Failures occur only if a cap is exceeded; thresholds before that only log. To manually sanity‑test:

```bash
python manage.py shell <<'PY'
from common import models
# (Assuming a concrete model e.g. products.Product extends BaseModel)
# p = Product.objects.create(ida='demo')
# Manipulate p.metadata / p.refs to approach thresholds then p.save()
PY
```

Check logs for info/warning lines.

## 5. Org Aspect Metrics & Validation

Unified organization aspects (OrgBase) add validation & telemetry helpers supporting tests:

| Tool | Purpose | Test Usage |
|------|---------|------------|
| `org_aspect_metrics` | Aggregates per-aspect item counts & JSON byte sizes | Assert growth stays within expected bounds pre/post factory runs |
| `org_validate_aspects` | Validates rows against Pydantic schema | CI gate to prevent malformed aspect payloads |
| `OrgBase.validate_aspects()` | In-Python snapshot / patch validation | Direct assertions inside unit tests when building complex org payloads |

Example (full snapshot):

```python
from apps.orgs.models import OrgBase

def test_org_aspects_schema_valid():
   org = OrgBase.objects.create(org_type="customer", display_name="Acme", status="active")
   ok, errs = org.validate_aspects()
   assert ok, errs
```

Example (patch):

```python
payload = {"contacts": [{"name": "Jane Smith", "role": "buyer"}]}
ok, errs = org.validate_aspects(partial=True, data=payload)
assert ok, errs
```

Operational details & advanced CLI flags live in `README_MANAGE.md` to avoid duplication.

## 6. Storage Load Report (Admin Telemetry)

A management command summarizes JSON field utilization:

```bash
python manage.py storage_load_report --field metadata --limit 100
python manage.py storage_load_report --json
```

Use this before large migrations or enabling JSON offload.

## 7. Optimistic Concurrency Pattern

Tests validate that updates must provide the correct version (If-Match semantics). When writing new tests around partial updates:

1. Fetch object, note `version`.
2. Perform modifying request with `If-Match: <version>` or param.
3. Expect 409 / VersionConflictError if stale.

## 8. Adding New Tests

- Place files under `tests/` prefixed with `test_`.
- Favor small, focused tests over broad integration when possible.
- Use existing factories / fixtures (if present) to avoid duplication.
- If adding new JSON envelope size caps, assert both below and above boundary behavior.

## 9. (Planned) Postman / API Contract Suite

A curated Postman collection will be added to enforce endpoint contract stability before merge. Placeholder workflow:

1. Export collection to `api_tests/UniversalAPI.postman_collection.json`.
2. Add an environment file for local dev variables.
3. Provide a helper script:
   
   ```bash
   newman run api_tests/UniversalAPI.postman_collection.json -e api_tests/local.postman_environment.json --reporters cli,junit --reporter-junit-export postman-results.xml
   ```
   
4. Gate CI merge on zero failures + Python tests green.

(Section will be updated once the collection is committed.)

## 10. Markers & Layered CI Execution

Pytest markers establish concentric feedback loops:

| Marker | Scope | Purpose | Typical Runtime |
|--------|-------|---------|-----------------|
| `smoke` | Single ultra-fast sanity test (basic model create) | Instant validation that environment & Django wiring load | < 2s |
| `fast` | Subset: BOM + smoke + a few core paths | Domain logic confidence without full suite cost | ~ under 5–10s (depends on additions) |
| `bom` | All Bill of Material integrity/cost tests | Targeted development on BOM model | Similar to fast minus other fast tests |
| (none) | Full suite | Comprehensive regression | Longest |

Usage examples:

```bash
./bin/pytest -m smoke -q
./bin/pytest -m fast -q
./bin/pytest -m bom -q
./bin/pytest -q          # full
```

Combine with -k if needed (e.g. `-m fast -k cost`).

CI Workflow (implemented in `.github/workflows/ci.yml`):

1. smoke job (Python 3.13) runs only `-m smoke` and must pass before heavier jobs begin.
2. tests matrix runs on Python 3.11, 3.12, 3.13:
   - Executes `-m fast` first (early fail) then full suite.
3. Environment defaults to in‑memory SQLite via `USE_SQLITE_TEST=1` unless future integration job enables Postgres.

Rationale: Fail fast on wiring errors (import/migrations), then domain subset, then full regression minimizing wasted CI minutes.

Extending:

- Add new super‑fast tests to `smoke` only if they remain sub‑second.
- Broader but still quick domain tests can join `fast`.
- Do not bloat `smoke` with DB-heavy or multiple-object scenarios.


Generating JUnit / coverage (optional enhancement):

```bash
./bin/pytest -m fast --junitxml=pytest-fast.xml --cov=.
```

## 11. Continuous Integration (Implemented & Next)

Implemented stages (`.github/workflows/ci.yml`):

1. Smoke (SQLite, Python 3.13) – runs `-m smoke`, uploads JUnit.
2. Matrix (3.11 / 3.12 / 3.13, SQLite) – runs fast subset with coverage + JUnit, then full suite (coverage & JUnit artifacts per Python version).
3. Integration (Postgres service) – runs integration‑marked tests against real Postgres, generates coverage (partial) + JUnit, then spins up Django and executes a minimal Postman collection via Newman producing JUnit XML.
4. Coverage aggregate job – downloads per-version `.coverage.*` files + integration, combines, enforces `COVERAGE_FAIL_UNDER` (default 70%).

Artifacts:
 
- `pytest-smoke.xml`, `pytest-fast-<py>.xml`, `pytest-full-<py>.xml`, `pytest-integration.xml`.
- Coverage XML per Python runtime + integration (can be aggregated later by an external tool if desired).
- `postman-results.xml` for contract tests.
- `.coverage.*` raw data shards + combined `coverage-combined.xml` (after aggregation job).

Codecov (optional): uncomment the Codecov step in `coverage-aggregate` job and add `CODECOV_TOKEN` (if private repo) to publish and replace the placeholder badge in `README.md`.

Postman collection now covers:

- Signup (creates user or handles existing)
- Login (JWT issuance)
- Authenticated wcapi/save contact create
- wcapi/get single fetch
- wcapi/query list fetch
- Version conflict simulation (If-Match header artificial stale)
- Allowed fields utility endpoint
- Models metadata endpoint
- Metrics endpoint
- Negative auth (missing token) acceptance (expects 401/403 unless relaxed dev flag allows 200)
- Pagination & filtered query (limit & name_first filter)
- Schema snapshot baseline fields presence (contacts)
- Response time guard (< 1200ms) for contacts query
Each step asserts HTTP status and minimal contract invariants (id propagation, non-empty results).

Next enhancement ideas:
 
- Aggregate multi-version coverage (e.g., use coverage combine + upload single report).
- Enforce coverage threshold (add `coverage report --fail-under=<pct>`).
- Expand Postman collection to assert contract (status codes, schema fragments) & add auth flows.
- Cache pip + possibly a pre-migration SQLite DB if start-up becomes slower.
- Add Codecov / Coveralls upload & badge.

## 12. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Failing concurrency tests | Version mismatch | Ensure you refresh object before updating |
| Unexpected size warning spam | Re-saving without metadata.versioning.size_activity persisted | Confirm model inherits full BaseModel & metadata saved |
| Management command shows 0 sizes | Field empty or model not inheriting BaseModel | Verify model mixins |
| ImportError Pydantic tests skipped | pydantic not installed | Add to requirements if typed schema needed |
| `no such table: settings` in early tests | Signals firing before tables exist on SQLite | Already mitigated with table introspection; ensure latest code |
| Test suite still using Postgres when undesired | Env forcing Postgres | Unset `PYTEST_FORCE_DB` / set `USE_SQLITE_TEST=1` |

## 13. Fast Local Loop Tips

- Use `-k` to filter by substring: `./bin/pytest -k atomic_json`.
- Use `--lf` (last-failed) or `--ff` (failed-first) for iterative debugging.
- Keep logs readable: optionally set `PYTEST_ADDOPTS='-q'` in env.

## 14. Guardrails Before Merge

(Adopt once Postman suite lands)

- [ ] Python unit/integration tests green
- [ ] Postman contract tests green
- [ ] No unexpected new size threshold warnings in logs (scan CI log tail)
- [ ] storage_load_report shows utilization < planned offload threshold for new data structures

---

Questions or gaps: open an issue referencing this file and the affected test file.
