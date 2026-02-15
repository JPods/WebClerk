# Django Improvements — wc3 & r25


<!-- TOC START -->

## Table of Contents

- [Django Improvements — wc3 \& r25](#django-improvements--wc3--r25)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [P0 — Security (do first)](#p0--security-do-first)
    - [1. Add DEFAULT\_PERMISSION\_CLASSES](#1-add-default_permission_classes)
    - [2. Reduce JWT Access-Token Lifetime](#2-reduce-jwt-access-token-lifetime)
    - [3. Audit AllowAny on Write Endpoints](#3-audit-allowany-on-write-endpoints)
  - [P1 — Data Safety \& Correctness](#p1--data-safety--correctness)
    - [4. Replace fields = "\_\_all\_\_" in Serializers — ✅ Implemented](#4-replace-fields--__all__-in-serializers--implemented)
    - [5. Consistent Soft-Delete Filtering — ✅ Implemented](#5-consistent-soft-delete-filtering--implemented)
    - [6. Create or Remove ViewEditPermission — ✅ Implemented](#6-create-or-remove-vieweditpermission--implemented)
  - [P2 — WCAPI as the Single Write Gate](#p2--wcapi-as-the-single-write-gate)
    - [7. Consolidate /api/ and /wcapi/ Write Paths — ✅ Implemented](#7-consolidate-api-and-wcapi-write-paths--implemented)
    - [8. WCAPI Write Guard — How It Works Today](#8-wcapi-write-guard--how-it-works-today)
    - [9. Add Rate Limiting — ✅ Implemented](#9-add-rate-limiting--implemented)
  - [P2 — Architecture](#p2--architecture)
    - [10. Refactor Transaction Signals — ✅ Implemented](#10-refactor-transaction-signals--implemented)
    - [11. Bootstrap Celery (or Remove .delay Calls) — ✅ Implemented](#11-bootstrap-celery-or-remove-delay-calls--implemented)
    - [12. Split common/middleware.py — ✅ Implemented](#12-split-commonmiddlewarepy--implemented)
  - [P3 — Hygiene \& Developer Experience](#p3--hygiene--developer-experience)
    - [13. Register Missing Admin Models — ✅ Implemented](#13-register-missing-admin-models--implemented)
    - [14. Testing Infrastructure — ✅ Implemented](#14-testing-infrastructure--implemented)
    - [15. Remove Debug print() Statements — ✅ Implemented](#15-remove-debug-print-statements--implemented)
    - [16. FK Naming Convention Rollout — ✅ Implemented](#16-fk-naming-convention-rollout--implemented)
  - [R25 Frontend Alignment](#r25-frontend-alignment)
    - [17. Type Generation from Django Models](#17-type-generation-from-django-models)
    - [18. Error Envelope Consistency — ✅ Implemented](#18-error-envelope-consistency--implemented)
    - [19. Token Storage Security — ✅ Implemented](#19-token-storage-security--implemented)
  - [Role-Based Write Policy](#role-based-write-policy)
    - [20. WCAPI Write-Field Enforcement — ✅ Implemented](#20-wcapi-write-field-enforcement--implemented)
  - [Implementation Order](#implementation-order)
  - [Related Documentation](#related-documentation)

<!-- TOC END -->

Date: 2026-02-15
Review: Team discussion pending
Status: Draft
Owner: Bill

## Overview

This document catalogues recommended improvements to the Django backend
(webClerk3 / wc3) and how they affect the React frontend (React2025 /
r25). The guiding principle: **all data access and mutations flow through
WCAPI** — the universal API layer that enforces authentication,
authorization, rate limiting, and envelope formatting in one place.

Items are grouped by priority:

| Priority | Scope | Count |
|---|---|---|
| ~~**P0**~~ | ~~Security — prevent unauthorized access~~ ✅ | 3 |
| ~~**P1**~~ | ~~Data safety — prevent accidental data exposure~~ ✅ | 3 |
| ~~**P2**~~ | ~~Architecture — consolidate and harden~~ ✅ | 6 |
| ~~**P3**~~ | ~~Hygiene — clean up tech debt~~ ✅ | 4 |
| ~~**R25**~~ | ~~Frontend alignment~~ ✅ | 3 |
| ~~**P4**~~ | ~~Write-field enforcement~~ ✅ | 1 |

---

## P0 — Security (do first)

### 1. Add DEFAULT\_PERMISSION\_CLASSES — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** `REST_FRAMEWORK` in `webclerk3_api/settings.py` had no
`DEFAULT_PERMISSION_CLASSES`. Any DRF view that omitted `permission_classes`
silently defaulted to `AllowAny`, exposing data to unauthenticated callers.

**What was done:** Added `DEFAULT_PERMISSION_CLASSES` to `REST_FRAMEWORK`
in `webclerk3_api/settings.py`:

```python
REST_FRAMEWORK = {
    ...
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

The default is now "locked unless opened." Views that genuinely need
public access override with `permission_classes = [AllowAny]` explicitly.

**R25 impact:** None — the frontend already sends JWT on every request via
Axios interceptors.

---

### 2. Reduce JWT Access-Token Lifetime — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** `ACCESS_TOKEN_LIFETIME = timedelta(days=7)` was far too long.
A leaked token granted 7 days of full access.

**What was done:** Updated `SIMPLE_JWT` in `webclerk3_api/settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),   # was 7 days
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),       # was 30 days
    'ROTATE_REFRESH_TOKENS': True,                     # added
    'BLACKLIST_AFTER_ROTATION': True,                  # added
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**R25 impact:** None — the frontend already handles 401 → refresh → replay
via the Axios interceptor in `src/api/axios.ts`. Shorter access tokens
trigger more refreshes, but the existing queue-and-replay logic handles
this transparently.

---

### 3. Audit AllowAny on Write Endpoints — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** Several ViewSets and views used `permission_classes = [AllowAny]`
on endpoints that accept POST/PUT/PATCH, allowing unauthenticated writes.

**What was done:** Replaced `AllowAny` with `IsAuthenticated` on 13 view
classes across 7 files:

| File | Views changed |
|---|---|
| `apps/products/views/inventory.py` | `ReservationListView`, `ReservationDetailView`, `ReservationCommitView`, `ReservationActionView` |
| `apps/products/views/inventory_views.py` | `InventoryReservationActionView`, `InventoryPrometheusMetricsView` |
| `apps/transactions/views/purchase_views.py` | `ReceivePurchaseView` |
| `apps/transactions/views/linkage_views.py` | `LinkageCommentsView` |
| `apps/transactions/views/order_views.py` | `OrderToInvoiceView`, `OrderToPurchaseView` |
| `apps/transactions/views/project_views.py` | `ProjectListView` |
| `apps/sync/views/connection.py` | `ConnectionListView` |

**Kept `AllowAny`** (legitimately public):

| File | Views | Reason |
|---|---|---|
| `apps/core/views/auth_views.py` | Login, signup, token refresh, password reset | Must be accessible pre-auth |
| `apps/core/views/system_info.py` | `SystemInfoView` | Public read-only system info |
| `apps/core/views/choices.py` | `ChoiceCatalogView` | Public read-only choice lists |
| `apps/sync/views/google_calendar.py` | OAuth callback | Google hits this without cookies |

With `DEFAULT_PERMISSION_CLASSES` now set to `IsAuthenticated` (item #1),
any new view that omits `permission_classes` is automatically locked down.

---

## P1 — Data Safety & Correctness

### 4. Replace fields = "\_\_all\_\_" in Serializers — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** 19 serializers used `fields = "__all__"`, exposing every model
field including `is_deleted`, `version`, `dt_modified`, `refs`, and other
internal columns.

**Role-based field exposure:** Implemented 2026-02-15 — `enforce_write_policy()`
in `model_policies.py` is now wired into both `SaveWcapiView` code paths
(`_perform_save()` and `post()`). Policies configured in `WCAPI_MODEL_POLICIES`
for contact, orgbase, item, all transaction headers/lines, and payment.
See [Role-Based Write Policy](#role-based-write-policy) section below.

**What was done:** Replaced `fields = "__all__"` with explicit field lists
and added `read_only_fields` covering all BaseModel system columns across
18 serializers in 4 files:

| File | Serializers changed | Notes |
|---|---|---|
| `apps/products/serializers.py` | 11 of 13 | `SpecificationSerializer` and `FlowSerializer` removed (models don't exist). `UsageSerializer` fixed to reference `ItemUsage` model. |
| `apps/transactions/serializers/transaction_serializers.py` | 3 | `ProposalLineSerializer`, `OrderLineSerializer`, `PurchaseLineSerializer` |
| `apps/transactions/serializers/requisition.py` | 1 | `RequisitionSerializer` — also fixed `read_only_fields` indentation bug (was at class level, not inside `Meta`) |
| `apps/core/views/action_views.py` | 1 | `ActionSerializer` |

All serializers now declare a shared `_BASE_RO` constant for the 13
BaseModel system fields:

```python
_BASE_RO = [
    "id", "uuid", "dt_created", "dt_modified", "version",
    "is_deleted", "is_archived", "metadata", "refs", "prefs",
    "actions", "comments", "health_rating",
]
```

**Kept `fields = "__all__"`:** `apps/orgs/admin.py` (`OrgBaseAdminForm`) —
standard practice for Django admin forms which are staff-only.

**Bugs fixed during audit:**
- `_model("Usage")` → `_model("ItemUsage")` — model class name mismatch
- `SpecificationSerializer` removed — `Specification` model doesn't exist
- `FlowSerializer` removed — `Flow` model doesn't exist
- `RequisitionSerializer.read_only_fields` moved inside `Meta` class

---

### 5. Consistent Soft-Delete Filtering — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** The default manager (`objects = FullManager()`) returned all
records including soft-deleted. Views using `Model.objects.all()`
inadvertently included deleted records.

**What was done:** Applied Option A — replaced `.objects.all()` with
`.objects.active()` across all view files. The `FullManager.active()`
method filters `is_active=True, is_deleted=False, is_archived=False`.

**Files changed (16 view files, ~57 queryset lines):**

| File | Views affected |
|---|---|
| `apps/transactions/views/line_views.py` | 27 querysets across all transaction list/detail views |
| `apps/transactions/views/transaction_views.py` | `ProposalViewSet`, `OrderViewSet`, `PurchaseViewSet`, `InvoiceViewSet`, `PaymentViewSet` |
| `apps/transactions/views/actions.py` | `ProposalToOrderView`, `OrderToInvoiceView`, `OrderToPurchaseView`, `ReceivePurchaseView`, `WorkOrderTransitionView`, `WorkOrderLineTransitionView` |
| `apps/transactions/views/unified.py` | `TransactionHeaderListCreate`, `TransactionHeaderDetail`, `TransactionTotalsPreview`, `LinkageCommentsView` |
| `apps/transactions/views/wcapi.py` | `WCAPIGetView`, `WCAPISyncView` |
| `apps/transactions/views/order_views.py` | `OrderViewSet`, `OrderLineViewSet` |
| `apps/transactions/views/invoice_views.py` | `InvoiceViewSet`, `InvoiceLineViewSet` |
| `apps/transactions/views/proposal_views.py` | `ProposalViewSet`, `ProposalLineViewSet` |
| `apps/transactions/views/payment_views.py` | `PaymentViewSet` |
| `apps/transactions/views/requisition.py` | `RequisitionListView`, `RequisitionDetailView` |
| `apps/transactions/views/project_views.py` | `ProjectListView` |
| `apps/orgs/views/customer_viewset.py` | `OrgBaseViewSet` + 5 proxy model ViewSets |
| `apps/sync/views/connection.py` | `ConnectionListView`, `ConnectionDetailView` |
| `apps/core/views/action_views.py` | `ActionViewSet` |
| `apps/core/views/wcapi.py` | Ordering validation |
| `apps/core/views/save_view.py` | `SaveView._handle_save` |
| `apps/products/views/item_variants.py` | `ItemVariantsView` |

**Special case:** Proxy models (`Customer`, `Vendor`, `Rep`, `Employee`,
`Manufacturer`) use `_TypeFilteredManager` which lacks `.active()`. These
use `.objects.filter(is_active=True, is_deleted=False)` instead.

---

### 6. Create or Remove ViewEditPermission — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** `apps/transactions/views/line_views.py` imported
`ViewEditPermission` from `apps.core.permissions`, but no class with that
name existed in the codebase. The import failed at runtime.

**What was done:** Created `ViewEditPermission` in
`apps/core/permissions.py` as a DRF `BasePermission` subclass that:

1. **Requires authentication** — unauthenticated requests are denied
2. **Bypasses for admins/superusers** — full access granted
3. **Resolves the model** from the view's `queryset` attribute
4. **Checks role-based rules** via `get_role_field_rules(model, role)`:
   - Read requests (GET/HEAD/OPTIONS): role must have at least one viewable field
   - Write requests (POST/PUT/PATCH/DELETE): role must have at least one editable field

Used by `BasePermission` in `line_views.py` and transitively by
`unified.py` for all transaction CRUD endpoints.

---

## P2 — WCAPI as the Single Write Gate

### 7. Consolidate /api/ and /wcapi/ Write Paths — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** Two parallel API surfaces exist:

| Prefix | Layer | Write endpoints |
|---|---|---|
| `/wcapi/save/`, `/wcapi/delete/` | Universal views | All models via `model_name` dispatch |
| `/api/orgs/`, `/api/transactions/`, `/api/products/` | DRF ViewSets | POST/PUT/PATCH/DELETE per-model |

Both paths can create/update/delete records. The WCAPI path runs through
`WriteGateMiddleware`, `AutoEnvelopeMiddleware`, and model-level
`api_validate_payload()`. The DRF path bypasses all of these.

**R25 current state:** The React frontend exclusively uses `/wcapi/save/`
for all writes (confirmed in `src/api/wcapi.ts`). The `/api/` ViewSets
are only used for **reads** via `GET` requests and even those are being
migrated to `/wcapi/get/`.

**Fix (phased):**

1. **Immediate:** Add `ReadOnlyModelViewSet` (or remove write mixins) from
   all DRF ViewSets that should be read-only:

```python
# Before — full CRUD open on /api/
class CustomerViewSet(viewsets.ModelViewSet):
    ...

# After — reads only; writes go through /wcapi/save/
class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    ...
```

2. **Medium-term:** Migrate remaining `/api/` reads to `/wcapi/get/` and
   retire the DRF router endpoints entirely.

3. **Long-term:** Remove DRF ViewSets and routers; WCAPI is the sole API
   surface.

**What was done:** Converted 19 DRF `ModelViewSet` classes to
`ReadOnlyModelViewSet` across 7 files, removing all `perform_create`,
`perform_update`, `perform_destroy` methods and stub `@action` methods.
Custom `@action` endpoints that perform writes via WCAPI services were
preserved.

| File | ViewSets converted |
|---|---|
| `apps/orgs/views/customer_viewset.py` | `OrgBaseViewSet`, `CustomerViewSet`, `VendorViewSet`, `RepViewSet`, `EmployeeViewSet`, `ManufacturerViewSet` |
| `apps/transactions/views/transaction_views.py` | `ProposalViewSet`, `OrderViewSet`, `PurchaseViewSet`, `InvoiceViewSet`, `PaymentViewSet` |
| `apps/transactions/views/proposal_views.py` | `ProposalViewSet`, `ProposalLineViewSet` |
| `apps/transactions/views/order_views.py` | `OrderViewSet`, `OrderLineViewSet` |
| `apps/transactions/views/invoice_views.py` | `InvoiceViewSet`, `InvoiceLineViewSet` |
| `apps/transactions/views/payment_views.py` | `PaymentViewSet` |
| `apps/core/views/action_views.py` | `ActionViewSet` |

---

### 8. WCAPI Write Guard — How It Works Today

For reference, the current write protection stack:

```
r25 (React)
  └─ POST /wcapi/save/  { model_name, data, id? }
       │
       ▼
  JSONOnlyMiddleware         → reject non-JSON Content-Type
  WriteGateMiddleware        → block non-whitelisted write paths
  RequestLogMiddleware       → log + request ID
       │
       ▼
  SaveWcapiView
    ├─ JWT authentication    → IsAuthenticated (via DRF auth classes)
    ├─ model_name lookup     → resolve to Django model class
    ├─ api_validate_payload  → pydantic schema validation (orgs)
    ├─ save service          → optimistic locking via version field
    └─ AutoEnvelopeMiddleware → wrap response in { status, code, data }
```

**Known gaps in this stack:**
- `WriteGateMiddleware` is **skipped during tests** (`PYTEST_CURRENT_TEST`
  check) — middleware behavior is never tested.
- ~~No per-model **field-level write protection** — any authenticated user
  can write any field.~~ ✅ Fixed — `enforce_write_policy()` now strips
  disallowed fields before the assignment loop in both save paths.
  Policies configured in `WCAPI_MODEL_POLICIES` (settings.py).
- No **rate limiting** at any layer (see item 9).

---

### 9. Add Rate Limiting — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** No throttling was configured. A compromised token or bot
could hammer the API indefinitely.

**What was done:** Added throttle configuration to `REST_FRAMEWORK` in
`webclerk3_api/settings.py`:

```python
REST_FRAMEWORK = {
    ...
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "120/minute",
        "anon": "30/minute",
    },
}
```

**Future enhancement:** For write-heavy endpoints (transaction saves with
lines), consider a separate throttle scope:

```python
class TransactionSaveThrottle(UserRateThrottle):
    scope = "transaction_save"
    rate = "30/minute"
```

---

## P2 — Architecture

### 10. Refactor Transaction Signals — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** `apps/transactions/signals.py` was 756 lines with 30+
receivers. The same inventory-tracking pattern (pre\_save → capture
original, post\_save → create pending adjustment, post\_delete → release)
was copy-pasted for 5 line types.

**What was done:** Complete rewrite from 756 → 284 lines using three
factory functions driven by a configuration table:

```python
_LINE_CONFIG = [
    (ProposalLine,  'parent',    'proposal',  'proposal',       'proposal_line'),
    (OrderLine,     'order',     'order',     'sales_order',    'order_line'),
    (InvoiceLine,   'invoice',   'invoice',   'invoice',        'invoice_line'),
    (PurchaseLine,  'purchase',  'purchase',  'purchase_order', 'purchase_line'),
    (WorkOrderLine, 'workorder', 'workorder', 'workorder',      'workorder_line'),
]
```

| Factory function | Purpose |
|---|---|
| `register_line_inventory_signals()` | pre_save/post_save/post_delete for inventory tracking |
| `register_line_header_links()` | maintains `refs.links` on parent header |
| `register_line_totals_signals()` | updates parent totals on line save/delete |

Unified `_resolve_item_id()` and `_get_quantity()` replace 6 duplicate
helpers. Header status-change and notification signals kept explicit
(genuinely different logic per model).

---

### 11. Bootstrap Celery (or Remove .delay Calls) — ✅ Implemented

**Status:** Completed 2026-02-15 (Option A — synchronous via `transaction.on_commit()`)

**Problem:** 3 calls to `.delay()` in `common/refs/tasks.py` used
`cast(Any, func).delay(...)` but no Celery infrastructure existed.
These would raise `AttributeError` at runtime.

**What was done:** Replaced all 3 `.delay()` calls with
`transaction.on_commit()` in `common/refs/tasks.py`:

```python
# Before:
cast(Any, prune_refs_for_owner).delay(owner_id, content_type_id)

# After:
transaction.on_commit(
    lambda oid=owner_id, ctid=content_type_id:
        prune_refs_for_owner(oid, ctid)
)
```

Affected functions: `nightly_prune_refs`, `nightly_backfill_assignee_refs`,
`nightly_backfill_action_refs`. Removed `from typing import Any, cast`
imports (no longer needed).

**Verified:** Zero `.delay()` calls remain in `apps/` or `common/`
(one exists in a scheduler docstring example — not runtime code).

**Future:** When Celery is bootstrapped (Option B), these can be
converted to `@shared_task` + `.delay()` with a broker configured.

---

### 12. Split common/middleware.py — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** `common/middleware.py` was 382 lines containing 7 middleware
classes. Two (`WCAPISearchGuardMiddleware`, `EnvelopeMiddleware`) were
dead code — defined but not in `MIDDLEWARE`.

**What was done:** Split into focused modules:

```
common/
  middleware/
    __init__.py            → re-exports for settings.MIDDLEWARE
    helpers.py             → shared helpers, constants, skip logic
    logging.py             → RequestLogMiddleware
    envelope.py            → AutoEnvelopeMiddleware
    exceptions.py          → ExceptionAsJsonMiddleware
    rendering.py           → EnsureRenderedMiddleware
    security.py            → WriteGateMiddleware
```

- Dead code removed: `WCAPISearchGuardMiddleware` and `EnvelopeMiddleware`
  (old stub) are not re-exported.
- `__init__.py` re-exports all 5 active classes + `ENVELOPE_SKIPS`,
  so `settings.MIDDLEWARE` strings (e.g., `'common.middleware.WriteGateMiddleware'`)
  continue to work unchanged.
- Old `common/middleware.py` renamed to `common/middleware_OLD.py` as backup.

---

## P3 — Hygiene & Developer Experience

### 13. Register Missing Admin Models — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** Several models in `WCAPI_BLESSED_MODELS` had no Django
admin registration, making them invisible in the admin UI for debugging.

**What was done:** Added admin registrations for 12 models across 4 admin files:

| App | Models Registered | Admin File |
|---|---|---|
| `accounts` | `Ledger`, `TaxJurisdiction`, `GlJournal` | `apps/accounts/admin.py` |
| `transactions` | `PaymentMethod`, `PaymentTerm`, `PaymentApplication` | `apps/transactions/admin.py` |
| `products` | `InventoryReservation`, `Specification` | `apps/products/admin.py` |
| `docs` | (none — `LinkageIndex` was deleted) | — |

Each registration uses `ScalarFirstFieldsetMixin` with `list_display`,
`search_fields`, and `list_filter`. Verified with `admin.autodiscover()`.

**Known issues found during audit:**
- 4 dead `WCAPI_BLESSED_MODELS` entries: `Flow`, `Campaign`, `LinkageIndex`, `ProjectLinks`
- `TaxJurisdiction.service_id` missing parentheses bug in FK definition
- `audit` blessed path is wrong (`core.Audit` should be `accounts.Audit`)

---

### 14. Testing Infrastructure — ✅ Implemented

**Status:** Completed 2026-02-15

**What was done:**

1. **Installed packages:** `pytest-cov==7.0.0` and `factory-boy==3.3.3`
2. **Created `.coveragerc`** with source paths, omit patterns, and
   `fail_under = 40` threshold
3. **Created `tests/conftest.py`** with 12 factories covering the core
   domain models:
   - `UserFactory`, `OrgBaseFactory`, `CustomerFactory`, `EmployeeFactory`
   - `ItemFactory`, `WarehouseFactory`, `InventoryLayerFactory`
   - `InvoiceFactory`, `PaymentFactory`, `PaymentApplicationFactory`
   - `CatalogFactory`, `OrderFactory`

Each factory uses `factory.Sequence` and `factory.SubFactory` for
realistic data generation. All factories inherit from
`factory.django.DjangoModelFactory`.

---

### 15. Remove Debug print() Statements — ✅ Implemented

**Status:** Completed 2026-02-15

**What was done:** Replaced 31 production `print()` calls across 8 files
with proper `logging` calls:

| File | Prints Removed | Replacement |
|---|---|---|
| `apps/orgs/admin.py` | 8 | `logger.debug()` |
| `apps/orgs/models/base.py` | 1 | `logger.warning()` |
| `apps/products/models/inventory_layer.py` | 6 | `logger.debug()` / `logger.warning()` |
| `apps/transactions/models/payment.py` | 3 | `logger.debug()` |
| `common/middleware/write_gate.py` | 5 | `logger.debug()` / `logger.warning()` |
| `apps/core/views/action_views.py` | 3 | `logger.debug()` |
| `apps/sync/services/*.py` | 3 | `logger.debug()` |
| `apps/transactions/views/*.py` | 2 | `logger.debug()` |

Only 2 `print()` in docstrings remain (intentional documentation).

---

### 16. FK Naming Convention Rollout — ✅ Implemented

**Status:** Completed 2026-02-15

See [FK Naming Conventions](../models/fk-naming-conventions.md) for the
full inventory.

**What was done:** Renamed all 48 Pattern B FK fields across 20 model
files (26 models). Each field was renamed to drop the `_id` suffix and
given an explicit `db_column` pointing to the clean column name.

**Strategy:** "Clean rename" — both Python field names AND DB column
names are changed (from `_id_id` to `_id`). Migrations use
`AlterField` + `RenameField` to safely rename columns.

**Model files modified:** 20 files across 7 apps:
- `orgs` (1 field), `core` (4 fields), `docs` (1 field), `sync` (1 field)
- `accounts` (3 fields), `transactions` (8 fields), `products` (30 fields)

**Reference sweep:** Updated 30+ files including:
- 4 admin files (raw_id_fields, list_filter, search_fields)
- 7 serializer files (source=, fields lists)
- 8+ service files (filter kwargs, create kwargs, select_related)
- 2 view files (filterset_fields, access control)
- 3 management commands
- 5 test files (13 fixtures + assertions)

**Migration files generated:** 6 migrations across accounts, core, docs,
products, sync, transactions — all using `RenameField` (not destructive
`RemoveField` + `AddField`).

**Bugs fixed during sweep:**
- `Ledger.gl_account` FK referenced non-existent `'accounts.Gl_account'`
  instead of `'accounts.GlAccount'` — pre-existing bug
- `payment_views.py` access control: `payment.contact_id != request.user`
  compared int (attname) to User object — always `True`, bypassing the
  security check. Fixed to `payment.contact != request.user`

**System check:** `python manage.py check` passes with 0 issues.
`python manage.py makemigrations --check` confirms no pending changes.

---

## R25 Frontend Alignment

### 17. Type Generation from Django Models — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** 68 hand-written TypeScript type files in r25
(`src/apps/*/models/*/types/*.ts`) are manually maintained copies of
Django model fields. They drift as fields are added, renamed, or removed
on the backend.

**Solution implemented:** Custom Django management command that reads
model `_meta` from all `WCAPI_BLESSED_MODELS` and generates TypeScript
interfaces directly.

**What was built:**

| Artifact | Location |
|---|---|
| Management command | `apps/core/management/commands/generate_ts_types.py` |
| Generated output | `React2025/src/generated/modelTypes.ts` |
| npm script | `npm run generate:types` (in r25 `package.json`) |

**Output stats:** 64 models → 192 interfaces → 4,707 lines across 8 apps
(accounts, communications, core, docs, orgs, products, sync, transactions).

**Three interfaces per model:**

| Interface | Purpose |
|---|---|
| `{Model}Record` | Full record shape — all fields including read-only |
| `Create{Model}Request` | Writable fields only (system fields excluded) |
| `Update{Model}Request` | Writable fields + `id` required, all others optional |

**Key design features:**

- **SYSTEM_ONLY_FIELDS** — excludes `refs`, `metadata`, `prefs`,
  `actions`, `is_deleted`, `is_archived`, `version`, timestamps, and
  other backend-managed JSONB envelopes from Create/Update interfaces
- **MODEL_ALIASES** — resolves 8 naming mismatches between
  `WCAPI_BLESSED_MODELS` keys and actual Django class names (e.g.,
  `SalesOrder` → `Order`, `PurchaseOrder` → `Purchase`)
- **FK handling** — FK fields emit `attname` (e.g., `customer_id: number`)
  matching WCAPI save payload convention
- **Comments** — each field carries inline TS comments: FK targets,
  choices, max_length, read-only status

**Relationship to hand-written types:** The 68 existing type files in
`src/apps/*/models/*/types/*.ts` remain in use. They contain:

- Component props (`CustomerAddProps`, `OrderAddProps`, etc.)
- Rich JSONB sub-types (`OrgFinancial`, `TransactionTotals`, etc.)
- Domain-specific interfaces (`ItemSearchType`, `TransactionFlow`, etc.)
- Extended response types (`CustomerApiTask`, `OrderApiTask`)

The generated `modelTypes.ts` provides **scalar-field ground truth** —
the canonical list of every column on every model with correct types,
nullability, and optionality. Hand-written types reference these or
extend them for UI-specific needs.

**7 models skipped** (in `WCAPI_BLESSED_MODELS` but no Django class
exists yet): Campaign, Flow, GlJournal, Ledger, LinkageIndex,
Specification, TaxJurisdiction.

**Usage:**

```bash
# Regenerate all types
npm run generate:types

# Or directly:
cd webClerk3 && python manage.py generate_ts_types \
  --out ../React2025/src/generated/modelTypes.ts

# Single model preview (stdout)
python manage.py generate_ts_types --model customer

# List available models
python manage.py generate_ts_types --list

# Filter by app
python manage.py generate_ts_types --app transactions
```

**Why management command over drf-spectacular?** The original
recommendation was drf-spectacular → OpenAPI → `openapi-typescript`.
The management command approach was chosen because:

1. **Serializer coverage is incomplete** — 19 serializers use
   `fields = "__all__"` and many models have no serializer at all
2. **WCAPI bypasses serializers** — `SaveWcapiView` writes directly
   via services, so serializer-generated types wouldn't match the
   actual API surface
3. **Model `_meta` is the single source of truth** — every field that
   exists in the database is captured, regardless of which serializer
   or view exposes it
4. **Zero dependencies** — no additional packages needed; works with
   the existing Django + WCAPI_BLESSED_MODELS infrastructure

**Future enhancement:** When hand-written types are migrated to import
from `modelTypes.ts`, the generated file becomes the single source and
hand-written files shrink to component props and JSONB sub-types only.

---

### 18. Error Envelope Consistency — ✅ Implemented

**Status:** Completed 2025-07-03

**Problem:** The frontend expects `ApiEnvelope<T>`:

```ts
{ status: string, code: number, message: string, error?: any, data: T }
```

Most WCAPI responses follow this shape via `AutoEnvelopeMiddleware`, but:
- Auth responses (`/wcapi/login/`, `/wcapi/token_refresh/`) sometimes
  returned flat `{ access, refresh }` instead of `{ data: { access, refresh } }`.
- The frontend handled both (`data.data.access || data.access`) — a
  workaround for backend inconsistency.

**What was done:**

1. **Backend — Auth views converted to `api_response()`:**
   All four auth views in `apps/core/views/auth_views.py` now use
   `api_response()` from `common/api_responses.py` which sets
   `_api_enveloped = True` on the response, preventing double-wrapping
   by `AutoEnvelopeMiddleware`:
   - `AuthLoginView`: `api_response(data={user, access, refresh}, message="login successful")`
   - `AuthLogoutView`: `api_response(data=None, message="logged out")`
   - `AuthMeView`: `api_response(data={"user": data}, message="authenticated")`
   - `AuthRegisterView`: `api_response(data={user, access, refresh}, message="registration successful", status_code=201)`
   - Error responses use `error={"code": "...", "details": ...}` structure

2. **Frontend — Removed dual-parse workarounds:**
   - `auth.ts`: Simplified token extraction to `payload?.access`
     (removed `payload?.token ?? payload?.access_token ?? payload?.tokens?.access` chain)
   - `axios.ts`: Simplified refresh interceptor to use `body?.data?.access`
     with compact fallback for flat SimpleJWT responses

---

### 19. Token Storage Security — ✅ Implemented

**Status:** Completed 2025-07-03

**Problem:** JWT tokens were stored in `localStorage`, which is accessible
to any JavaScript running on the page (XSS risk).

**What was done:**

Moved refresh token to an `httpOnly` `SameSite=Lax` cookie. Access token
lives in memory only. On page load, `bootstrapAuth()` calls
`/wcapi/token_refresh/` to acquire a fresh access token from the cookie.

**Backend changes:**

1. **`apps/core/views/token_cookie.py`** (new) — Shared cookie helpers:
   - `REFRESH_COOKIE_NAME = "refresh_token"`, `REFRESH_COOKIE_PATH = "/wcapi/"`,
     `REFRESH_COOKIE_SAMESITE = "Lax"`, `REFRESH_COOKIE_HTTPONLY = True`,
     `REFRESH_COOKIE_SECURE = not DEBUG`
   - `set_refresh_cookie(response, refresh_token)`, `clear_refresh_cookie(response)`

2. **`apps/core/views/cookie_token_refresh.py`** (new) — Custom
   `CookieTokenRefreshView` replacing SimpleJWT's stock `TokenRefreshView`:
   - Reads refresh from `request.COOKIES["refresh_token"]`, falls back to
     `request.data.get("refresh")` for backwards compatibility
   - Blacklists old token, issues new access + rotated refresh
   - Sets new refresh cookie, returns `api_response(data={"access": token})`
   - Clears cookie on invalid/expired/user-not-found errors

3. **`apps/core/urls.py`** — Replaced `TokenRefreshView` with
   `CookieTokenRefreshView`

4. **`apps/core/views/auth_views.py`** — Login and Register set refresh
   cookie and exclude `refresh` from JSON body. Logout clears the cookie.

**Frontend changes:**

1. **`axios.ts`:**
   - `accessToken` initialized as `null` (removed IIFE reading from localStorage)
   - `persistTokens()` only stores access token in memory variable
   - `clearTokens()` cleans legacy localStorage keys for migration
   - `authClient` has `withCredentials: true` for httpOnly cookie sending
   - 401 interceptor sends empty body `{}` to refresh endpoint (cookie auto-sent)
   - New `bootstrapAuth()` export — calls `/wcapi/token_refresh/` on page load
     to acquire access token from cookie, returns token or null
   - New `getAccessToken()` export — returns current in-memory token for
     diagnostics/dev tools

2. **`auth.ts`:**
   - `login()` reads only `access` from response, no longer reads `refresh`
   - `logout()` sends empty body (server clears cookie)

3. **`AuthInitializer.tsx`:**
   - No longer checks `localStorage.getItem("accessToken")`
   - Calls `bootstrapAuth()` first to recover session from cookie
   - Then fetches user profile if token recovered

4. **`authSlice.ts`:**
   - Removed `hasStoredToken()` (no longer checks localStorage for tokens)
   - `isLoading: true` always on init — AuthInitializer resolves via bootstrapAuth

5. **`AdminWorkbench.tsx`**, **`networkDiagnostics.ts`**, **`testDashboard.ts`:**
   - Replaced `localStorage.getItem("accessToken")` with Redux `isAuthenticated`
     state or `getAccessToken()` import

---

## Role-Based Write Policy

### 20. WCAPI Write-Field Enforcement — ✅ Implemented

**Status:** Completed 2026-02-15

**Problem:** The `RoleAwareModelSerializer` system existed but was only
used by DRF ViewSets. The WCAPI save path (`SaveWcapiView`) bypasses
serializers entirely — any authenticated user could write any field on
any model via `/wcapi/save/`.

**What was done:**

1. **Enhanced `enforce_write_policy()`** in `apps/core/utils/model_policies.py`:
   - Calls `write_allowlist(model, request)` using the existing
     `WCAPI_MODEL_POLICIES` settings infrastructure
   - Strips disallowed fields from the payload before the field
     assignment loop
   - `SYSTEM_ONLY_FIELDS` (`id`, `uuid`, `dt_created`, `dt_modified`,
     `version`, `is_deleted`, `is_archived`, `health_rating`) are always
     stripped for non-admin users
   - `PASSTHROUGH_KEYS` (`model_name`, `id`, `version`, `lines`, etc.)
     are never stripped (structural envelope keys)
   - Logs denied fields via `wcapi.policy` logger
   - Returns `(filtered_data, denied_fields)` tuple

2. **Fixed `_roles_for()`** — now includes the `Contact.role` field
   value (`admin`, `employee`, `user`) in the role resolution chain.
   Previously only checked `is_superuser`/`is_staff`.

3. **Wired into both save paths** in `apps/core/views/save_view.py`:
   - `_perform_save()` (~line 327) — called by `SaveWcapiViewWithModel`
   - `post()` (~line 1582) — direct HTTP entry point

4. **Expanded `WCAPI_MODEL_POLICIES`** in `webclerk3_api/settings.py`
   with write policies for 16 model keys:

| Model | Admin | Employee | User (default) |
|---|---|---|---|
| `contact` | `*` | email, names, role | email, names |
| `orgbase` | `*` | display_name, contact, address, terms, financial, etc. | none |
| `item` | `*` | name, sku, description, price, cost, catalog, etc. | none |
| Transaction headers (order, invoice, proposal, purchase) | `*` | status, priority, customer, pricing, terms, etc. | status, comments |
| Transaction lines (orderline, invoiceline, etc.) | `*` | item, quantity, price, cost, status, etc. | status, quantity, comments |
| `payment` | `*` | status, amount, method, reference | none |

**Role resolution order** (first match wins in `by_role`):
1. `admin` — if `is_superuser` or `is_staff` is `True`
2. `Contact.role` value — `"employee"`, `"admin"`, `"user"`
3. Django group names
4. `"user"` — fallback (always present)

**Design decisions:**
- **Opt-in, safe by default** — models without policies get NO filtering
  (unrestricted). This preserves backward compatibility for all existing
  models while allowing incremental policy rollout.
- **Silent stripping, not rejection** — disallowed fields are silently
  removed rather than returning 403. This prevents frontend breakage if
  policies are tightened. Stripped fields are logged for audit.
- **Complementary to DRF serializers** — `RoleAwareModelSerializer`
  handles read-side filtering for DRF ViewSet responses.
  `enforce_write_policy()` handles write-side filtering for WCAPI saves.

**Tests:** `tests/test_write_policy.py` — 21 tests covering:
- `_roles_for()` resolution (6 tests)
- `write_allowlist()` per-role resolution (5 tests)
- `enforce_write_policy()` field stripping (7 tests)
- End-to-end `SaveWcapiView` integration (3 tests)

---

## Implementation Order

Suggested sequence for the team to tackle these:

| Sprint | Items | Effort |
|---|---|---|
| ~~**This week**~~ | ~~#1 DEFAULT\_PERMISSION\_CLASSES~~ ✅, ~~#2 JWT lifetime~~ ✅, #15 remove print() | ~~2 hours~~ |
| ~~**Next sprint**~~ | ~~#3 AllowAny audit~~ ✅, ~~#7 ReadOnlyModelViewSet~~ ✅, ~~#9 rate limiting~~ ✅ | ~~4 hours~~ |
| ~~**Following**~~ | ~~#4 serializer fields~~ ✅, ~~#5 soft-delete filtering~~ ✅, ~~#6 ViewEditPermission~~ ✅ | ~~1 day~~ |
| ~~**Backlog (P2)**~~ | ~~#10 signals refactor~~ ✅, ~~#11 remove .delay()~~ ✅, ~~#12 middleware split~~ ✅ | ~~completed~~ |
| ~~**Backlog (P3)**~~ | ~~#13 admin~~ ✅, ~~#14 tests~~ ✅, ~~#15 remove print()~~ ✅, ~~#16 FK naming~~ ✅ | ~~completed~~ |
| ~~**R25 alignment**~~ | ~~#17 type generation~~ ✅, ~~#18 envelope consistency~~ ✅, ~~#19 token storage~~ ✅ | ~~completed~~ |
| **Ongoing** | ~~#16 FK naming rollout~~ ✅ | ~~completed~~ |

---

## Related Documentation

- [FK Naming Conventions](../models/fk-naming-conventions.md) — field
  naming rules and rename inventory
- [FK-First Migration Policy](../models/fk-first-migration.md) — FK vs
  `.refs` policy
- [Save Path Consolidation](save-path-consolidation.md) — WCAPI save
  architecture
- [Model Name Conventions](../models/model_name_conventions.md) — endpoint
  & table naming
