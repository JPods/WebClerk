# UserDailyLog — Daily API Usage Aggregation

## Overview

The **UserDailyLog** feature provides per-user, per-day summaries of API
activity with auto-generated diagnostic hints. Raw `APILog` rows are crunched
nightly into a single summary row per user per calendar day, enabling fast
dashboard queries without scanning millions of granular log records.

```
┌────────────┐   nightly   ┌──────────────┐   wcapi   ┌──────────────────────────┐
│  APILog    │──────────▶  │ UserDailyLog │──────────▶│ UserActivityDashboard    │
│  (granular)│  Celery task │  (aggregated)│   GET     │ R25 admin page           │
└────────────┘             └──────────────┘           └──────────────────────────┘
```

---

## File Map

| Layer | File | Role |
|-------|------|------|
| wc3 model | `apps/core/models/log.py` → `UserDailyLog` | Django model — one row per user per day |
| wc3 migration | `apps/core/migrations/0003_add_user_daily_log.py` | Creates `user_daily_logs` table |
| wc3 task | `apps/support/scheduler/tasks.py` → `_aggregate_for_date()` | Groups APILog by user, computes counts & hints |
| wc3 task | `apps/support/scheduler/tasks.py` → `task_aggregate_user_daily_logs` | Celery shared_task wrapper (nightly at 1:30 AM) |
| wc3 settings | `webclerk3_api/settings.py` → `CELERY_BEAT_SCHEDULE` | `aggregate-user-daily-logs-nightly` entry |
| r25 model | `src/apps/core/models/log/UserDailyLog.ts` | TypeScript interface + sub-types |
| r25 service | `src/apps/core/services/userDailyLogApi.ts` | `fetchUserDailyLogs`, `fetchRecentDailyLogs`, `fetchDailyLogsByDate` |
| r25 page | `src/pages/admin/UserActivityDashboard.tsx` | Admin dashboard at `/core/user-activity` |
| r25 route | `src/routes/Routes.ts` → `coreUserActivityDashboard` | Route constant |
| r25 route | `src/routes/protectedRoutesConfig.tsx` | Protected route entry |

---

## Model — `UserDailyLog`

Table: `user_daily_logs`

| Field | Type | Notes |
|-------|------|-------|
| `user` | FK → User | `CASCADE`, related_name `daily_logs` |
| `log_date` | DateField | UTC calendar date |
| `call_counts` | JSONField | Calls by method, endpoint, model, source |
| `response_summary` | JSONField | Success/error totals, durations, status codes |
| `hints` | JSONField (list) | Auto-generated diagnostic entries |
| `error_details` | JSONField (list) | Grouped errors with counts and timestamps |
| `total_calls` | PositiveIntegerField | Denormalized total (fast `ORDER BY`) |
| `total_errors` | PositiveIntegerField | Denormalized error count |
| `avg_duration_ms` | PositiveIntegerField | Average request duration |

**Unique constraint:** `(user, log_date)` — one row per user per day.

Inherits `BaseModel` fields: `id`, `uuid`, `ida`, `dt_created`, `dt_modified`,
`version`, `is_active`, `security_level`.

### JSON Field Schemas

#### `call_counts`

```json
{
  "total": 152,
  "by_method":   { "GET": 120, "POST": 32 },
  "by_endpoint": { "get": 100, "save": 30, "query": 15, "manage": 7 },
  "by_model":    { "order": 45, "item": 30, "contact": 25 },
  "by_source":   { "r25": 140, "wc3": 12 }
}
```

#### `response_summary`

```json
{
  "success_count": 145,
  "error_count": 7,
  "error_rate": 0.046,
  "avg_duration_ms": 85,
  "max_duration_ms": 2400,
  "status_codes": { "200": 140, "201": 5, "400": 3, "500": 4 },
  "slowest_endpoints": [
    { "endpoint": "/wcapi/query/", "model": "order", "duration_ms": 2400 }
  ]
}
```

#### `hints`

