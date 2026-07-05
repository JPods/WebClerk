# Alice Observations — Setup and Coaching Guide
**Created:** 2026-07-03
**Purpose:** How Alice learns from user behavior in real-time, and how to coach users through the system.

---

## What Alice Observations Are

Alice watches what happens in the browser and logs patterns to the `alice_observations` table. This feeds her pattern recognition loop:

**observe → log → pattern → recommend → promote**

Observations come from three sources:
1. **Console capture** — automatic. Errors, warnings, and significant events from the browser console
2. **Signal handlers** — automatic. Server-side events (invoice saved, payment applied, inventory adjusted)
3. **Manual** — Alice or a power user creates an observation about a workflow pattern

---

## How It Works

### Browser → Alice Pipeline

```
Browser console (errors, warnings)
    ↓ consoleCapture.ts (auto-flush every 60s)
    ↓ POST /wcapi/save/ {model_name: "alice_observation"}
    ↓ AliceObservation record created
    ↓ Alice pattern detection (scheduled)
    ↓ Promoted to AlicePreset or Setting (if pattern confirmed)
```

### The Models

| Model | Table | Purpose |
|-------|-------|---------|
| `AliceObservation` | `alice_observations` | Raw patterns, anomalies, coaching suggestions |
| `AlicePreset` | `alice_presets` | Promoted searches, layouts, workflows ("paved paths") |
| `AliceCoachingLog` | `alice_coaching_log` | Training drill completions, user progress |

All three are in `apps/ai_assistant/models_alice.py` and accessible via wcapi.

### wcapi Access

```bash
# Create an observation
POST /wcapi/save/
{
  "model_name": "alice_observation",
  "data": {
    "category": "pattern",      # pattern, anomaly, coaching, alert, search, layout, performance
    "source": "alice",           # alice, wchq, power_user, console_capture
    "priority": 0,               # 0=normal, 1=important, 2=urgent
    "message": "Short description",
    "detail": "Longer explanation or data",
    "model_name": "order",       # optional: which model this is about
    "record_id": 42,             # optional: which record
    "dedup_key": "unique-key"    # optional: prevents duplicate observations
  }
}

# Read observations
GET /wcapi/get/?model_name=alice_observation&category=pattern&resolved=false

# Acknowledge
POST /wcapi/save/
{
  "model_name": "alice_observation",
  "id": 1,
  "data": {"acknowledged": true, "dt_acknowledged": 1783114333349}
}

# Resolve
POST /wcapi/save/
{
  "model_name": "alice_observation",
  "id": 1,
  "data": {"resolved": true, "resolution": "Fixed by adjusting the workflow"}
}
```

---

## Setup Checklist

### 1. Django Models (already done)

The import in `apps/ai_assistant/models.py`:
```python
from apps.ai_assistant.models_alice import AliceObservation, AlicePreset, AliceCoachingLog  # noqa: F401
```

### 2. wcapi Registry (already done)

Alias map in `apps/core/services/wcapi_registry.py`:
```python
_ALIAS_MAP = {
    'alice_observation': 'aliceobservation',
    'alice_observations': 'aliceobservation',
    'alice_preset': 'alicepreset',
    'alice_coaching_log': 'alicecoachinglog',
    ...
}
```

### 3. Console Capture (already done)

`src/utils/consoleCapture.ts` — started at app boot in `main.tsx`:
```typescript
consoleCapture.start();
```

Auto-flushes errors and warnings to `alice_observation` every 60 seconds.

### 4. Database Migration

If deploying to a new instance:
```bash
python3 manage.py makemigrations ai_assistant
python3 manage.py migrate
```

Tables: `alice_observations`, `alice_presets`, `alice_coaching_log`

---

## Observation Categories

| Category | When Alice creates it | Example |
|----------|----------------------|---------|
| `pattern` | Repeated user behavior detected | "User searches for 'widget' then filters by vendor — 5 times this week" |
| `anomaly` | Data doesn't look right | "Invoice #45 has 0 lines but status is 'released'" |
| `coaching` | User could benefit from a shortcut | "You're manually filtering by status — try the 'Open Orders' preset" |
| `alert` | Something needs attention now | "3 invoices past due > 90 days for customer ACME" |
| `search` | Search pattern worth saving | "Frequent search: items where on_hand < reorder_point" |
| `layout` | Layout suggestion | "You always hide the 'uuid' column — Alice can remove it from the default view" |
| `performance` | Slow query or UI issue | "DataBrowser load time > 3s for Invoice model (2,000+ records)" |
| `console` | Browser error captured | "Failed to fetch staff badge prefs: 401" |

