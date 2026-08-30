# WCAPI Choice Catalog Endpoint

## Purpose

Expose a single endpoint that aggregates every `DEFAULT_SELECT_LISTS` definition from app-level `choices.py` modules so frontend clients can build dropdowns without hardcoding enums. The endpoint consolidates data from every Django app registered in this project.

## Endpoint Summary

- **URL**: `/wcapi/choices/`
- **Method**: `GET`
- **Authentication**: Same as other WCAPI endpoints; Add bearer token or session cookie when enforced.

### Query Parameters

| Name     | Type  | Description |
|----------|-------|-------------|
| `app`    | str   | Optional. Repeatable filter for specific Django app labels (e.g. `app=core&app=transactions`). Omitting returns all apps.
| `refresh`| bool  | Optional. Accepts `1`, `true`, or `yes`. When present, clears the cached registry before the response is generated.

### Response Shape

```json
{
  "apps": {
    "core": {
      "Contact": {
        "role": [
          {"value": "", "label": "---------"},
          {"value": "user", "label": "User"}
        ]
      }
    }
  },
  "meta": {
    "app_count": 1,
    "model_count": 3
  }
}
```

- `apps`: grouped by Django app label → model name → field → list of `{value, label}` objects
- `meta.app_count`: number of app labels returned
- `meta.model_count`: total models represented in the response

## Implementation Notes

- Source code: `common/choices_registry.py` and `apps/core/views/choices.py`
- Choice registries are cached via `functools.lru_cache` to minimize import churn. Calling with `refresh=1` clears the cache.
- Non-dict iterables are normalized to lists of `{"value", "label"}` for JSON safety.
- Null or blank options from models must already exist in the underlying `choices.py` files.

## Usage Patterns

### Fetch Everything

```bash
curl -H "Authorization: Bearer <token>" https://<host>/wcapi/choices/
```

### Filter to Selected Apps

```bash
curl "https://<host>/wcapi/choices/?app=core&app=transactions"
```

### Force Cache Refresh

```bash
curl "https://<host>/wcapi/choices/?refresh=1"
```

## Integrating With React 2025

1. Call `/wcapi/choices/` on app bootstrap or when dropdown definitions need to refresh.
2. Persist the payload (Redux/Query cache) and provide typed helpers that return arrays e.g. `choices.apps.core.Contact.role`.
3. Use `refresh=1` when an admin updates server-side `choices.py` definitions and you need the new versions immediately.
4. The React Whitelist Tester preset (see React2025 README) demonstrates live probing of the endpoint.

## Testing Checklist

- `GET /wcapi/choices/` returns HTTP 200 with expected schema.
- Filtering with an invalid app label silently omits it (no error).
- `refresh=1` forces the registry to rebuild (verify via log timestamps or temporary instrumentation).
- Endpoint accessible via the Spectacular-generated API docs under the "Choice catalog" summary.
