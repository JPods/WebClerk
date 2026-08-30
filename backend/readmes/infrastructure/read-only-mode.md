# READ_ONLY_MODE — Database Write Protection

**Created:** 2026-08-09
**Setting:** `READ_ONLY_MODE=True` in `.env`

---

## What It Does

A single `.env` setting turns any WebClerk instance into a read-only database. Four independent layers enforce the lock — all controlled by one boolean:

| Layer | Where | What it blocks |
|-------|-------|---------------|
| **1. Middleware** | `common/middleware/security.py` | All POST, PUT, PATCH, DELETE HTTP methods — rejected before reaching any view |
| **2. Save view** | `apps/core/views/save_view.py` | `/wcapi/save/` — returns 405 at the top of `post()` before any processing |
| **3. Delete view** | `apps/core/views/wcapi.py` | `/wcapi/delete/` — returns 405 at the top of `_do_delete()` |
| **4. Admin** | `webclerk3_api/urls.py` | Django admin URL is removed from the URL configuration entirely |

All four layers return the same JSON response:
```json
{
  "detail": "This is a read-only demo. Download WebClerk at webclerk.com to modify data."
}
```

**Optional fifth layer** — use a SELECT-only PostgreSQL user for defense in depth:
```sql
CREATE ROLE webclerk_ro WITH LOGIN PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE your_db TO webclerk_ro;
GRANT USAGE ON SCHEMA public TO webclerk_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO webclerk_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO webclerk_ro;
```

---

## When to Use It

| Use Case | Why |
|----------|-----|
| **Public demo** | Let prospects browse real data without risk of vandalism |
| **Audit snapshot** | Freeze a database at a point in time for review |
| **Archive instance** | Keep historical data accessible but immutable |
| **Training environment** | Students can explore without breaking anything |
| **Staging review** | QA team reviews data without accidental changes |
| **Compliance hold** | Legal requires data preservation during investigation |

---

## How to Enable

Add one line to `.env`:
```env
READ_ONLY_MODE=True
```

Restart the service:
```bash
sudo systemctl restart webclerk3
```

That's it. All writes are blocked. Reads continue normally.

### To disable — remove the line or set to False:
```env
READ_ONLY_MODE=False
```

---

## What Still Works in Read-Only Mode

| Feature | Works? | Notes |
|---------|--------|-------|
| Browse data via React app | Yes | All GET requests pass through |
| DataBrowser list/detail views | Yes | Read-only |
| API queries (`/wcapi/get/`, `/wcapi/query/`) | Yes | Full query capability |
| Reports and dashboards | Yes | Read-only data |
| Search | Yes | Including saved searches |
| Login/authentication | Yes | Session-based auth works (no DB write needed after initial login) |
| Save records | No | 405 — blocked at middleware and view layers |
| Delete records | No | 405 — blocked at middleware and view layers |
| Django admin | No | URL removed entirely |
| Celery tasks that write | No | DB user rejects writes if SELECT-only role is used |

---

## Architecture

```
                    HTTP Request
                         │
                    ┌────▼────┐
                    │  Nginx  │
                    └────┬────┘
                         │
                ┌────────▼────────┐
          Layer 1│  WriteGate     │ ← blocks POST/PUT/PATCH/DELETE
                │  Middleware     │   when READ_ONLY_MODE=True
                └────────┬────────┘
                         │ (GET passes through)
                         │
        ┌────────────────┼────────────────┐
        │                │                │
  ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
  │  /wcapi/  │   │  /wcapi/  │   │  /admin/  │
  │  save/    │   │  delete/  │   │           │
  │ Layer 2   │   │ Layer 3   │   │ Layer 4   │
  │ 405 block │   │ 405 block │   │ URL gone  │
  └───────────┘   └───────────┘   └───────────┘
        │                │
        └────────┬───────┘
                 │ (never reached)
          ┌──────▼──────┐
   Layer 5│  PostgreSQL │ ← SELECT-only user
          │  (optional) │   rejects INSERT/UPDATE/DELETE
          └─────────────┘
```

---

## Implementation Details

### settings.py
```python
READ_ONLY_MODE = config('READ_ONLY_MODE', default=False, cast=bool)
```

### WriteGateMiddleware (Layer 1)
```python
if self._read_only_mode:
    return JsonResponse({
        'detail': 'This is a read-only demo. ...',
    }, status=405)
```

### SaveWcapiView.post() (Layer 2)
```python
if getattr(settings, 'READ_ONLY_MODE', False):
    return api_response(success=False, status_code=405, ...)
```

### WCAPIDeleteView._do_delete() (Layer 3)
```python
if getattr(_settings, 'READ_ONLY_MODE', False):
    return api_response(success=False, status_code=405, ...)
```

### urls.py (Layer 4)
```python
*([] if getattr(settings, 'READ_ONLY_MODE', False) else [path('admin/', admin.site.urls)]),
```

---

## See Also

- [Production Deployment](production-deployment.md) — full deployment guide including demo instance setup
- [Minimal Viable Install](minimal-viable-install.md) — seed commands for demo data
