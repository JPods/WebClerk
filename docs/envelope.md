# Unified API Response Envelope

Canonical specification for the JSON envelope emitted by **all** API endpoints (Universal `wcapi/*` + dedicated DRF views + future async job status endpoints). Middleware + exception handlers enforce this contract so new code cannot silently diverge.

## Schema

Keys are optional unless marked REQUIRED. Order is not semantically significant (JSON object), but shown in conventional order.

```jsonc
{
  "status": "success",          // REQUIRED: "success" | "error"
  "message": "Human summary",    // Optional: short human-readable explanation (success OR error)
  "data": { /* or [] */ },        // Present on success when returning resource(s)
  "error": {                      // Present when status=="error"
    "code": "validation_error",  // REQUIRED when error object present (stable machine code)
    "details": { /* OPTIONAL structured info (e.g. field errors) */ }
  },
  "meta": {                       // OPTIONAL diagnostics / pagination / tracing
    "total": 123,
    "page_size": 50,
    "next": "?page=3",
    "previous": null,
    "request_id": "9f3c..."     // Mirrors X-Request-ID header (if configured)
  }
}
```

### Minimal Success

```json
{ "status": "success", "message": "Deleted" }
```

### Minimal Error

```json
{ "status": "error", "error": { "code": "not_found" }, "message": "Resource not found" }
```

### Design Notes

- `status` replaces the legacy boolean `success`; only `success` | `error` allowed.
- `message` is always permissible for user / developer clarity; avoid leaking internals in production error messages.
- Put new cross-cutting, non-domain-specific fields under `meta` to preserve top-level stability.
- Pagination MUST populate `meta.total`, `meta.page_size`, `meta.next`, `meta.previous` when the endpoint is inherently list/paged.
- `error.code` values are machine-stable identifiers. Prefer `snake_case` and keep them short.

## Current Error Codes

| Code | HTTP | Description | Source |
|------|------|-------------|--------|
| validation_error | 400 | Serializer / payload validation failed | DRF ValidationError |
| permission_denied | 403 | Authenticated but lacks permission | DRF PermissionDenied |
| not_found | 404 | Object or route missing | Django/DRF NotFound/404 handler |
| version_conflict | 412 | Optimistic concurrency (If-Match) mismatch | Custom VersionConflict exception |
| rate_limited | 429 | Throttle scope exceeded | DRF Throttled |
| server_error | 500 | Unhandled exception catch‑all | 500 handler |

Planned (add when implemented & tested): `authentication_failed` (401), `method_not_allowed` (405), `bad_media_type` (415).

## Enforcement Infrastructure

| Component | Responsibility |
|-----------|----------------|
| `common/api_responses.api_response` | Single construction helper used by views / services |
| `common.middleware.AutoEnvelopeMiddleware` | Wraps any dict/list/QuerySet JSON responses, stamps `status` & merges meta |
| `common/exception_handlers.py` | Normalizes DRF + Django exceptions to envelope errors |
| Custom `handler404`, `handler500` | Ensures non-DRF paths still generate proper envelope |
| Skip telemetry (in middleware) | Records any deliberate bypass (streaming, file responses) for pytest summary |

Excluded path prefixes (never wrapped): `/admin/`, `/static/`, `/media/`.

## Raw / Transitional Mode (Deprecated)

Temporary escape hatch (DEV ONLY):

```bash
export API_ENVELOPE_ALLOW_RAW=1  # enable raw passthrough for debugging
```

Even when enabled, avoid committing tests or clients that rely on raw responses. Removal date tracked in `docs/upgrade.md` (roadmap section).

Per-request bypass (rare, e.g. third‑party signature constraints): set `request._skip_envelope = True` **before** returning a `JsonResponse`. Each skip is surfaced in test run summaries; unexpected skips fail CI (future gate).

## Legacy Key Bubbling Removal (2025-09-02)

During the migration window (Aug–early Sept 2025) middleware mirrored selected nested `data` keys (e.g. `results`, `count`, aggregation metrics) onto the top level of the envelope to keep untouched legacy tests green. This shim is now **removed**. Tests and clients must access payload fields strictly via:

```python
payload['data']['results']      # list resources
payload['data']['count']        # pagination count (or better: use meta.total when implemented)
payload['data']['total_lines']  # aggregation example
```

Top-level lookups like `payload['results']` or `payload['count']` will now fail. Update any remaining references accordingly. Validation field errors likewise remain inside `error.details` (do not assume bubbled field keys at the root). If more ergonomic shortcuts are desired, add helper accessors in client code rather than re‑introducing middleware mutation.

## Pagination Meta

Populate when returning a *bounded window* of a larger logical list. Recommended keys:

| Key | Type | Meaning |
|-----|------|---------|
| total | int | Total matching resources (ignoring pagination window) |
| page_size | int | Requested / effective page size |
| next | str/null | Query string for next page (or absolute URL) |
| previous | str/null | Query string for previous page |
| request_id | str | Trace correlation token (if middleware assigns) |

## Testing & Guardrails

Representative tests (add new ones for new codes / variants):

- `tests/test_response_envelope_contract.py`
- `tests/test_error_envelope.py`
- `tests/test_envelope_skip_reporting.py`

When adding an error code:

1. Implement mapping in exception handlers / raising site.
2. Add table row above.
3. Add test asserting HTTP status + `error.code` + shape.

## Versioning Policy

Minor, *additive* meta fields require no version bump. Breaking changes (renaming keys, removing existing required keys) are disallowed without a deprecation cycle documented in `docs/upgrade.md`. If we ever introduce `v2`, we will support both for a defined overlap window and negotiate via `Accept: application/vnd.webclerk.v2+json` (planned, not yet required).

## Client Guidance

Pseudocode for robust client handling:

```python
payload = response.json()
if payload.get("status") == "error":
    code = payload.get("error", {}).get("code", "unknown")
    raise ApiError(code, payload.get("message"), details=payload.get("error", {}).get("details"))
data = payload.get("data")
meta = payload.get("meta", {})
```

Avoid relying on ordering or incidental fields; treat absence of `data` on success as an operation that yielded no resource body (e.g., DELETE, idempotent action trigger).

## FAQ

**Why not replicate HTTP codes inside `error.code`?**  
Semantic codes are more stable & expressive (`validation_error` beats repeating `400`). HTTP status still conveys coarse category to intermediaries.

**Why keep `message` instead of forcing clients to interpret codes?**  
Developer diagnostics and user‑facing toasts benefit from concise summaries; `code` is for branching logic, `message` for humans.

**Can we embed partial success info?**  
Return `status: "success"`, encode per-item issues under `meta.partial_failures` with an array of `{id, code, message}` objects; do **not** mix success+error top-level statuses.

---

Maintain this document as the single source of truth; keep root `README.md` section concise and link here.
