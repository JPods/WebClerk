# Table Registry & Permissions Refactor

<!-- TOC START -->

## Table of Contents

- [Table Registry & Permissions Refactor](#table-registry--permissions-refactor)
  - [Table of Contents](#table-of-contents)
  - [Summary](#summary)
  - [Motivations](#motivations)
  - [Key Artifacts](#key-artifacts)
    - [Table Registry](#table-registry)
    - [Validation](#validation)
    - [Permissions](#permissions)
    - [Registry API Endpoint](#registry-api-endpoint)
    - [Purge Utility](#purge-utility)
  - [Migration / Reset Approach](#migration--reset-approach)
  - [Test Additions](#test-additions)
  - [Extension Points](#extension-points)
  - [Quick Usage](#quick-usage)
    - [New entries: Work Orders](#new-entries-work-orders)
  - [Gotchas](#gotchas)
  - [Next Steps (Optional)](#next-steps-optional)

<!-- TOC END -->

## Summary

Between Sept 3–4 2025 we performed a domain naming and authorization hardening pass:

- Pluralized transactional header & line table physical names.
- Removed temporary legacy alias fallbacks for permissions.
- Introduced a canonical table registry for consistent `model_name` usage across backend, tests, and frontend.
- Enforced strict validation of `Setting.model_target` values.
- Added endpoint to introspect registry & (optionally) field metadata.
- Added purge utility for stale legacy `Setting` rows.

All tests: **156 passed, 1 skipped** after changes.

## Motivations

| Problem | Impact | Resolution |
|---------|--------|------------|
| Inconsistent singular/plural names | Permission mismatches, cognitive load | Standardized plural for multi-row tables (`orders`, `order_lines`, etc.) |
| Silent legacy alias mapping | Risk of drift & hidden coupling | Removed alias layer, forced explicit corrections |
| No authoritative table metadata source | Duplication in serializers, views, docs | Added centralized registry (`TABLE_REGISTRY`) |
| Unvalidated `Setting.model_target` | Typos caused 403s with little guidance | Model + serializer validation with explicit enum list |
| Hard to inspect allowed tables on frontend | Manual syncing, fragile | `/wcapi/tables/` endpoint (list & detail) |
| Orphan legacy Setting rows | Noise & potential confusion | `purge_legacy_model_names` mgmt command |

## Key Artifacts

### Table Registry

File: `apps/core/constants/model_registry.py`

Provides:

- `TableMeta` dataclass
- `MODEL_REGISTRY` (canonical singular key -> metadata)
- `VALID_MODEL_NAMES` list
- Reverse endpoint lookup helpers
- Lazy model import for field inspection

### Validation

`apps/core/models/setting.py` – `clean()` enforces membership in `VALID_MODEL_NAMES`.
`apps/core/serializers/setting.py` – serializer-level validation mirrors rule.

### Permissions

`apps/core/permissions.py` now uses strict exact table name matches – no fallbacks or heuristic singular stripping.

### Registry API Endpoint

`GET /wcapi/tables/` (list)
`GET /wcapi/tables/?table=<key>&include_fields=1` (detail + field metadata)
`GET /wcapi/tables/?endpoint=<slug>&include_fields=1` (lookup by endpoint slug)

Field metadata includes:

```json
{
  "id": {"type": "BigAutoField", "null": false, "blank": false, "primary_key": true},
  "status": {"type": "CharField", "null": false, "blank": false, "primary_key": false}
}
```

### Purge Utility

Command: `python manage.py purge_legacy_model_names [--apply] [--purpose view_edit]`
Dry run by default; shows count and sample of stale rows.

## Migration / Reset Approach

1. Dropped old migrations, regenerated clean `transactions` initial schema with plural table names.
2. Updated tests to use plural forms only.
3. Removed alias compatibility code.
4. Added validation & registry; fixed any failing tests (introduced `documents` placeholder for existing keyword test).

## Test Additions

- `test_setting_invalid_model_name_rejected` ensures invalid legacy names (e.g. `order_line`) produce 400 with field error.

## Extension Points

| Need | Option |
|------|--------|
| Frontend dynamic form building | Use registry detail with `include_fields=1` |
| Caching | Add ETag or short cache headers to `/wcapi/tables/` |
| Enum exposure in OpenAPI | Generate schema enum from `VALID_model_nameS` |
| Field-level auth overlay | Extend registry to annotate field visibility per role |
| Code generation | Export registry as JSON for client SDK scaffolding |

## Quick Usage

Fetch all tables:

```bash
curl -s http://localhost:8000/wcapi/tables/ | jq '.data.tables | keys'
```

Fetch single table with fields:

```bash
curl -s 'http://localhost:8000/wcapi/tables/?table=order_lines&include_fields=1' | jq '.data.table.fields.status'
```

### New entries: Work Orders

The registry now includes Work Orders:

- workorder — app: `transactions`, endpoint: `/wcapi/work-orders/`, kind: `header`, aliases: work_orders
- workorder_line — app: `transactions`, endpoint: `/wcapi/workorder-lines/`, kind: `line`, aliases: work_order_lines

Examples:

```bash
curl -s 'http://localhost:8000/wcapi/tables/?table=workorder&include_fields=1' | jq '.data.table'
curl -s 'http://localhost:8000/wcapi/tables/?table=workorder_line&include_fields=1' | jq '.data.table'
```

## Gotchas

- Adding a new model requires updating `MODEL_REGISTRY`; forgetting leads to validation errors when creating Settings.
- The placeholder `documents` entry exists solely for an existing settings test – adjust once a real documents model lands.
- Legacy singular settings must be purged or updated before deploying environments that relied on fallback logic.

## Next Steps (Optional)

1. Implement lightweight 60s cache for registry responses.
2. Add management command to export registry as JSON for CI artifact.
3. Introduce `kind` filters (`/wcapi/tables/?kind=line`).
4. Auto-generate OpenAPI components for table & field enums.

---
_Refactor completed Sept 4 2025 – authored via assisted session. Commit includes validation, registry endpoint, and documentation._
