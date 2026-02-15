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
    - [4. Replace fields = "\_\_all\_\_" in Serializers](#4-replace-fields--__all__-in-serializers)
    - [5. Consistent Soft-Delete Filtering](#5-consistent-soft-delete-filtering)
    - [6. Create or Remove ViewEditPermission](#6-create-or-remove-vieweditpermission)
  - [P2 — WCAPI as the Single Write Gate](#p2--wcapi-as-the-single-write-gate)
    - [7. Consolidate /api/ and /wcapi/ Write Paths](#7-consolidate-api-and-wcapi-write-paths)
    - [8. WCAPI Write Guard — How It Works Today](#8-wcapi-write-guard--how-it-works-today)
    - [9. Add Rate Limiting](#9-add-rate-limiting)
  - [P2 — Architecture](#p2--architecture)
    - [10. Refactor Transaction Signals](#10-refactor-transaction-signals)
    - [11. Bootstrap Celery (or Remove .delay Calls)](#11-bootstrap-celery-or-remove-delay-calls)
    - [12. Split common/middleware.py](#12-split-commonmiddlewarepy)
  - [P3 — Hygiene \& Developer Experience](#p3--hygiene--developer-experience)
    - [13. Register Missing Admin Models](#13-register-missing-admin-models)
    - [14. Testing Infrastructure](#14-testing-infrastructure)
    - [15. Remove Debug print() Statements](#15-remove-debug-print-statements)
    - [16. FK Naming Convention Rollout](#16-fk-naming-convention-rollout)
  - [R25 Frontend Alignment](#r25-frontend-alignment)
    - [17. Type Generation from Django Models](#17-type-generation-from-django-models)
    - [18. Error Envelope Consistency](#18-error-envelope-consistency)
    - [19. Token Storage Security](#19-token-storage-security)
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
| **P0** | Security — prevent unauthorized access | 3 |
| **P1** | Data safety — prevent accidental data exposure | 3 |
| **P2** | Architecture — consolidate and harden | 6 |
| **P3** | Hygiene — clean up tech debt | 4 |
| **R25** | Frontend alignment | 3 |

---

## P0 — Security (do first)

### 1. Add DEFAULT\_PERMISSION\_CLASSES

**Problem:** `REST_FRAMEWORK` in `webclerk3_api/settings.py` has no
`DEFAULT_PERMISSION_CLASSES`. Any DRF view that omits `permission_classes`
silently defaults to `AllowAny`, exposing data to unauthenticated callers.

**Fix:**

```python
# webclerk3_api/settings.py
REST_FRAMEWORK = {
    ...
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

Views that genuinely need public access (login, signup, system info) can
override with `permission_classes = [AllowAny]` explicitly. This inverts
the default from "open unless locked" to "locked unless opened."

**R25 impact:** None — the frontend already sends JWT on every request via
Axios interceptors.

---

### 2. Reduce JWT Access-Token Lifetime

**Problem:** `ACCESS_TOKEN_LIFETIME = timedelta(days=7)` is far too long.
A leaked token grants 7 days of full access.

**Fix:**

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),   # was 7 days
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),       # was 30 days
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

**R25 impact:** The frontend already handles 401 → refresh → replay via
the Axios interceptor in `src/api/axios.ts`. Shorter access tokens will
trigger more refreshes, but the existing queue-and-replay logic handles
this transparently. Test the flow after changing.

---

### 3. Audit AllowAny on Write Endpoints

**Problem:** Several ViewSets and views use `permission_classes = [AllowAny]`
on endpoints that accept POST/PUT/PATCH:

| File | View | Risk |
|---|---|---|
| `apps/products/views/inventory_views.py` | Inventory adjustments | Write without auth |
| `apps/transactions/views/purchase_views.py` | Purchase orders | Write without auth |
| `apps/docs/views/linkage_views.py` | Linkage entries | Write without auth |
| `apps/sync/views/connection_views.py` | Sync connections | Write without auth |

**Fix:** Replace `AllowAny` with `IsAuthenticated` on all write endpoints.
For read-only public endpoints (e.g., system info, catalog browsing), use
a split permission class:

```python
class ReadOnlyOrAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated
```

---

## P1 — Data Safety & Correctness

### 4. Replace fields = "\_\_all\_\_" in Serializers

**Problem:** 19 serializers use `fields = "__all__"`, exposing every model
field including `is_deleted`, `version`, `dt_modified`, `refs`, and other
internal columns. This bypasses the `RoleAwareModelSerializer` system
designed for field-level access control.

**Affected files (13 of the 19 are in products):**

| File | Count |
|---|---|
| `apps/products/serializers.py` | 13 |
| `apps/transactions/serializers/transaction_serializers.py` | 3 |
| `apps/transactions/serializers/requisition.py` | 1 |
| `apps/core/views/action_views.py` | 1 |
| `apps/orgs/admin.py` (admin form) | 1 |

**Fix:** Replace each `fields = "__all__"` with an explicit field list.
Inherit from `RoleAwareModelSerializer` to get automatic field filtering
by user role. At minimum, add `read_only_fields` for system columns:

```python
class ItemSerializer(RoleAwareModelSerializer):
    class Meta:
        model = Item
        fields = [
            "id", "uuid", "ida", "description", "sku",
            "unit_price", "cost", "is_active", "status",
            # ... explicit list
        ]
        read_only_fields = ["id", "uuid", "dt_created", "dt_modified", "version"]
```

---

### 5. Consistent Soft-Delete Filtering

**Problem:** The default manager (`objects = FullManager()`) returns all
records including soft-deleted. Views and serializers using
`Model.objects.all()` inadvertently include deleted records.

WCAPI's `services.list_items()` applies its own filtering, but the DRF
ViewSets under `/api/` typically call `self.get_queryset()` which returns
the unfiltered manager.

**Fix — option A (recommended):** Override `get_queryset()` in all
ViewSets to use `.active()`:

```python
class CustomerViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Customer.objects.active()
```

**Fix — option B:** Add a second default manager that auto-filters:

```python
class BaseModel(models.Model):
    objects = FullManager()           # all records (admin, debugging)
    active_objects = ActiveManager()  # is_active=True, is_deleted=False

    class Meta:
        default_manager_name = "objects"  # keep full for admin
```

Then use `Model.active_objects` in views and serializers.

---

### 6. Create or Remove ViewEditPermission

**Problem:** `apps/transactions/views/line_views.py` imports
`ViewEditPermission` from `apps.core.permissions`, but no class with that
name exists in the codebase. The import either silently fails or points to
dead code.

**Fix:** Either:
- **Create it** in `apps/core/permissions.py` — a proper permission class
  that checks model-level view/edit rights based on user role and the
  Setting-driven `get_accessible_fields()` system.
- **Remove it** and use `IsAuthenticated` + per-view logic instead.

---

## P2 — WCAPI as the Single Write Gate

### 7. Consolidate /api/ and /wcapi/ Write Paths

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
- No per-model **field-level write protection** — any authenticated user
  can write any field. The `RoleAwareModelSerializer` system exists but
  is not wired into WCAPI's `SaveWcapiView`.
- No **rate limiting** at any layer (see item 9).

---

### 9. Add Rate Limiting

**Problem:** No throttling is configured. A compromised token or bot
could hammer the API indefinitely.

**Fix:**

```python
# webclerk3_api/settings.py
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

For write-heavy endpoints (transaction saves with lines), consider a
separate throttle scope:

```python
class TransactionSaveThrottle(UserRateThrottle):
    scope = "transaction_save"
    rate = "30/minute"
```

---

## P2 — Architecture

### 10. Refactor Transaction Signals

**Problem:** `apps/transactions/signals.py` is 756 lines with 30+
receivers. The same inventory-tracking pattern (pre\_save → capture
original, post\_save → create pending adjustment, post\_delete → release)
is copy-pasted for 5 line types: ProposalLine, OrderLine, InvoiceLine,
PurchaseLine, WorkOrderLine.

Duplicate helpers:
- `_resolve_item_id_from_line()`
- `_resolve_item_id_from_purchase_line()`
- `_resolve_item_id_from_workorder_line()`

All do the same thing with different field names.

**Fix:** Create a generic signal factory:

```python
def register_line_inventory_signals(line_model, item_resolver, parent_field):
    """Register pre_save/post_save/post_delete signals for inventory tracking."""

    @receiver(pre_save, sender=line_model)
    def track_original(sender, instance, **kwargs):
        if instance.pk:
            instance._original = sender.objects.filter(pk=instance.pk).first()

    @receiver(post_save, sender=line_model)
    def create_pending(sender, instance, created, **kwargs):
        item_id = item_resolver(instance)
        if not item_id:
            return
        # ... shared logic

# Usage:
register_line_inventory_signals(OrderLine, resolve_item_id, "order")
register_line_inventory_signals(InvoiceLine, resolve_item_id, "invoice")
```

This reduces the file from ~756 lines to ~150.

---

### 11. Bootstrap Celery (or Remove .delay Calls)

**Problem:** Multiple files call `.delay()` on functions that are **not
decorated with `@shared_task`**:

| File | Offending call |
|---|---|
| `common/refs/tasks.py` | `prune_refs_for_owner.delay(...)` |
| `common/tasks.py` | `refresh_keywords_task` (called as function) |
| `apps/products/tasks.py` | `process_pending_inventory_task` (called as function) |

No `webclerk3_api/celery.py` exists. No `CELERY_BROKER_URL` in settings.
These `.delay()` calls will **raise `AttributeError` at runtime**.

**Fix — option A (recommended for now):** Remove `.delay()` calls and
run tasks synchronously via `transaction.on_commit()`:

```python
from django.db import transaction

# Instead of task.delay(owner_id):
transaction.on_commit(lambda: prune_refs_for_owner(owner_id))
```

**Fix — option B (when ready for async):** Create
`webclerk3_api/celery.py`, add `CELERY_BROKER_URL` to settings, decorate
all task functions with `@shared_task`, and run a worker process.

---

### 12. Split common/middleware.py

**Problem:** `common/middleware.py` is 382 lines containing 6+ middleware
classes mixing logging, envelope formatting, write gating, and exception
handling. Two classes (`WCAPISearchGuardMiddleware`,
`EnvelopeMiddleware`) are defined but **not listed in `MIDDLEWARE`** —
dead code.

**Fix:** Split into focused modules:

```
common/
  middleware/
    __init__.py            → re-exports for settings.MIDDLEWARE
    logging.py             → RequestLogMiddleware
    envelope.py            → AutoEnvelopeMiddleware
    security.py            → WriteGateMiddleware
    exceptions.py          → ExceptionAsJsonMiddleware
    rendering.py           → EnsureRenderedMiddleware
```

Remove the unused `WCAPISearchGuardMiddleware` and `EnvelopeMiddleware`
or consolidate into the active classes.

---

## P3 — Hygiene & Developer Experience

### 13. Register Missing Admin Models

**Problem:** Several models in `WCAPI_BLESSED_MODELS` have no Django
admin registration, making them invisible in the admin UI for debugging:

| App | Missing Models |
|---|---|
| `support` | `Campaign` (entire admin.py is empty) |
| `accounts` | `Ledger`, `TaxJurisdiction`, `GlJournal` |
| `transactions` | `PaymentMethod`, `PaymentTerm`, `PaymentApplication` |
| `products` | `InventoryReservation`, `Specification`, `Flow` |
| `docs` | `LinkageIndex` |

**Fix:** Add minimal admin registrations with `list_display`, `search_fields`,
`list_filter`. Use the existing `ScalarFirstFieldsetMixin` for auto-generated
fieldsets where possible.

---

### 14. Testing Infrastructure

**Current gaps:**
- No coverage configuration (`.coveragerc` or `pytest-cov` in `pytest.ini`)
- No shared fixtures — each test creates its own data
- No factory library (factory\_boy or model\_bakery)
- `WriteGateMiddleware` skipped during tests — never tested
- 86 test files flat in one directory

**Recommended additions:**

```ini
# pytest.ini
[pytest]
addopts = --cov=apps --cov=common --cov-report=term-missing --cov-fail-under=40
```

```python
# tests/conftest.py
import factory
from apps.orgs.models import OrgBase, Customer

class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrgBase

    display_name = factory.Sequence(lambda n: f"Customer {n}")
    org_type = "customer"
    is_active = True
```

Organize tests into subdirectories matching apps:
```
tests/
  core/
  orgs/
  products/
  transactions/
  conftest.py
```

---

### 15. Remove Debug print() Statements

**Problem:** Production-reachable code paths contain `print()` calls that
should use `logging`:

| File | Example |
|---|---|
| `apps/orgs/admin.py` | `print(f"Form cleaned_data: ...")`, `print(f"save_model called: ...")` |
| `apps/orgs/models/base.py` | `print(f"Validation error during save (continuing anyway): {e}")` |
| Various signals and views | `print()` for debugging |

**Fix:** Replace all with `logger.debug()` or `logger.warning()`:

```python
import logging
logger = logging.getLogger(__name__)

# Instead of: print(f"Validation error: {e}")
logger.warning("Validation error during save (continuing): %s", e)
```

---

### 16. FK Naming Convention Rollout

See [FK Naming Conventions](../models/fk-naming-conventions.md) for the
full inventory. Summary:

- **48 FK fields** use `_id` suffix (Pattern B) — need rename +
  `db_column` override
- Work in batches by app: orgs → core → products → transactions →
  accounts → docs/sync
- Each rename is a Python-only change (no DB migration) when `db_column`
  is set

---

## R25 Frontend Alignment

### 17. Type Generation from Django Models

**Problem:** TypeScript interfaces in r25 (`src/apps/*/types/`) are
manually maintained copies of Django model fields. They drift as fields
are added, renamed, or removed on the backend.

**Options:**

| Approach | Effort | Accuracy |
|---|---|---|
| **drf-spectacular** → OpenAPI → `openapi-typescript` | Medium | Auto-generated from serializers |
| **django-typer** or custom management command | Low | Generates TS from model `_meta` |
| **Manual + lint rule** | Low | JSDoc `@see` comments + code-review discipline (current approach) |

**Recommended:** Use `drf-spectacular` (already partially configured for
schema generation at `/wcapi/schema/`) to produce an OpenAPI spec, then
run `openapi-typescript` in r25's build pipeline to generate types. This
eliminates manual drift.

---

### 18. Error Envelope Consistency

**Problem:** The frontend expects `ApiEnvelope<T>`:

```ts
{ status: string, code: number, message: string, error?: any, data: T }
```

Most WCAPI responses follow this shape via `AutoEnvelopeMiddleware`, but:
- Auth responses (`/wcapi/login/`, `/wcapi/token_refresh/`) sometimes
  return flat `{ access, refresh }` instead of `{ data: { access, refresh } }`.
- The frontend handles both (`data.data.access || data.access`) — a
  workaround for backend inconsistency.
- DRF ViewSet responses (`/api/...`) are **not** wrapped in the envelope
  (middleware only matches `/wcapi/` prefix).

**Fix:** Ensure all auth endpoints return the standard envelope. The
frontend can then remove the dual-parse fallback logic.

---

### 19. Token Storage Security

**Problem:** JWT tokens are stored in `localStorage`, which is accessible
to any JavaScript running on the page (XSS risk).

**Options:**

| Storage | XSS Risk | CSRF Risk | Complexity |
|---|---|---|---|
| `localStorage` (current) | **High** | None | Low |
| `httpOnly` cookie | None | Medium (mitigated by SameSite) | Medium |
| In-memory + `httpOnly` refresh cookie | None | Low | Medium |

**Recommended:** Move refresh token to an `httpOnly` `SameSite=Strict`
cookie. Keep access token in memory only (the module-level variable in
`axios.ts` already does this). On page load, call `/wcapi/token_refresh/`
to get a new access token from the cookie.

This eliminates localStorage token storage entirely while maintaining the
existing Axios interceptor flow.

---

## Implementation Order

Suggested sequence for the team to tackle these:

| Sprint | Items | Effort |
|---|---|---|
| **This week** | #1 DEFAULT\_PERMISSION\_CLASSES, #2 JWT lifetime, #15 remove print() | 2 hours |
| **Next sprint** | #3 AllowAny audit, #7 ReadOnlyModelViewSet, #9 rate limiting | 4 hours |
| **Following** | #4 serializer fields, #5 soft-delete filtering, #6 ViewEditPermission | 1 day |
| **Backlog** | #10 signals refactor, #11 Celery, #12 middleware split, #13 admin, #14 tests | 2–3 days |
| **R25 alignment** | #17 type generation, #18 envelope consistency, #19 token storage | 1 day |
| **Ongoing** | #16 FK naming rollout (batch per app) | 30 min/batch |

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