```json
[
  { "level": "warning",  "category": "rate_limit",  "message": "Hit rate limit 12 times …", "count": 12 },
  { "level": "error",    "category": "validation",  "message": "3 failed saves on 'order' …",  "count": 3 },
  { "level": "info",     "category": "performance", "message": "5 requests over 2 s …",        "count": 5 }
]
```

#### `error_details`

```json
[
  {
    "endpoint": "/wcapi/save/",
    "model": "order",
    "status_code": 400,
    "error_message": "…",
    "count": 3,
    "first_at": "2026-02-20T14:30:00Z",
    "last_at": "2026-02-20T17:45:00Z"
  }
]
```

---

## Celery Aggregation Task

### `_aggregate_for_date(target_date)`

Private helper that does the actual work:

1. **Queries** `APILog` for the target date grouped by `user_id`
2. **Computes** call breakdowns:
   - `by_method` — GET, POST, PUT, DELETE, etc.
   - `by_endpoint` — last segment of the URL path (get, save, query, manage)
   - `by_model` — extracted from `request_body.model_name`
   - `by_source` — r25, wc3, ext
3. **Computes** response summary:
   - Success vs error counts, avg/max duration, status code histogram
   - Identifies the 5 slowest endpoints
4. **Generates** diagnostic hints based on patterns:

| Hint Category | Trigger Condition | Level |
|---------------|-------------------|-------|
| `error_rate` | >10% error rate (min 10 calls) | warning |
| `performance` | Any request ≥ 2,000 ms | info |
| `validation` | ≥ 3 status-400 responses | error |
| `server_error` | Any status ≥ 500 | error |
| `rate_limit` | Any status 429 | warning |
| `usage` | >500 calls in a day | info |

5. **Upserts** via `UserDailyLog.objects.update_or_create(user_id, log_date)`

### `task_aggregate_user_daily_logs`

```python
@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def task_aggregate_user_daily_logs(self, target_date_str=None):
```

- **Schedule:** nightly at **1:30 AM UTC** via Celery Beat
- **Default:** aggregates the **previous day** (UTC now − 1 day)
- **Manual:** pass `target_date_str='2026-02-20'` to re-aggregate a specific date
- **Tracking:** creates a `TaskRun` record for monitoring
- **Retries:** up to 2 retries with 120 s delay

### Manual Invocation

```python
# Django shell or Celery CLI
from apps.support.scheduler.tasks import task_aggregate_user_daily_logs

# Aggregate yesterday (default)
task_aggregate_user_daily_logs.delay()

# Aggregate a specific date
task_aggregate_user_daily_logs.delay(target_date_str='2026-02-20')
```

---

## R25 Frontend — UserActivityDashboard

**Route:** `/core/user-activity`

### Service API (`userDailyLogApi.ts`)

| Function | Purpose | Params |
|----------|---------|--------|
| `fetchUserDailyLogs(params?)` | Generic fetch with pagination | `user_id`, `log_date`, date range, `ordering`, `limit`, `offset` |
| `fetchRecentDailyLogs(userId, days)` | Last N days for a user | user ID, days (default 14) |
| `fetchDailyLogsByDate(date)` | All users for a specific date | date string `YYYY-MM-DD` |

All functions use `getRecords("userdailylog", ...)` through the wcapi SDK.

### Dashboard Features

- **6 stat cards:** Total Calls, Total Errors, Error Rate, Avg Duration, Diagnostic Hints, Days Covered
- **Two view modes:**
  - *Recent* — last 30 days for the logged-in user (default)
  - *By Date* — all users' activity for a chosen calendar date (admin overview)
- **Expandable day rows** with:
  - Call breakdown by HTTP method, endpoint, model, and source
  - Color-coded status code badges (green 2xx, yellow 3xx, orange 4xx, red 5xx)
  - Diagnostic hint panels with severity icons (info/warning/error)
  - Error group tables with counts and timestamps
- **Dark mode** support via Tailwind classes

---

## Related Models

| Model | Table | Purpose |
|-------|-------|---------|
| `APILog` | `api_logs` | Granular per-request log (source of truth for aggregation) |
| `AuditLog` | `audit_logs` | Data mutation tracking (separate from API usage) |
| `UserDailyLog` | `user_daily_logs` | Daily user aggregate (this feature) |
