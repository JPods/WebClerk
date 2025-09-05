# webClerk3


<!-- TOC START -->

## Table of Contents

- [webClerk3](#webclerk3)
  - [Table of Contents](#table-of-contents)
  - [Project Docs](#project-docs)
  - [Contributors](#contributors)
  - [Documentation Map](#documentation-map)
  - [Data Basics](#data-basics)
  - [Path Basics](#path-basics)
  - [Install](#install)
    - [Enable Coverage Badge (Codecov)](#enable-coverage-badge-codecov)
    - [Normal run](#normal-run)
    - [Port already in use](#port-already-in-use)
    - [Schema changes (add/remove/modify columns)](#schema-changes-addremovemodify-columns)
    - [First time setup](#first-time-setup)
- [or: psql -U williamjames -d postgres](#or-psql-u-williamjames-d-postgres)
    - [Reset Postgres (if issues)](#reset-postgres-if-issues)
  - [Git Workflow](#git-workflow)
  - [Running Tests](#running-tests)
    - [Test Database Strategy](#test-database-strategy)
  - [🎯 Architecture Overview](#architecture-overview)
    - [Pattern Structure (dev without front end)](#pattern-structure-dev-without-front-end)
    - [Universal API Endpoints](#universal-api-endpoints)
  - [Universal API Usage Examples](#universal-api-usage-examples)
    - [View All Contacts](#view-all-contacts)
    - [View Specific Contact](#view-specific-contact)
    - [Manage Contact's Emails](#manage-contacts-emails)
    - [Create New Action](#create-new-action)
    - [API Data Retrieval](#api-data-retrieval)
    - [Key Features](#key-features)
    - [New: Bill of Material (BOM) API (Experimental)](#new-bill-of-material-bom-api-experimental)
    - [Unified Response Envelope](#unified-response-envelope)
    - [Operational Headers](#operational-headers)
    - [Client Migration Checklist](#client-migration-checklist)
    - [Pagination (Universal Query)](#pagination-universal-query)
    - [Field Projection (Selective Columns)](#field-projection-selective-columns)
    - [Optimistic Concurrency (Universal Save)](#optimistic-concurrency-universal-save)
    - [Strict Filter Mode (Opt-In)](#strict-filter-mode-opt-in)
    - [Filtering Infrastructure (django-filter)](#filtering-infrastructure-django-filter)
    - [Metrics Backend Options](#metrics-backend-options)
    - [Projection Field Cache](#projection-field-cache)
    - [Metrics Endpoint](#metrics-endpoint)
- [HELP wcapi_requests_total Total WCAPI requests](#help-wcapirequeststotal-total-wcapi-requests)
- [TYPE wcapi_requests_total counter](#type-wcapirequeststotal-counter)
- [HELP wcapi_request_duration_seconds Request duration seconds](#help-wcapirequestdurationseconds-request-duration-seconds)
- [TYPE wcapi_request_duration_seconds summary](#type-wcapirequestdurationseconds-summary)
    - [Model Registry & Security Hardening](#model-registry-security-hardening)
    - [Error Path Guarantees](#error-path-guarantees)
    - [Extending the Universal API](#extending-the-universal-api)
    - [Navigation Structure](#navigation-structure)
  - [Model Visualization](#model-visualization)
  - [Celery Monitoring](#celery-monitoring)
  - [Keyword Refresh System (Universal API Search Index)](#keyword-refresh-system-universal-api-search-index)
  - [API Rate Limiting](#api-rate-limiting)
  - [Logging](#logging)
  - [Transaction Line & Aggregation Endpoints](#transaction-line-aggregation-endpoints)
    - [Field-Level Authorization (view_edit)](#field-level-authorization-viewedit)
  - [Running Tests](#running-tests)
  - [Deployment (Placeholder)](#deployment-placeholder)
  - [Environment Variables](#environment-variables)
  - [API Documentation Access (Placeholder)](#api-documentation-access-placeholder)
  - [Internationalization (i18n)](#internationalization-i18n)
  - [Production Deployment (Placeholder)](#production-deployment-placeholder)
  - [Optimistic Concurrency & Atomic JSON PATCH (Universal API)](#optimistic-concurrency-atomic-json-patch-universal-api)
    - [Why](#why)
    - [Core Pieces](#core-pieces)
    - [PATCH Payload Contract (Atomic)](#patch-payload-contract-atomic)
    - [Fallback (Non-atomic) Partial Update](#fallback-non-atomic-partial-update)
    - [Example Flow](#example-flow)
    - [Error Responses](#error-responses)
    - [Extending To Another Model](#extending-to-another-model)
    - [Design Rationale](#design-rationale)
    - [Future Enhancements](#future-enhancements)
  - [Modular BaseModel & CoreModel (Capability Composition)](#modular-basemodel-coremodel-capability-composition)
    - [Mixins & Capabilities](#mixins-capabilities)
    - [Choosing a Composition](#choosing-a-composition)
    - [Example Compositions](#example-compositions)
    - [Pending (Queue) Example](#pending-queue-example)
    - [Migrating an Existing Full Model to a Leaner Composition](#migrating-an-existing-full-model-to-a-leaner-composition)
    - [Capability Introspection](#capability-introspection)
    - [Design Principles](#design-principles)
    - [Why Not Just Two Bases?](#why-not-just-two-bases)
    - [Pydantic Integration](#pydantic-integration)
    - [Future Extensions](#future-extensions)
  - [Consistency Standards (All Apps / Models)](#consistency-standards-all-apps-models)
- [serializers/myresource.py](#serializersmyresourcepy)
- [views/myresource.py](#viewsmyresourcepy)

<!-- TOC END -->

<!-- CI Badges (add actual URLs once Codecov token configured in repo secrets) -->
![CI](https://github.com/JPods/webClerk3/actions/workflows/ci.yml/badge.svg)
<!-- Replace OWNER/REPO in next line once Codecov enabled; token not needed for public repos -->
![Coverage](https://codecov.io/gh/JPods/webClerk3/branch/main/graph/badge.svg)
![Coverage bill_dev](https://codecov.io/gh/JPods/webClerk3/branch/bill_dev/graph/badge.svg)


## Project Docs

[Google Docs](https://docs.google.com/document/d/1a8ZYgSVpJsa6VhhEPkW5bOreRfY4mZ0tuRk0NHJIFJI/edit?usp=sharing)


## Contributors

- Antor Ahmed
- Riju Karar
- Samir Biswas
- Sanjutka Patra
- CoPilot
- Bill James

## Documentation Map

Authoritative guides are split by concern (single source each, no duplication):

- Core onboarding & architecture: this README
- Data / model structure map: `readmes/data-map.md`
- Management & Operations: `readmes/manage.md`
- Inventory & Costing: `readmes/inventory.md`
- Flow vs Inventory Domain Boundary: `readmes/flow-vs-inventory.md`
- Testing & Verification: `readmes/testing.md`
- Upgrade Roadmap: `readmes/upgrade.md`
- Rules & Guidelines: `readmes/rules.md`
- Service Billing Guide: `readmes/service_billing.md`
- Service JSON Schemas: `readmes/service_schemas.md`
- Table Registry & Permissions: `readmes/table-registry-and-permissions.md`

If you add >~15 lines of procedural or reference material, place it in the appropriate doc file under `readmes/` and add (or update) a single-line link here instead of duplicating.

## Data Basics


Commands (in `common/management/commands`):

```bash
python manage.py demo_data_import_export export
python manage.py demo_data_import_export import
```

If needed (example):

```sql
DROP TABLE IF EXISTS pending CASCADE;
```

Location: `common/management/commands/`  
Data file: `all_tables_export.json`

Export/import data (avoid exporting or importing rows still marked pending):

```bash
python manage.py demo_data_import_export export
python manage.py demo_data_import_export import
```
Seed data:
python manage.py seed_minimal_if_empty.py

```bash
python -m venv .
source ./bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

3-column admin reference: [Grok Link](https://grok.com/share/c2hhcmQtMg%3D%3D_427dc198-2378-41ef-b3c5-c77d1e4e1062)

## Path Basics

```text
webClerk3/
├── apps/
│   ├── core/
│   │   ├── models/
│   │   ├── views/
│   │   ├── services/
│   │   ├── templates/
│   │   └── ...
│   ├── communications/
│   │   ├── models/
│   │   ├── views/
│   │   └── ...
│   └── accounts/
│       ├── models/
│       └── ...
├── templates/
├── common/
│   └── management/commands/
└── webclerk3_api/
  ├── settings.py
  ├── celery_app.py
  └── ...
```

## Install

Prerequisites:

- Celery
- Redis
- Pydantic (optional – JSON typing) – video: [YouTube](https://www.youtube.com/watch?v=XIdQ6gO3Anc)
- (Optional) Codecov account for coverage reporting (add CODECOV_TOKEN secret if repository private).

### Enable Coverage Badge (Codecov)

1. Sign in to Codecov with GitHub and add the repository.
2. If the repo is private, create a `CODECOV_TOKEN` in Codecov settings.
3. In GitHub repo settings add repository secret `CODECOV_TOKEN`.
4. Update workflow to upload combined coverage (see commented snippet in `ci.yml`).
5. Replace placeholder badge above with:

```markdown
![Coverage](https://codecov.io/gh/JPods/webClerk3/branch/main/graph/badge.svg)
```

For a branch badge (e.g. bill_dev):

```markdown
![Coverage bill_dev](https://codecov.io/gh/JPods/webClerk3/branch/bill_dev/graph/badge.svg)
```


### Normal run

```bash
source ./bin/activate
python manage.py runserver
```

### Port already in use

```bash
kill -9 $(lsof -t -i :8000)
```

### Schema changes (add/remove/modify columns)

```bash
source ./bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

### First time setup

```bash
python -m venv .
source ./bin/activate
pip install -r requirements.txt
psql -U an7or -d postgres
# or: psql -U williamjames -d postgres
CREATE DATABASE commerce_expert;
rm */migrations/0*.py || true
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py view_edit_to_settings
python manage.py runserver
```

### Reset Postgres (if issues)

```bash
source ./bin/activate
psql -U an7or -d postgres
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'commerce_expert' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS commerce_expert;
CREATE DATABASE commerce_expert;
rm */migrations/0*.py || true
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py view_edit_to_settings
python manage.py runserver
```

## Git Workflow

Daily start:

```bash
API requests and errors are logged to `webclerk3.log`.
python manage.py check_services  # or ./check_services.sh
```

After changes:

```bash

## Running Tests

### Test Database Strategy

The settings module now auto-selects an in-memory SQLite database during pytest runs (detected via `PYTEST_CURRENT_TEST`) for speed and isolation, while normal development / `runserver` defaults to Postgres for persistence. Previously a `conftest.py` fixture forced SQLite; that override has been removed to avoid duplication and accidental masking of Postgres integration tests.

Environment variables:

| Var | Purpose | Typical Use |
|-----|---------|-------------|
| `PYTEST_FORCE_DB=1` | Force Postgres inside pytest | Run integration / migration-sensitive tests |
| `USE_SQLITE_TEST=1` | Force ephemeral in-memory SQLite even outside pytest (warning printed) | One-off throwaway experiments |
| (unset) | Default behavior (SQLite in pytest, Postgres otherwise) | Standard workflow |

If you unexpectedly see auth errors like `no such table: contacts` outside pytest, ensure you did not export `USE_SQLITE_TEST=1` and that migrations have been applied (`python manage.py migrate`).

Deeper details & scenarios: see `README_TESTS.md` (Environment Assumptions section).

```

Create PR:

1. Visit: <https://github.com/JPods/webClerk3/branches>
2. Open Pull Requests tab
3. New pull request (dev <- your_branch)
4. Complete review steps

## 🎯 Architecture Overview

**Universal API System** – One API pattern handles all data operations (contacts, actions, emails, phones, domains, addresses).

### Pattern Structure (dev without front end)

```text
core/templates/
├── base.html
├── core/
│   ├── home.html
│   ├── about.html
│   └── contact.html
└── auth/
  ├── login.html
  └── signup.html
```

### Universal API Endpoints

Details listed below with examples.

## Universal API Usage Examples

Source: `webclerk3/core/urls.py`

### View All Contacts

`http://localhost:8000/wcapi/manage/?table_name=contacts`

### View Specific Contact

`http://localhost:8000/wcapi/manage/?table_name=contacts&id=123`

### Manage Contact's Emails

`http://localhost:8000/wcapi/manage/?table_name=emails&contact_id=123`

### Create New Action

`http://localhost:8000/wcapi/manage/?table_name=actions&mode=create`

### API Data Retrieval

`http://localhost:8000/wcapi/get/?table_name=contacts&id=123`

### Key Features

✅ **Universal API** – One pattern for all tables  
✅ **Contact-Centric** – Everything revolves around contacts  
✅ **Relationship Management** – JSON refs system  
✅ **Lesson1-Style Navigation** – Clean, emoji-driven nav  
✅ **Bootstrap 5 UI** – Modern, responsive design  
✅ **Django Default 404** – Developer-friendly error pages  
✅ **Consolidated Patterns** – All in core/templates/  
✅ **Future-Proof** – Ready for React front-end migration

### New: Bill of Material (BOM) API (Experimental)

Lightweight REST endpoints expose BOM lines for bundle/assembly style items:

Base path: `/products/bom/`

Endpoints:

- `GET /products/bom/<parent_id>/` – List BOM lines for parent item (ordered by sequence then id). Optional query params: `revision=<rev>` and `as_of=YYYY-MM-DD` (future enrichment for effective windows).
- `POST /products/bom/<parent_id>/` – Create a BOM line for parent. Required fields: `component_id`, `quantity`. Optional: `scrap_factor`, `sequence`, `is_alternate`, `alternate_group`, `is_optional`, `revision`, `effective_from`, `effective_to`, `change_reason`, `op_data`.
- `GET /products/bom/line/<id>/` – Retrieve a single BOM line.
- `PATCH /products/bom/line/<id>/` – Partial update of a line (same writable fields as create).
- `DELETE /products/bom/line/<id>/` – Remove a BOM line.
- `POST /products/bom/<parent_id>/recalc/` – Recompute and persist parent cost component snapshot aggregate (writes to `item.cost.components.snapshot_total` or `default_cost`).

Serializer returns: `id, parent, component, revision, effective_from, effective_to, quantity, scrap_factor, yield_pct, sequence, is_alternate, alternate_group, is_optional, cost_snapshot, op_data, change_reason, dt_last_recalc, dt_created, dt_modified, is_active`.

Notes / Roadmap:

- Initial version does not yet enforce effective date window filtering (placeholder logic kept simple) – planned enhancement will respect `effective_from`/`effective_to` via query param `as_of`.
- No pagination required now (expected small component counts); add if parent BOMs exceed practical limits.
- Access restricted to authenticated users; future permission hook may scope by product ownership / role.
- `is_active` currently ignored in list filtering (all lines returned). Soft-disable behavior can be added later.
- Test coverage introduced in `apps/products/tests/test_bom_api.py` (basic list/create). Extend with patch/delete and cost roll-up assertions.


### Unified Response Envelope

Concise summary: All API endpoints emit a normalized JSON envelope (`status`, optional `message`, optional `data`, optional `error{code,details}`, optional `meta{...}`). The legacy boolean `success` flag is removed. Error codes are stable machine identifiers (e.g. `validation_error`, `not_found`). Middleware + exception handlers guarantee shape; deliberate bypasses are logged in tests.

Full canonical spec, error code table, pagination meta rules, test guidance, and versioning policy: see `webclerk/readmes/envelope.md`.

### Operational Headers

`RequestLogMiddleware` adds `X-Request-ID` and processing duration. Propagate `request_id` into the envelope `meta` if correlation beyond headers is needed (future enhancement).

### Client Migration Checklist

1. Assume envelope always present; ignore any prior raw handling branches.
2. Inspect `status`; treat non-`success` as failure even if HTTP 2xx (we currently align HTTP status with semantic status, but guard regardless).
3. Use `error.code` for program logic (NOT message text).
4. Safely ignore unknown keys (forward compatibility).
5. Log / surface `meta.request_id` when present for cross-service tracing.
Provide a schema component in OpenAPI (spectacular) describing the envelope for reuse via `extend_schema(responses=...)` to cut duplication. (Planned)

Usage Pattern (simple view):

```python
from common.api_responses import api_response

def sample_view(request):
  data = {"foo": "bar"}
  return api_response(data=data)
```

Open Questions / TODOs:

- Should delete responses unify on HTTP 200 + message, or 204 with empty envelope? (Currently 200 + message for enveloped deletes.)
- Decide on enforcing `success` vs `error` purely from HTTP status class (e.g. always map non-2xx to error) – middleware today only auto-wraps success style.
- Add test harness ensuring all non-exempt API paths include `status` key (contract test).

### Pagination (Universal Query)

All list responses now include:

```json
{
  "status": "success",
  "table_name": "contacts",
  "data": [ ... ],
  "total": 123,      // total rows matching filters (before limit/offset)
  "limit": 25,       // page size actually applied (capped at 50)
  "offset": 0        // starting row
}
```

Client supplies `?limit=` and `?offset=` (GET) or includes them in JSON body (POST). Server enforces `MAX_RESULTS = 50` hard cap.

### Field Projection (Selective Columns)

Reduce payload size by requesting only specific fields:

```http
GET /wcapi/query/?table_name=contacts&fields=id,email,name_first
```

or JSON list (URL encoded):

```http
GET /wcapi/query/?table_name=contacts&fields=["id","email"]
```

POST body variant:

```json
{
  "table_name": "contacts",
  "fields": "id,email,name_first",
  "company": "Acme"  // normal filters still allowed
}
```

Invalid / unknown fields → `400` with `{"status":"error","message":"Invalid field(s): ..."}`. At least one field must remain; empty list is rejected.

### Optimistic Concurrency (Universal Save)

Updates can include a `version` field (preferred) or an `If-Match` header to avoid lost writes. (Legacy `expected_version` is still accepted for now but will be removed.)

```http
POST /wcapi/save/
{"table_name":"contacts","id":7,"version":3,"name_first":"Ada"}
```

If the current row version differs → `412 Precondition Failed`:

```json
{"status":"error","message":"Version conflict: expected 3 got 5"}
```

You may also send an HTTP header:

```http
If-Match: 3
```

Stub behavior today: a plain integer is treated as the expected version; `*` skips the check. Future work: full ETag semantics / 412 Precondition Failed responses.

Successful update returns bumped `version` in the envelope. New rows omit (or set initial) version.

All version conflicts across updated endpoints now return `412 Precondition Failed` (older `409` responses have been retired for consistency).

### Strict Filter Mode (Opt-In)

Default behavior: unknown filter keys on `/wcapi/query/` are ignored (backward compatible).

Enable strict validation (reject any unknown filter key with HTTP 400) via body param or header:

```json
{"table_name":"contacts","status":"active","strict":1}
```

Header equivalent:

```http
X-WCAPI-Strict: 1
```

Error example:

```json
{"status":"error","message":"Invalid filter field(s): bad_key"}
```

### Filtering Infrastructure (django-filter)

The project includes `django-filter` (added to `INSTALLED_APPS` and DRF `DEFAULT_FILTER_BACKENDS`) to enable declarative filtering on traditional DRF viewsets / endpoints. The lightweight `/wcapi/query/` endpoint intentionally implements its own explicit allow‑list (`SAFE_FILTER_FIELDS`) instead of relying on automatic generation to:

- Prevent accidental exposure of internal / heavy columns
- Keep the payload contract stable and predictable
- Allow an opt‑in strict mode separate from global DRF filter behavior

If you create new DRF viewsets, you can define `filterset_fields` or custom `FilterSet` classes and they will be powered by `django-filter`. For the universal wcapi endpoint, extend `SAFE_FILTER_FIELDS` (and underlying model fields) rather than adding broad automatic filter backends.

Version: pinned in `requirements.txt` (`django-filter==25.1`).

Troubleshooting:

- If you see `ModuleNotFoundError: No module named 'django_filters'`, ensure your virtualenv has been updated: `pip install -r requirements.txt`.
- Clear any stale venv if mismatched (`rm -rf bin lib include` then recreate) when upgrading major Django versions.


### Metrics Backend Options

Fallback in-memory counters are used by default. To enable Prometheus metrics:

1. Install `prometheus_client`.
2. Set `WCAPI_PROMETHEUS=1` (env var) or legacy `WCAPI_METRICS_BACKEND=prom`.

Then `/wcapi/metrics/` returns the standard Prometheus exposition via `prometheus_client`.

### Projection Field Cache

Projection field validation now caches model field name sets per process to reduce metadata lookups.

### Metrics Endpoint

Lightweight in‑memory counters (temporary / dev) exposed at:

```text
GET /wcapi/metrics/
```

Prometheus text format (sample):

```text
# HELP wcapi_requests_total Total WCAPI requests
# TYPE wcapi_requests_total counter
wcapi_requests_total{method=GET} 42
# HELP wcapi_request_duration_seconds Request duration seconds
# TYPE wcapi_request_duration_seconds summary
wcapi_request_duration_seconds{method=GET}_sum 0.123400
wcapi_request_duration_seconds{method=GET}_count 42
```

Swap to `prometheus_client` later for process-safe metrics & histograms.

### Model Registry & Security Hardening

Dynamic model resolution has been replaced with an explicit allow‑list in `apps/core/services/wcapi_registry.py`:

```python
MODEL_MAP = {
  'contacts': Contact,
  'actions': Action,
  'emails': Email,
  # ...
}
```

Only keys in `MODEL_MAP` (exported as `ALLOWED_TABLE_NAMES`) can be queried. The universal query view (`WcapiView`) rejects unknown tables with HTTP 400.

Filtering is intentionally constrained to a small safe subset (`SAFE_FILTER_FIELDS`) to avoid heavy uncontrolled queries or probing internal structure. Current allow‑list:

```text
email, name_first, name_last, company, action, status
```

Requests providing other keys are ignored for filtering (not errors). Result sets are capped (`MAX_RESULTS = 50`).

### Error Path Guarantees

| Scenario | Status | HTTP | Message |
|----------|--------|------|---------|
| Missing `table_name` (GET/POST) | error | 400 | Missing table_name / Missing required field: table_name |
| Unknown table | error | 400 | Unknown table |
| Invalid JSON body | error | 400 | Invalid JSON ... |
| Record id not found (GET with id) | error | 404 | Not found |
| Unsupported verb (e.g. DELETE /wcapi/query/) | error | 405 | VERB not supported |

Automated tests covering these behaviors: `tests/test_wcapi_errors.py`.

### Extending the Universal API

1. Add model to `MODEL_MAP` in `wcapi_registry.py` (prefer plural key).
2. (Optional) Add new filterable field to `SAFE_FILTER_FIELDS` if low cardinality and indexed.
3. Add/adjust tests to lock behavior (copy patterns from `test_wcapi_errors.py`).
4. Update docs here if response structure evolves.

Future enhancements being considered:

- Role-based dynamic field whitelisting (replace raw `values()` usage)
- Pagination token instead of fixed `MAX_RESULTS` limit
- Per-user/table throttling tiers
- Async export job for large result sets


### Navigation Structure

🏠 **Home** – Landing page with system overview  
**About** – System documentation and features  
**Contacts** – `/wcapi/manage/?table_name=contacts`  
**Actions** – `/wcapi/manage/?table_name=actions`  
**Communications** – `/wcapi/manage/?table_name=emails`  
🥳 **New Contact** – Quick create contact  
**Admin** – Django admin (superusers only)  
🤚 **Logout** – Session termination

## Model Visualization

```bash
pip install pydot
brew install graphviz   # macOS for image output
python manage.py graph_models --pydot -a -g -o webclerk3_visualized.png
```

Graphviz docs: <https://graphviz.org/doc/build.html>

## Celery Monitoring

Flower is a web-based tool for monitoring and administrating Celery clusters.

**To install and run Flower:**

```bash
pip install flower
celery -A webclerk3_api flower
```

Visit <http://localhost:5555> in your browser to view the dashboard.

If you see warnings like `Inspect method ... failed`, it usually means there are no active tasks.

## Keyword Refresh System (Universal API Search Index)

We defer expensive keyword extraction for BaseModel derivatives to keep write latency low.

Flow:

1. On each save, `metadata.flags.keywords_pending` is set True.
2. A periodic Celery task `common.tasks.refresh_keywords_task` (every 10 minutes) processes pending rows, updates `refs.keywords`, clears the flag.
3. Manual runs:

```bash
python manage.py refresh_keywords --dry-run
python manage.py refresh_keywords --limit 500
python manage.py audit_base_models --limit 5
```

Force immediate refresh of all pending rows:

```bash
python manage.py refresh_keywords --limit 0
```

Relevant code: `common/models.py`, commands in `common/management/commands/`, task `common/tasks.py`, scheduling in `common/__init__.py`.

Planned enhancements:

- Dirty-field tracking for change log
- Optional materialized keyword table for analytics

## API Rate Limiting

All API endpoints are rate limited using Django REST Framework:

- Authenticated users: 1000 requests/day
- Unauthenticated users: 100 requests/day

## Logging

API requests and errors are logged to `webclerk3.log`.

## Transaction Line & Aggregation Endpoints

All transaction parent and line resources share a consistent CRUD pattern under `tx/`:

Parents (headers):

```text
GET/POST   /tx/proposals/
GET/PUT    /tx/proposals/{id}/
GET/POST   /tx/orders/
GET/PUT    /tx/orders/{id}/
... (invoices, purchases, workorders, requisitions)
```

Lines:

```text
GET/POST   /tx/proposal-lines/?parent_ref_id={id}
GET/PUT    /tx/proposal-lines/{id}/
... (order-lines, invoice-lines, purchase-lines, workorder-lines, requisition-lines)
```

Filtering / Searching / Ordering (lines):

- Filter: `?parent_ref_id=123&status=open`
- Search: `?search=widget`
- Order: `?ordering=parent_ref_id` (prefix with `-` for descending)

Aggregation:

```text
GET /tx/lines/aggregate/?parent_ref_id={id}[&model=proposal-line][&ttl=120][&include_breakdown=1]
```

Parameters:

- parent_ref_id (required): Parent transaction id.
- model (optional): Scope to single line model code (proposal-line, order-line, invoice-line, purchase-line, workorder-line, requisition-line).
- ttl (optional int >=5): Override cache TTL seconds (default 60 or project setting).
- include_breakdown (optional 0/1/true/false): When scoping to a single model include per-model breakdown (normally only returned when unscoped).

Unscoped example (no model param) response:

```json
{
  "parent_ref_id": 42,
  "total_lines": 7,
  "total_price_extended": "123.45",
  "total_cost_extended": "97.10",
  "breakdown": {
    "proposal-line": {"lines": 3, "price_extended": "80.00", "cost_extended": "60.00"},
    "order-line": {"lines": 4, "price_extended": "43.45", "cost_extended": "37.10"}
  },
  "ttl_seconds": 60,
  "cache_window": 29123456
}
```

Scoped example with breakdown forced:

```json
{
  "parent_ref_id": 42,
  "model": "proposal-line",
  "total_lines": 3,
  "total_price_extended": "80.00",
  "total_cost_extended": "60.00",
  "breakdown": {
    "proposal-line": {"lines": 3, "price_extended": "80.00", "cost_extended": "60.00"}
  },
  "ttl_seconds": 30,
  "cache_window": 29123457
}
```

Notes:

- Decimal totals are stringified for precision.
- `ttl_seconds` reflects actual TTL used (min 5). `cache_window` aids debugging (floor(now / ttl)).
- Cache invalidates automatically on any line create/update/delete.
- Set a project-wide default TTL via Django settings (if provided) or rely on built-in default (60s).
- Configure default aggregation TTL globally by adding `TX_AGGREGATE_TTL_SECONDS = 120` (example) to `settings.py`.

Authentication:

- JWT or session auth required (HTTP 401/403 if missing).

Throttle Scopes:

- Parents: `tx_parent`
- Lines: `tx_line`
- Aggregate: `tx_aggregate`

OpenAPI generation (drf-spectacular) will include summaries for these endpoints.

### Field-Level Authorization (view_edit)

Field visibility & editability are driven by rows in `settings` with `purpose="view_edit"` and `table_name` matching the model DB table (e.g. `transactions_proposalline`). The JSON structure:

```json
{
  "USER": {"view": ["id", "status"], "edit": ["status"]},
  "ADMIN": {"view": ["id", "status", "probability"], "edit": ["status", "probability"]},
  "PUBLIC": {"view": ["id"], "edit": []}
}
```

API layer effects:

- Responses filter out fields not in the role's `view` list.
- Writes (POST/PATCH/PUT) are rejected if attempting to change fields not in `edit` list.
- Authorization matrix endpoint: `GET /tx/auth/fields/?model=proposal-line` returns `{ role, rules:{view,edit} }` for the authenticated user.

Add new permissions simply by editing the JSON in the Setting record; caching auto-invalidation occurs on modification timestamp change.

Frontend consumption (React example):

1. Fetch rules on component mount:

```js
const res = await fetch('/tx/auth/fields/?model=proposal-line', { headers: { Authorization: `Bearer ${token}` }});
const { rules } = await res.json();
```

1. Helpers:

```js
const canView = f => rules.view.includes(f);
const canEdit = f => rules.edit.includes(f);
```

1. Conditional render:

```jsx
{canView('status') && <span>{line.status}</span>}
{canEdit('status') && <input value={status} onChange={e=>setStatus(e.target.value)} />}
```

1. Submit only editable fields; backend returns 400 with per-field errors if unauthorized fields included.

Authorization matrix (single model):

```text
GET /tx/auth/fields/?model=proposal-line
```

Batch authorization matrix:

Two options (choose based on URL length / convenience):

1. GET (comma separated model list)

```text
GET /tx/auth/fields/batch/?models=proposal-line,order-line,invoice-line
```

1. POST (JSON body – preferred for many models)

```http
POST /tx/auth/fields/batch/
Content-Type: application/json

{"models": ["proposal-line", "order-line", "invoice-line"]}
```

Response shape:

```json
{
  "role": "USER",
  "models": {
    "proposal-line": {"view": ["id", "status"], "edit": ["status"]},
    "order-line": {"view": ["id"], "edit": []},
    "bad-line": {"error": "invalid-model"}
  }
}
```

CLI inspection of active matrices:

```bash
python manage.py list_view_edit_matrices --pretty
python manage.py list_view_edit_matrices --table proposal_line --role user --pretty
```

Example output:

```json
{
  "proposal_line": {
    "id": 42,
  "dt_modified": "2025-08-29T06:50:00.123456Z",
    "data": {
      "USER": {"view": ["id", "status"], "edit": ["status"]}
    }
  }
}
```

## Running Tests

```bash
python manage.py test
```

## Deployment (Placeholder)

Add instructions for gunicorn, nginx, HTTPS (Let's Encrypt), environment hardening.

## Environment Variables

Create a `.env` file in the project root with:

```env
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASS=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
SENTRY_DSN=
```

## API Documentation Access (Placeholder)

Document how to access OpenAPI/Swagger (e.g., `/api/schema/`, `/api/docs/`).

## Internationalization (i18n)

We will use multiple languages ONLY for warning messages where clarity and speed are both required. React will manage all other language issues.

To add a new language:

1. Add the language code to `LANGUAGES` in `settings.py`.
2. Mark all user-facing strings with `{% trans %}` or `gettext_lazy`.
3. Run `python manage.py makemessages -l <lang>`.
4. Edit the `.po` files in `locale/<lang>/LC_MESSAGES/`.
5. Run `python manage.py compilemessages`.

```bash
python manage.py test
```

## Production Deployment (Placeholder)









## Optimistic Concurrency & Atomic JSON PATCH (Universal API)

We provide a consistent, versioned PATCH mechanism for all `BaseModel` descendants using:

- Optimistic concurrency (integer `version` field)
- Atomic JSON path mutation (`jsonb_set` / list append) without rewriting entire JSON blobs

### Why

Avoid lost updates and reduce write amplification when only a small nested JSON value changes (e.g., toggling a flag, adding a note) while multiple clients may edit the same record.

### Core Pieces

| Component | Location | Purpose |
|-----------|----------|---------|
| `version` | `BaseModel.version` | Incremented on each successful save / atomic op |
| Atomic helpers | `BaseModel.atomic_json_set`, `BaseModel.atomic_list_append` | SQL-level jsonb mutation & row locking |
| Mixin | `common/mixins.py::OptimisticPatchMixin` | Reusable PATCH handler (set/append + version check) |
| Exception | `common.models.VersionConflictError` | Signals version mismatch (HTTP 412) |

### PATCH Payload Contract (Atomic)

```jsonc
{
  "version": 7,                // required current version
  "set": {                     // optional map of dot paths -> value
    "metadata.flags.schema_rev": 3,
    "prefs.ui.theme": "dark"
  },
  "append": {                  // optional map of list paths -> element
    "comments.notes": {"text": "hello", "type": "info"}
  }
}
```

Rules:

- At least one of `set` or `append` must be present for atomic mode.
- Dot paths: first segment must be one of `metadata`, `refs`, `prefs`, `comments`.
- Each successful operation bumps `version` by 1 (append returns the new version).
- Stale `version` ⇒ 412 response: `{ "detail": "Version conflict: expected X got Y", "code": "version_conflict" }`.

### Fallback (Non-atomic) Partial Update

If the PATCH body lacks `set`/`append`, the request falls back to normal DRF partial update. If a `version` key is provided it is still checked before updating, returning 412 on mismatch.

### Example Flow

1. Client GET `/comm/domains/42/` → `{ ..., "version": 7 }`.
1. Client wants to bump schema rev:

```http
PATCH /comm/domains/42/
Content-Type: application/json

{"version":7, "set":{"metadata.flags.schema_rev":5}}
```

1. Server applies atomic jsonb_set → returns `version:8`.
1. Client appends a note:

```http
PATCH /comm/domains/42/
{"version":8, "append":{"comments.notes":{"text":"investigated","type":"log"}}}
```

1. Server returns `version:9`.
1. A stale client still holding `version:7` sends a patch → receives 412 conflict and must re-fetch.

### Error Responses

| Status | When | Shape |
|--------|------|-------|
| 400 | Missing version / invalid root path / no ops | `{ "version": ["This field is required for atomic patch."] }` or path-specific message |
| 412 | Version mismatch | `{ "detail": "Version conflict: expected 7 got 9", "code": "version_conflict" }` |

### Extending To Another Model

1. Ensure model inherits `BaseModel` (already has `version`).
1. Use `OptimisticPatchMixin` in the detail view:

```python
class WidgetDetailView(OptimisticPatchMixin, generics.RetrieveUpdateDestroyAPIView):
  queryset = Widget.objects.all()
  serializer_class = WidgetSerializer
  def patch(self, request, *args, **kwargs):
    obj = self.get_object()
    data = request.data
    if any(k in data for k in ("set","append")):
      try:
        updated = self.apply_atomic_ops(obj, data)
      except VersionConflictError as e:
  return Response({"detail": str(e), "code": "version_conflict"}, status=412)
      return Response(self.get_serializer(updated).data)
    if 'version' in data and data['version'] != obj.version:
  return Response({"detail": f"Version conflict: expected {data['version']} got {obj.version}", "code": "version_conflict"}, status=412)
    return super().patch(request, *args, **kwargs)
```

1. Add tests mirroring `test_domain_atomic_patch_and_version_conflict`.

### Design Rationale

- Uses PostgreSQL row-level locks + jsonb functions → safe under concurrency.
- Keeps payloads small and avoids overwriting sibling keys.
- Allows gradual introduction of more operations (future: `remove`, `increment`, `merge`).

### Future Enhancements

- Header-based version (support `If-Match` / `ETag`).
- Batch multi-row atomic operations.
- Conflict auto-merge strategies (server-side field diffing).
- Audit log entries per atomic operation.

## Modular BaseModel & CoreModel (Capability Composition)

We decomposed the former monolithic `BaseModel` into a small `CoreModel` plus optional mixins. Compose only what each table needs while keeping a universal contract (id, uuid, ida, dt_created, dt_modified, version).

### Mixins & Capabilities

| Mixin / Core | Adds Fields | Key Helpers | feature_flags | Typical Use |
|--------------|-------------|-------------|---------------|-------------|
| CoreModel | id, uuid, ida, dt_created, dt_modified, version | optimistic_save/assert_version | core | Minimal high‑churn tables, queues |
| MetadataMixin | metadata | history access, set/get metadata value | metadata | Lifecycle, audit, versioned schemas |
| RefsMixin | refs | add_keyword/add_tag | refs | Keyword/tag search, soft links |
| PrefsMixin | prefs | (none yet) | prefs | Per-record user configuration |
| CommentsMixin | comments | add_note | comments | Collaboration, notes, discussions |
| HealthMixin | health_rating | (none yet) | health | Data quality scoring |
| KeywordsMixin | (relies on refs+metadata) | mark_keywords_dirty, update_keywords | keywords | Async keyword extraction pipeline |
| LifecycleMixin | is_deleted, is_archived | soft_delete/restore/archive | lifecycle | Soft delete & archival controls |
| AtomicJSONMixin | (no fields) | atomic_json_set / atomic_list_append | atomic_json | JSONB atomic patch operations |
| UniversalDictMixin | (no fields) | to_universal_dict / as_pydantic | universal_dict | Uniform API serialization |

`BaseModel` = full composition of all the above (in MRO order):


```python
class BaseModel(MetadataMixin, RefsMixin, PrefsMixin, CommentsMixin,
        HealthMixin, KeywordsMixin, LifecycleMixin,
        CoreModel, UniversalDictMixin, AtomicJSONMixin):
  pass
```


`CoreModel` (a.k.a previously slim) = minimal identity + version only.

### Choosing a Composition

Decision checklist (add mixins until all requirements satisfied):

| Requirement | Add This |
|-------------|----------|
| Need only identity + optimistic concurrency | CoreModel |
| Track lifecycle history + timestamps in metadata | MetadataMixin |
| Store tags / keywords / lightweight links | RefsMixin (+ KeywordsMixin for auto keyword pipeline) |
| Allow user-level display or behavior settings | PrefsMixin |
| Attach threaded notes / comments | CommentsMixin |
| Score or surface health/quality metrics | HealthMixin |
| Soft delete / archive states | LifecycleMixin |
| Atomic JSON path set / list append | AtomicJSONMixin (requires relevant JSON field) |
| Uniform serialization (generic endpoints) | UniversalDictMixin |

If you need keywords auto-generation you typically include: MetadataMixin + RefsMixin + KeywordsMixin.

### Example Compositions

1. Full domain entity (most models): BaseModel
2. Queue / staging (Pending): CoreModel only
3. Audited but no comments/prefs: class AuditOnly(MetadataMixin, RefsMixin, CoreModel, UniversalDictMixin, AtomicJSONMixin)

### Pending (Queue) Example

`apps/core/models/pending.py` inherits `CoreModel` only. It keeps writes fast and payloads small while still benefiting from version for optimistic concurrency.

### Migrating an Existing Full Model to a Leaner Composition

1. Create new class inheriting the reduced set of mixins + CoreModel.
2. Remove unused JSON fields from the model class.
3. makemigrations / migrate.
4. Update serializers to reflect removed fields.
5. Remove atomic PATCH operations if AtomicJSONMixin is no longer included.
6. Adjust docs / client expectations.
7. Run test suite.

### Capability Introspection

Use `model_capabilities(MyModel)` to enumerate enabled feature flags. Generic views can branch on capabilities (e.g., deny atomic JSON ops if `atomic_json` absent).

### Design Principles

- Keep `BaseModel` as the default for rich entities.
- Start with `CoreModel` for any ephemeral/high‑churn table; add only what’s justified.
- One mixin = one responsibility; no hidden cross‑dependencies beyond documented expectations (e.g., KeywordsMixin assumes Refs + optionally Metadata).
- Avoid premature inclusion of atomic JSON mixin—only when partial updates are required.

### Why Not Just Two Bases?

Granular mixins prevent midpoint compromises (e.g., wanting metadata + refs but not comments). This keeps schema surface proportional to real functional need and reduces JSON serialization overhead and index bloat.

### Pydantic Integration

`UniversalDictMixin` supplies `to_universal_dict()` and Pydantic conversion via an optional cached `UniversalAPISchema`. All compositions sharing this mixin automatically serialize consistently.

### Future Extensions

- Add MetricsMixin (aggregated counters) when needed.
- Add EncryptionMixin for sensitive JSON subtrees.
- Provide a factory to auto‑generate Pydantic models from any composition for stricter contracts.

---

## Consistency Standards (All Apps / Models)

Every model inheriting `BaseModel` should expose a uniform API surface:

1. Serializer: subclass `RoleAwareModelSerializer` (in `common/base_serializers.py`) and set `table_name` if DB table differs.
2. List/Create: subclass `BaseListCreateView` (in `common/base_views.py`) and set `queryset`, `serializer_class`, optional `ALLOWED_ROLES`, and `pagination_class`.
3. Detail (Retrieve/Update/Destroy): subclass `BaseOptimisticDetailView` for versioned PATCH + atomic ops.
4. Search: subclass `PrefixAndSearchView` (in `common/search_mixins.py`) setting `model`, `serializer_class`, `search_fields`, optional `role_set`.
5. URLs: expose three patterns per resource under its app namespace:
   - `resource/` (list & create)
   - `resource/<id>/` (detail + PATCH)
   - `resource/search/` (multi-term prefix search)
6. Field visibility & edit rules: driven by settings `view_edit` matrix; serializers automatically enforce.
7. Pagination: page size default 25 with `?page_size=` override up to 500.
8. Ordering: list views support `?ordering=` parameter (defaults to `-dt_modified`).
9. Versioning: clients must supply `version` in atomic PATCH payload; conflict => 412.
10. Minimal fallback exposure for non-privileged roles when no matrix configured.

Template Example (New Resource)

```python
# serializers/myresource.py
from common.base_serializers import RoleAwareModelSerializer
from .models import MyResource

class MyResourceSerializer(RoleAwareModelSerializer):
  table_name = 'my_resource'
  class Meta:
    model = MyResource
  fields = ['id','uuid','name','status','refs','prefs','metadata','dt_created','dt_modified','version']
  read_only_fields = ['id','uuid','dt_created','dt_modified','version']

# views/myresource.py
from common.base_views import BaseListCreateView, BaseOptimisticDetailView
from common.search_mixins import PrefixAndSearchView
from .models import MyResource
from .serializers.myresource import MyResourceSerializer

class MyResourceListView(BaseListCreateView):
  queryset = MyResource.objects.all()
  serializer_class = MyResourceSerializer
  ALLOWED_ROLES = {'staff','admin'}

class MyResourceDetailView(BaseOptimisticDetailView):
  queryset = MyResource.objects.all()
  serializer_class = MyResourceSerializer
  ALLOWED_ROLES = {'staff','admin'}

class MyResourceSearchView(PrefixAndSearchView):
  model = MyResource
  serializer_class = MyResourceSerializer
  search_fields = ['name','status']
  role_set = {'staff','admin'}
```

Benefits

- Single evolution point for auth, field filtering, concurrency.
- Predictable client behavior across all resources.
- Easier onboarding and automated documentation generation.

Deviation Policy

- Only deviate for performance-critical endpoints (bulk ingest, streaming) and document rationale adjacent to code.











