# Request Security Pipeline — JSON-by-Default, WriteGate, Demo Read-Only
**Created:** 2026-08-09
**Owner:** System (middleware layer — runs before any view)

---

## What It Does

Three middleware layers control what gets into WC3 and what format it speaks. Every HTTP request passes through all three before any view executes:

1. **Demo Read-Only** — blocks ALL writes when enabled (for public demos)
2. **WriteGate** — allow-lists which paths accept write methods (POST/PUT/PATCH/DELETE)
3. **JSON-by-Default** — all responses are JSON unless the path is explicitly HTML-exempt

Flowchart: `readmes/flowcharts/wc3-request-security.dot`
```bash
dot -Tpdf readmes/flowcharts/wc3-request-security.dot -o readmes/flowcharts/wc3-request-security.pdf
```

---

## Layer 1: Demo Read-Only

```python
DEMO_READ_ONLY = config('DEMO_READ_ONLY', default=False, cast=bool)
```

When `True`, **every** write method on **every** path returns 405:

```json
{
    "detail": "This is a read-only demo. Download WebClerk at webclerk.com to modify data."
}
```

No exemptions. No admin. No API writes. The demo is read-only.

**Use case:** webclerk.com public demo instance. Visitors can browse, search, view records — but can't modify anything. They download WC3 to run it locally with full sovereignty.

**Configuration:** Set via environment variable. Not in settings.py directly — prevents accidental hardcoding.

---

## Layer 2: WriteGate

```python
WRITE_GATE_ENABLED = True
```

When enabled, write methods (POST, PUT, PATCH, DELETE) are only allowed on paths that match one of three allow-lists:

### Exact Paths
```python
WRITE_GATE_EXACT_PATHS = (
    '/wcapi/save', '/wcapi/save/',
    '/wcapi/query', '/wcapi/query/',
    '/wcapi/delete', '/wcapi/delete/',
)
```

### Prefix Paths
```python
WRITE_GATE_PREFIXES = (
    '/wcapi/',
    '/api/auth/', '/api/token/', '/wcapi/login/', '/wcapi/signup/',
    '/admin/', '/admin-django/',
)
```

### Regex Paths
```python
WRITE_GATE_ALLOWED_REGEX = (
    r'^/[a-z0-9_]+/\d+/?$',    # /<model>/<id>  (POST update, DELETE single)
    r'^/[a-z0-9_]+/?$',        # /<model>       (DELETE batch by body)
)
```

Any write to a path that doesn't match returns:
```json
{"detail": "WriteGate: path not allowed"}
```
Status: 405.

**Why:** Defense in depth. Even if a new URL route is added without proper auth, WriteGate blocks writes unless the path is explicitly allowed. The gate prevents accidental exposure of write endpoints.

**Test bypass:** Disabled when `PYTEST_CURRENT_TEST` is in the environment.

---

## Layer 3: JSON-by-Default

```python
API_JSON_DEFAULT = True
```

All responses are JSON unless the request path is HTML-exempt. This means:
- Unhandled exceptions → JSON error response (not Django's HTML debug page)
- 404 → JSON `{"detail": "Not found"}`
- 500 → JSON `{"detail": "Internal server error"}`
- Any non-exempt path → JSON content negotiation

### HTML-Exempt Paths

```python
HTML_EXEMPT_PATH_PREFIXES = (
    '/admin/', '/admin-django/', '/static/', '/media/',
    '/api/swagger/', '/api/schema/', '/api/redoc/',
)
```

Plus exact paths (`/`, `/about/`, `/signup/`, `/login/`, `/logout/`) and page prefixes (`/manage/`, `/user/`, `/manager/`).

**Why:** WC3 is API-first. The React frontend talks JSON. Django admin is HTML. Swagger docs are HTML. Everything else is JSON. No accidental HTML responses leaking through API endpoints.

---

## Request Flow

```
HTTP Request
    │
    ▼
[1] Demo Read-Only?
    │ YES + write method → 405 "read-only demo"
    │ NO or GET/HEAD → continue
    │
    ▼
[2] WriteGate
    │ Write method? → check exact → prefix → regex → 405 if no match
    │ GET/HEAD? → skip gate
    │
    ▼
[3] JSON-by-Default
    │ HTML-exempt path? → serve HTML
    │ All other paths → serve JSON (including errors)
    │
    ▼
[4] DRF Auth (JWT/Session) → RBAC → field_access
    │
    ▼
[5] View executes
```

---

## Configuration Summary

| Setting | Default | What it controls |
|---------|---------|-----------------|
| `DEMO_READ_ONLY` | `False` (env var) | Blocks all writes — public demo mode |
| `WRITE_GATE_ENABLED` | `True` | Allow-list enforcement for write paths |
| `WRITE_GATE_EXACT_PATHS` | 3 wcapi paths | Exact path matches for writes |
| `WRITE_GATE_PREFIXES` | 5 prefixes | Prefix matches for writes |
| `WRITE_GATE_ALLOWED_REGEX` | 2 patterns | Regex matches for model CRUD paths |
| `API_JSON_DEFAULT` | `True` | Force JSON responses on non-exempt paths |
| `HTML_EXEMPT_PATH_PREFIXES` | 7 prefixes | Paths that serve HTML (admin, static, docs) |

---

## Files

| File | What it is |
|------|-----------|
| `common/middleware/security.py` | WriteGateMiddleware — blocks unauthorized write paths |
| `common/middleware/exceptions.py` | JSON-by-default exception handler |
| `common/middleware/helpers.py` | `is_template_page()` — HTML exemption logic |
| `webclerk3_api/settings.py:438-463` | All configuration constants |
| `readmes/flowcharts/wc3-request-security.dot` | Visual pipeline diagram |
