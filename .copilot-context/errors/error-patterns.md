# Known Error Patterns

> Curated list of common errors with diagnosis and fixes.
> Used by the AI debugger mode and Copilot to provide instant solutions.
> Add new patterns as they're discovered.

---

## Django / Backend Errors

### CSRF 403 Forbidden on POST/SAVE

**Error:**
```
Forbidden (403)
CSRF verification failed. Request aborted.
```

**Cause:** Missing CSRF token on API request from frontend.

**Fix:**
- For JWT-authenticated requests: Ensure the endpoint is in `CSRF_EXEMPT_URLS` in settings.py
- For session-authenticated requests: Include `X-CSRFToken` header from the `csrftoken` cookie
- All `/wcapi/` endpoints should be CSRF-exempt when using Bearer auth
- Check `webclerk3_api/settings.py` → `CSRF_EXEMPT_URLS` list

---

### Line Save 500 — Required Fields Missing

**Error:**
```
IntegrityError: null value in column "xxx" violates not-null constraint
```
or
```
ValidationError: {'field_name': ['This field is required.']}
```

**Cause:** `transaction_save.save_transaction_with_lines()` requires certain fields per line type.

**Fix:**
- Check required fields in the model: `apps.transactions.models.base_line_model.BaseLineModel`
- Common missing fields: `item_id`, `quantity`, `unit_price`, `line_number`
- Line numbers are auto-assigned if not provided (see `transaction_save._assign_line_numbers()`)
- Use `apps.transactions.services.line_item_service.add_item_to_transaction()` instead of raw save — it handles defaults

---

### Pending Stuck in "processing" State

**Error:** Pending records remain in `status="processing"` and never complete.

**Cause:** Celery worker crashed mid-task or the inventory processor hit an unhandled exception.

**Fix:**
```python
from apps.core.models import Pending
# Reset stuck pendings back to 'new'
Pending.objects.filter(
    status='processing',
    dt_modified__lt=timezone.now() - timedelta(hours=1)
).update(status='new')
```
- Then restart Celery: `./start_celery.sh`
- Check `logs/celery.log` for the original error
- Root cause is usually in `apps.transactions.services.pending_inventory_processor`

---

### Model Resolver KeyError

**Error:**
```
KeyError: 'model_name_here'
```
in `apps.core.services.wcapi_registry.get_model()`

**Cause:** The model name is not registered in the WCAPI registry.

**Fix:**
- Add the model to `apps.core.services.wcapi_registry.MODEL_REGISTRY`
- Use the snake_case version of the model name (e.g., `order_line` not `OrderLine`)
- Also ensure the model has `to_universal_dict()` if it extends `BaseModel`
- Check: `python manage.py shell -c "from apps.core.services.wcapi_registry import MODEL_REGISTRY; print(sorted(MODEL_REGISTRY.keys()))"`

---

### Optimistic Locking — VersionConflictError

**Error:**
```
VersionConflictError: Expected version X, found Y
```

**Cause:** Two concurrent saves to the same record. `CoreModel.optimistic_save()` detected a version mismatch.

**Fix:**
- Refresh the object from DB before saving: `obj.refresh_from_db()`
- In frontend: show a "record was modified by another user" warning and reload
- Don't suppress this error — it prevents data loss

---

### 4D Sync Connection Timeout

**Error:**
```
httpx.ConnectTimeout: Timed out connecting to 4D server
```

**Cause:** The 4D server is unreachable or the VPN is down.

**Fix:**
- Verify 4D server IP/port in settings: `FOUR_D_HOST`, `FOUR_D_PORT`
- Check if the VPN connection is active
- Try: `curl http://<4D_HOST>:<4D_PORT>/rest/$info`
- If timeout persists, check firewall rules on the 4D server

---

## React / Frontend Errors

### TypeError: Cannot read properties of undefined (reading 'id')

**Common in:** Detail pages, transaction forms

**Cause:** Component rendered before data loaded. The record object is `undefined` during initial render.

**Fix:**
- Add a loading guard: `if (!record) return <LoadingSpinner />;`
- Check that the `useWCAPI()` hook returns data before accessing nested fields
- For transaction lines: ensure the lines array is initialized as `[]` not `undefined`

---

### Hydration Mismatch / useLayoutEffect Warning

**Error:**
```
Warning: useLayoutEffect does nothing on the server
```

**Cause:** Server-side rendering mismatch (not actually used in this project, but appears in dev mode).

**Fix:** This is a development-only warning from React Strict Mode. Safe to ignore. Not present in production builds.

---

### API Response 401 — Token Expired

**Error:**
```
AxiosError: Request failed with status code 401
```

**Cause:** JWT token expired. The interceptor in `src/api/axios.ts` should auto-refresh.

**Fix:**
- Check that the refresh token endpoint is configured: `VITE_API_URL/auth/token/refresh/`
- If refresh also fails: user session fully expired, redirect to login
- Check `src/api/axios.ts` interceptor for the refresh logic

---

### Form Save Returns 400 — Validation Errors

**Error:**
```json
{"status": "error", "errors": {"field_name": ["Error message"]}}
```

**Cause:** Backend validation rejected the payload.

**Fix:**
- Check the error response body — it lists exactly which fields failed
- Common issues: missing required fields, invalid choice values, duplicate unique constraints
- In `transaction_save`: totals are verified server-side, so a frontend calculation mismatch causes a 400
- Use `verify_line_calculations()` before saving if you've modified line amounts

---

### AdvancedDataTable — Column Not Found

**Error:**
```
Error: Column 'field_name' not found in data
```

**Cause:** The column config references a field that doesn't exist on the model.

**Fix:**
- Check the model's `to_universal_dict()` output — it defines available fields
- Nested JSON fields use dot notation: `metadata.flags.status` not `metadata_flags_status`
- Ensure the field is included in the WCAPI `get` response (some fields are excluded for performance)

---

## Celery / Background Task Errors

### Worker Not Receiving Tasks

**Error:** Tasks created but celery worker log shows nothing.

**Cause:** Redis broker is down or worker is connected to wrong queue.

**Fix:**
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Restart celery
./start_celery.sh

# Check active queues
celery -A webclerk3_api inspect active_queues
```

---

### Task Timeout — SoftTimeLimitExceeded

**Error:**
```
celery.exceptions.SoftTimeLimitExceeded
```

**Cause:** A task exceeded the default 5-minute soft time limit.

**Fix:**
- For long tasks: set `soft_time_limit` and `time_limit` in the task decorator
- Check if the task is doing N+1 queries (common in batch operations)
- Use `select_related()` / `prefetch_related()` for queryset operations inside tasks

---

## Adding New Patterns

When you encounter a new recurring error:

1. Add it to this file under the appropriate section
2. Include: error text, cause, and fix
3. Run `python manage.py index_docs --source copilot_context` to reindex
4. The AI debugger will now recognize this pattern immediately
