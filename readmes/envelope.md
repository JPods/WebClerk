<!-- Canonical envelope spec (migrated from README_s/envelope.md on consolidation). -->

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

Even when enabled, avoid committing tests or clients that rely on raw responses. Removal date tracked in upgrade roadmap.

Per-request bypass (rare, e.g. third‑party signature constraints): set `request._skip_envelope = True` **before** returning a `JsonResponse`. Each skip is surfaced in test run summaries; unexpected skips fail CI (future gate).

## Legacy Key Bubbling Removal

During a migration window middleware mirrored selected nested `data` keys (e.g. `results`, `count`) onto the top level to keep untouched legacy tests green. This shim is now **removed**. Access payload strictly via:

```python
payload['data']['results']
payload['data']['count']
```

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

1. Implement mapping.
2. Add table row above.
3. Add test asserting HTTP status + `error.code` + shape.

## Versioning Policy

Additive meta fields require no version bump. Breaking changes (renaming keys, removing existing required keys) follow deprecation cycle documented in upgrade roadmap. Future `v2` may negotiate via `Accept: application/vnd.webclerk.v2+json`.

## Client Guidance

```python
payload = response.json()
if payload.get("status") == "error":
	code = payload.get("error", {}).get("code", "unknown")
	raise ApiError(code, payload.get("message"), details=payload.get("error", {}).get("details"))
data = payload.get("data")
meta = payload.get("meta", {})
```

## FAQ

**Why not replicate HTTP codes inside `error.code`?** Stable semantic codes are more expressive. HTTP conveys coarse class.

**Why keep `message`?** Human diagnostics; `code` is for branching.

**Partial success?** Return `status: "success"` and embed per-item issues under `meta.partial_failures`.

---
Maintain this document as the single source of truth; root `README.md` links here.
