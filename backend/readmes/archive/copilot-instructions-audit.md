# Copilot Instructions Audit

> **Date**: 2026-02-21
> **Scope**: Codebase compliance against `.github/instructions/copilot.instructions.md`
> **Status**: Initial audit

---

## Scorecard

| Section | Verdict | Issues |
|---------|---------|--------|
| §2 Model Hierarchy | **PASS** | All 12 mixins + `BaseModel` + `TransactionBaseModel` present and composed correctly |
| §2 Folder Structure | **PASS** | All 9 apps match exactly |
| §2 Services Directories | **PARTIAL** | `communications/` has no `services/` directory |
| §2 Unified API Gateway | **PARTIAL** | `/wcapi/get/` and `/wcapi/save/` registered; `/wcapi/query/` and `/wcapi/manage/` have no URL route |
| §2 Model Registry | **PARTIAL** | `wcapi_registry.py` exists but auto-discovers all models instead of a restrictive allow-list |
| §3 Canonical Renames | **PARTIAL** | Clean except `purchase_order` in `compare_lines.py:112` |
| §4 Response Envelope | **PARTIAL** | `api_response()` + middleware + exception handlers all exist; 2 views in `wcapi.py` hand-roll `Response()` bypassing the helper |
| §5 JSONB / Denorm | **PARTIAL** | All correct except `MAX_METADATA_SIZE` is 128000 in code but 32000 in instructions — docs are stale |
| §5 Denorm Registry | **PASS** | `common/denorm_registry.py` exists; no hard-coded field lists found anywhere |
| §7 Testing | **PARTIAL** | `fast` marker used in 20+ tests but not registered in `pytest.ini`; `slow` and `integration` registered but never used |
| §8 Model Inheritance | **PARTIAL** | 3 models bypass `BaseModel` — `PendingInventoryAdjustment`, `InventoryReservation`, `SoftDeleteLedger` inherit raw `models.Model` |
| §8 No HTML | **PASS** | Zero `render()` or `TemplateResponse()` calls in views |
| §8 Soft Delete | **FAIL** | 15 hard `.delete()` calls across services/views despite instruction to use `LifecycleMixin` soft deletes |
| §9 Save Hooks | **PASS** | Fully implemented with pre/post/async hooks, cached, integrated into save flow |
| §10 Key File Locations | **PASS** | All 10 documented paths exist |

---

## Issues Requiring Code Fixes

### HIGH — 15 hard `.delete()` calls violate "never hard-delete" rule

| File | Line | Context |
|------|------|---------|
| `apps/core/services/wcapi.py` | 319 | Generic `obj.delete()` on any registered model |
| `apps/transactions/services/line_item_service.py` | 558 | `line.delete()` |
| `apps/transactions/services/payment_application.py` | 189 | `application.delete()` |
| `apps/accounts/services/terms_ledger.py` | 360 | Bulk ledger delete |
| `apps/accounts/services/ledger_balance.py` | 372, 568 | Ledger balance delete |
| `apps/transactions/services/inventory_flow.py` | 152, 314 | Reservation hard deletes |
| `apps/products/services/bom_services.py` | 46 | BOM line delete |
| `apps/transactions/views/wcapi.py` | 427 | Generic `obj.delete()` |
| `apps/transactions/views/line_views.py` | 147 | 5 instances of `instance.delete()` for line items |

**Recommendation**: Either override `delete()` in `LifecycleMixin` to call `soft_delete()` (with a `force_hard=False` escape hatch), or replace call sites with `.soft_delete()`. The generic wcapi delete path at `apps/core/services/wcapi.py:319` is the highest risk since it affects all models.

### MED — `/wcapi/query/` and `/wcapi/manage/` not routed

These endpoints are documented in the instructions and referenced in tests (`test_workorders_phase1.py`, `test_wcapi_errors.py`, `settings.py`) but have **no `path()` entry** in any `urls.py`.

**Recommendation**: Either register the routes in `apps/core/urls.py` or remove them from the instructions if they're deferred.

### MED — Model registry is open, not restrictive

`wcapi_registry.py` auto-discovers all installed Django models via `django_apps.get_models()`. The `ALLOWED_TABLE_KEYS` at line 114 is auto-generated, not a curated allow-list. The instructions state "Models must be registered to be accessible."

**Recommendation**: Add an explicit allow-list or document the open discovery as intentional.

---

## Issues Requiring Docs Fixes

### MED — `MAX_METADATA_SIZE` mismatch

Code value: **128000** (`common/models.py:51`)
Instructions value: **32000** (§5)

**Fix**: Update `copilot.instructions.md` §5 to read `MAX_METADATA_SIZE = 128000`.

### LOW — `AuthorizedAccessMixin` undocumented

Exists at `common/models.py:992` but not shown in the §2 hierarchy diagram. `BaseModel` does not inherit from it, so the hierarchy is technically accurate — but the mixin should be mentioned for completeness.

### LOW — `communications/services/` missing

The instructions state "Business logic lives in each app's `services/` package" but `apps/communications/` has no `services/` directory. Either create the directory or note the exemption.

---

## Issues Requiring Test Config Fixes

### LOW — Register `fast` marker in `pytest.ini`

The `@pytest.mark.fast` marker is used in 20+ test files but is **not registered** in `pytest.ini` (only `slow` and `integration` are). This produces pytest warnings.

**Fix**: Add `fast: marks fast unit tests` to the `markers` list in `pytest.ini`.

### LOW — `slow` / `integration` markers never applied

Both markers are registered in `pytest.ini` but no test file uses `@pytest.mark.slow` or `@pytest.mark.integration`. The documented commands (`pytest -m "not slow"`, `pytest -m integration`) are effectively no-ops.

**Fix**: Tag long-running or DB-dependent tests with the appropriate markers.

---

## Minor / Cleanup

| Issue | Location |
|-------|----------|
| Legacy name `purchase_order` in diagnostic script | `compare_lines.py:112` |
| 2 views hand-roll `Response()` instead of `api_response()` | `apps/core/views/wcapi.py` — `ModelListView` (L929), `ModelDetailView` (L988) |
| Bare `{"detail": "invalid model"}` response relies on middleware | `apps/core/views/wcapi.py:981` |
| 3 models inherit raw `models.Model` | `PendingInventoryAdjustment`, `InventoryReservation`, `SoftDeleteLedger` — arguably justified as operational tables |

---

## Summary

The architecture, mixins, denormalization, envelope system, save hooks, and file structure are solidly implemented. The main gap is **hard-delete usage** (15 instances) where the instructions mandate soft deletes. The secondary gaps are **two unrouted wcapi endpoints** and an **open model registry** described as restrictive in the docs. The rest are documentation drift or minor config items.
