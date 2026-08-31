# Frontend Dropdowns System

## Overview

Frontend dropdowns now flow through a single pipeline: JSON metadata defines the options, Django exposes matching `choices`, and WCAPI serves the combined catalog to React. This aligns backend validation and frontend UX without duplicating logic.

## Source of Truth

- Canonical definitions live in [common/choices.json](../../../common/choices.json).
- Each entry stores `domain`, `model`, `field`, `purpose`, `where_used`, `allow_blank`, and the `{value, label}` options.
- `_meta.version` helps consumers detect breaking schema shifts.

**Example snippet:**

```json
"ACTION_KANBAN_COLUMNS": {
  "domain": "core",
  "model": "Action",
  "field": "kanban_column",
  "allow_blank": true,
  "options": [
    {"value": "", "label": "---------"},
    {"value": "Backlog", "label": "Backlog"},
    {"value": "Planning", "label": "Planning"}
  ]
}
```

## Python Loader Layer

- [common/choices.py](../../../common/choices.py) parses the JSON and generates Django-friendly tuples while keeping metadata accessible via helper functions.
- Domain-specific modules re-export the tuples and compose `DEFAULT_SELECT_LISTS` so existing imports remain valid.

## Registry and API

- [common/choices_registry.py](../../../common/choices_registry.py) aggregates every app’s `DEFAULT_SELECT_LISTS`, normalizes entries, and memoizes the payload.
- [apps/core/views/choices.py](../../../apps/core/views/choices.py) exposes `GET /wcapi/choices/`.
  - `app=<label>` (repeatable) filters to specific Django app labels.
  - `refresh=1` clears the in-process cache after JSON edits.
- **Response structure:**

```json
{
  "apps": {
    "core": {
      "Action": {
        "kanban_column": [
          {"value": "", "label": "---------"},
          {"value": "Backlog", "label": "Backlog"}
        ]
      }
    }
  },
  "meta": {
    "app_count": 1,
    "model_count": 1,
    "errors": []
  }
}
```

The endpoint is intentionally unauthenticated so the frontend can prefetch drop-in configuration. Treat the payload as read-only guidance.

## Frontend Consumption Pattern

1. Bootstrap: call `GET /wcapi/choices/?app=core&app=transactions`.
2. Cache results client-side for ~5 minutes to limit chatter.
3. Feed the normalized `{value, label}` pairs straight into select components; server-side validation uses the same tuples.
4. After admin edits, call the endpoint with `refresh=1` to invalidate cached data.

## Editing or Adding Select Lists

1. Update [common/choices.json](../../../common/choices.json).
2. Ensure [common/choices.py](../../../common/choices.py) exports the tuple and the relevant app module includes it in `DEFAULT_SELECT_LISTS`.
3. Run tests to catch import errors recorded by the registry.
4. Document consumer expectations when introducing new lists.

## Future Direction

- JSON definitions will seed Settings records, enabling per-tenant overrides and an admin UI.
- The `GET /wcapi/choices/` contract remains stable; only the storage backend evolves.
- Role-aware and tenant-aware filtering layers will build atop the Settings integration.
