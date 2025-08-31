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
- PostgreSQL running & Django settings point at a test database (pytest will create/tear down as needed).
- Redis / Celery only required if you explicitly run tasks tests (none are mandatory for core model suite right now).

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

## 10. Continuous Integration Suggestions (Future)

- Matrix: Python versions (keep minimal if not needed).
- Steps: install deps -> run `./bin/pytest -q` -> run Postman (Newman) -> optional coverage threshold.
- Artifact: store JUnit XML from both pytest (`-q --junitxml=pytest-results.xml`) and newman.

## 11. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Failing concurrency tests | Version mismatch | Ensure you refresh object before updating |
| Unexpected size warning spam | Re-saving without metadata.versioning.size_activity persisted | Confirm model inherits full BaseModel & metadata saved |
| Management command shows 0 sizes | Field empty or model not inheriting BaseModel | Verify model mixins |
| ImportError Pydantic tests skipped | pydantic not installed | Add to requirements if typed schema needed |

## 12. Fast Local Loop Tips

- Use `-k` to filter by substring: `./bin/pytest -k atomic_json`.
- Use `--lf` (last-failed) or `--ff` (failed-first) for iterative debugging.
- Keep logs readable: optionally set `PYTEST_ADDOPTS='-q'` in env.

## 13. Guardrails Before Merge

(Adopt once Postman suite lands)

- [ ] Python unit/integration tests green
- [ ] Postman contract tests green
- [ ] No unexpected new size threshold warnings in logs (scan CI log tail)
- [ ] storage_load_report shows utilization < planned offload threshold for new data structures

---

Questions or gaps: open an issue referencing this file and the affected test file.
