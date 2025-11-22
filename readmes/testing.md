<!-- Replaced placeholder with authoritative content from README_s/testing.md -->

# Test & Verification Guide

<!-- TOC START -->

## Table of Contents

- [Test \& Verification Guide](#test--verification-guide)
  - [Table of Contents](#table-of-contents)
  - [1. Quick Start (most common)](#1-quick-start-most-common)
  - [2. Environment Assumptions](#2-environment-assumptions)
  - [3. Test Categories Overview](#3-test-categories-overview)
  - [4. Size Telemetry \& JSON Envelope Checks](#4-size-telemetry--json-envelope-checks)
  - [5. Org Aspect Metrics \& Validation](#5-org-aspect-metrics--validation)
  - [6. Storage Load Report (Admin Telemetry)](#6-storage-load-report-admin-telemetry)
  - [7. Optimistic Concurrency Pattern](#7-optimistic-concurrency-pattern)
  - [8. Adding New Tests](#8-adding-new-tests)
  - [9. Planned Postman and API Contract Suite](#9-planned-postman-and-api-contract-suite)
  - [10. Markers \& Layered CI Execution](#10-markers--layered-ci-execution)
  - [11. Continuous Integration (Implemented \& Next)](#11-continuous-integration-implemented--next)
  - [12. Troubleshooting](#12-troubleshooting)
  - [13. Fast Local Loop Tips](#13-fast-local-loop-tips)
  - [14. Guardrails Before Merge](#14-guardrails-before-merge)

<!-- TOC END -->

Date: 2025-09-03
Review: 2025-12-15
Status: -- status --
Owner: Bill

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
- Test runs (when `PYTEST_CURRENT_TEST` is present) auto-switch to an in‑memory SQLite database for speed/isolation. This requires no local Postgres for unit tests.
- Normal development runtime (`runserver`, management commands outside pytest) now defaults to Postgres to prevent data loss.
- Ephemeral SQLite outside pytest: export `USE_SQLITE_TEST=1` (warning printed).
- Force Postgres inside pytest: set `PYTEST_FORCE_DB=1`.

## 3. Test Categories Overview

| Category | Files | Purpose |
|----------|-------|---------|
| Core model behavior | `test_base_model_enhancements.py` | Versioning, timestamps, changed_fields, size thresholds |
| Pydantic / schema | `test_base_model_pydantic.py` | Optional typed representation behavior |
| Atomic JSON ops | `test_atomic_json_updates.py` | `atomic_json_set`, `atomic_list_append`, concurrency guard |
| Universal API endpoints | `test_universal_api*.py` | Generic list/get/patch semantics & filter rules |
| Filters / validation | `test_wcapi_invalid_filters.py`, `test_wcapi_strict_filters.py` | Allowed filters & strict mode |
| Concurrency & If-Match | `test_wcapi_if_match.py`, `test_wcapi_concurrency.py` | Optimistic locking |
| Errors & edge cases | `test_wcapi_errors.py` | Error payload codes |
| Keywords / refs | `test_keywords_property.py` | Keyword extraction & flags |
| Capabilities API | `test_capabilities.py` | `model_capabilities()` discovery |
| Transactions / line items | `test_transaction_lines.py` | Domain specific integrity checks |
| BOM integrity & cost | `test_bom_cycle_and_rollup.py` | Cycle prevention & cost roll‑up |
| BOM API endpoints | `apps/products/tests/test_bom_api.py` | BOM list/create contract |

## 4. Size Telemetry & JSON Envelope Checks

Progressive size logging at threshold percentages. To manually inspect:

```bash
python manage.py shell <<'PY'
from common import models
# Example manipulations here
PY
```

## 5. Org Aspect Metrics & Validation

See `manage.md` for `org_aspect_metrics` and validation command details. Typical test usage examples:

```python
ok, errs = org.validate_aspects()
```

## 6. Storage Load Report (Admin Telemetry)

```bash
python manage.py storage_load_report --field metadata --limit 100
```

## 7. Optimistic Concurrency Pattern

1. Fetch object & note `version`.
2. PATCH/PUT with `If-Match` header.
3. Expect 412 if stale.

## 8. Adding New Tests

- Place new files under `tests/` prefixed with `test_`.
- Favor focused unit tests; add integration only when necessary.
- Keep envelope contract assertions up to date.

## 9. Planned Postman and API Contract Suite

Placeholder workflow for Newman automation; see future updates.

## 10. Markers & Layered CI Execution

Markers create feedback loops: `smoke`, `fast`, `bill_of_material`, full. Use `-m` and `-k` to scope.

## 11. Continuous Integration (Implemented & Next)

Stages: smoke → matrix → integration → coverage aggregate. Artifacts: JUnit XML + coverage per stage. See `.github/workflows/ci.yml`.

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Missing table errors | Using ephemeral DB | Run migrations / disable `USE_SQLITE_TEST` |
| Version conflicts | Stale version header | Refetch & retry |
| Size warnings | Large JSON growth | Inspect field diffs |

## 13. Fast Local Loop Tips

`./bin/pytest -k substring`, `--lf`, `--ff`, combine markers.

## 14. Guardrails Before Merge

Checklist (adopt with Postman suite): tests green, contract tests green, no unexpected size warnings, storage utilization sane.

---
Questions or gaps: open an issue referencing this file and affected test file.