---

## Coaching Users — How Alice Teaches

### The AliceHintBar

The `AliceHintBar` component shows unacknowledged observations to the user. It appears at the top of relevant pages:

- **Pattern observations** show as suggestions: "Alice noticed you frequently..."
- **Anomaly observations** show as warnings: "Alice found a data issue..."
- **Coaching observations** show as tips: "Did you know you can..."

Users acknowledge hints to dismiss them. Alice tracks which hints are acknowledged vs ignored — ignored hints that recur get promoted to `important` priority.

### Training Drills (via Quiz Engine)

Alice's quiz engine (Document records with `model_name="quiz"`) provides learning drills:

1. User opens Alice Training page
2. Alice selects questions based on the user's role and past performance
3. User answers multiple-choice questions
4. Results logged to `AliceCoachingLog`
5. Alice adjusts future question difficulty based on scores

Quiz categories: `commerce_flow`, `models`, `tools`, `billing`, `data_quality`, `inventory`

### Promoted Presets (AlicePreset)

When Alice confirms a pattern (observed 5+ times across 2+ users), she promotes it to an `AlicePreset`:

| Preset Type | What it creates | Example |
|-------------|----------------|---------|
| `search` | Saved search with filters | "Open orders for customer ACME" |
| `layout` | DataBrowser column layout | "Invoice list with payment status columns" |
| `dashboard` | Dashboard widget config | "Aging summary by customer" |
| `workflow` | Multi-step action sequence | "Order → verify inventory → create PO if needed → invoice" |
| `report` | Report preset | "Monthly sales by rep with commission" |

Presets are available to all users. Alice tracks usage (`use_count`, `dt_last_used`) and retires unused presets after 90 days.

---

## For Developers

### Adding New Observation Sources

Any code — server or client — can create observations:

**Python (server-side):**
```python
from apps.ai_assistant.models_alice import AliceObservation

AliceObservation.objects.create(
    category='anomaly',
    source='alice',
    message='Invoice has 0 lines but status is released',
    detail=f'Invoice #{invoice.id}, status={invoice.status}',
    model_name='invoice',
    record_id=invoice.id,
    dedup_key=f'zero-lines-invoice-{invoice.id}',
)
```

**JavaScript (client-side):**
```typescript
import apiClient from '@/api/axios';

await apiClient.post('/wcapi/save/', {
  model_name: 'alice_observation',
  data: {
    category: 'pattern',
    source: 'alice',
    message: 'User navigated Order→Invoice→Payment in sequence',
    model_name: 'order',
    record_id: orderId,
  },
});
```

### Dedup Key

Use `dedup_key` to prevent duplicate observations. Before creating, check:
```python
if not AliceObservation.objects.filter(dedup_key=key, resolved=False).exists():
    AliceObservation.objects.create(dedup_key=key, ...)
```

### Lifecycle

1. **Created** — `resolved=False`, `acknowledged=False`
2. **Acknowledged** — user saw it, `acknowledged=True`, `dt_acknowledged` set
3. **Resolved** — issue fixed or pattern promoted, `resolved=True`, `resolution` text
4. **Pruned** — acknowledged observations older than 30 days are pruned by Alice's housekeeping task

---

## MCP Integration

Alice's MCP server (`alice-mcp-server.py`) includes the `alice_observe` tool:

```
alice_observe(event="pattern", model_name="order", message="...", data={...})
```

This writes to the `alice_log` table in the Allie database (separate from WC3). For cross-system observations, use both: `alice_observe` for Allie's memory, `wcapi save` for WC3's record.

---

## Files

| File | What it does |
|------|-------------|
| `apps/ai_assistant/models_alice.py` | AliceObservation, AlicePreset, AliceCoachingLog models |
| `apps/ai_assistant/models.py` | Imports models_alice (line 7) |
| `apps/core/services/wcapi_registry.py` | `_ALIAS_MAP` maps underscore names to Django model_names |
| `React2025/src/utils/consoleCapture.ts` | Browser console capture → auto-flush to alice_observation |
| `React2025/src/main.tsx` | `consoleCapture.start()` at app boot |
| `React2025/src/contexts/AliceContext.tsx` | Alice hint bar, observation display |
| `apps/ai_assistant/services/user_patterns.py` | Pattern detection, observation creation |
| `apps/ai_assistant/services/field_change_requests.py` | Field change requests as observations |
