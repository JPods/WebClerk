# WCAPI System Endpoints — Underscore Prefix Convention

**Established:** 2026-08-23
**Audience:** System administrators, developers, anyone adding endpoints

## The Rule

All system plumbing endpoints use an underscore prefix: `wcapi/_action/`.

```
wcapi/_pjpv_fields/     ← system plumbing (schema metadata for React)
wcapi/get/order/        ← data endpoint (returns order records)
```

**System plumbing** = metadata, configuration, health checks, and internal
tooling that React needs to render the UI. Not business data.

**Data endpoints** = CRUD operations on business records (orders, invoices,
contacts, items). These use model names in the URL.

## Why the Underscore

Django URL routing is first-match-wins. WC3 uses wildcard patterns for
data endpoints:

```python
path("wcapi/<str:model_name>/get/", ...)    # matches any model name
path("wcapi/<str:model_name>/save/", ...)   # matches any model name
```

A system endpoint like `wcapi/fields/` gets captured by the wildcard —
Django thinks `fields` is a model name, the view tries to look it up,
and returns 404.

The underscore prefix solves this permanently:
- Django model names never start with `_`
- The wildcard `<str:model_name>` will never match `_pjpv_fields`
- No URL ordering issues
- Clear visual separation in logs, browser dev tools, and documentation

**Cost of learning this:** 30 minutes of server restarts and cache clears
debugging a 404 that only appeared in the running server, not in shell tests.
Scar #68.

## Current System Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `wcapi/_pjpv_fields/` | Pydantic schema metadata for React | Public |
| `wcapi/_pjpv_fields/?envelope=totals` | Single envelope schema | Public |

## How to Add a New System Endpoint

Add a handler method to `SystemDispatchView` and register it in the
`ACTIONS` dict. One line each.

```python
# In SystemDispatchView.ACTIONS:
'my_action': '_handle_my_action',

# Add the method:
def _handle_my_action(self, request):
    return Response({'result': 'done'})
```

The URL is automatically `wcapi/_my_action/`. No changes to `urls.py`.

## Candidates for Migration

These existing endpoints are system plumbing, not data. They could move
behind the `_` prefix in a future cleanup:

| Current URL | What it does | Candidate |
|-------------|-------------|-----------|
| `wcapi/bootstrap/` | App startup data | `_bootstrap` |
| `wcapi/system-info/` | Server health/version | `_system_info` |
| `wcapi/choices/` | Choice catalog for selects | `_choices` |
| `wcapi/selectlists/` | Select list options | `_selectlists` |
| `wcapi/settings-health/` | Settings health check | `_settings_health` |
| `wcapi/settings-bootstrap/` | Initial settings load | `_settings_bootstrap` |
| `wcapi/dev/config/` | Dev tools config | `_dev_config` |
| `wcapi/dev/restart/` | Dev server restart | `_dev_restart` |

**Do not migrate these now.** React hardcodes these URLs. Migration requires
coordinated React + Django changes. The `_` prefix convention applies to
all NEW system endpoints going forward.

## Django URL Routing — What System Admins Need to Know

1. **First match wins.** URL patterns are tried in order. A wildcard early
   in the list captures URLs meant for specific patterns later.

2. **`__pycache__` is the enemy.** Django compiles `.py` to `.pyc` bytecode.
   If you change `urls.py` and the server doesn't pick it up:
   ```bash
   find /path/to/webClerk3 -type d -name "__pycache__" -exec rm -rf {} +
   ```
   Then restart the server. The auto-reloader sometimes misses changes to
   files imported at the top of `urls.py`.

3. **`include()` creates a prefix scope.** `path('wcapi/', include(patterns))`
   strips `wcapi/` and matches the remainder against the included patterns.
   This is NOT a problem for `_` prefixed URLs because the dispatcher is
   registered before any `include()`.

4. **The runserver auto-restart loop** (`runserver.sh`) uses a parent process
   that watches files and a child that serves. The child can inherit stale
   module state from the parent. When in doubt: kill the process, clear
   pycache, start fresh.

## Architecture

```
Browser/React
    │
    ├── wcapi/_pjpv_fields/     → SystemDispatchView → schema metadata
    ├── wcapi/_bootstrap/       → SystemDispatchView → app startup data
    ├── wcapi/_choices/         → SystemDispatchView → select options
    │
    ├── wcapi/get/order/        → WCAPIGetView → business data
    ├── wcapi/save/invoice/     → SaveWcapiView → business data
    └── wcapi/transactions/...  → transaction views → business data
```

One URL pattern (`wcapi/_<str:action>/`) routes all system calls.
No ordering conflicts. No wildcard captures. Clear intent.

## See Also

- `pjpv-process.md` — Full PJPV audit and schema buildout
- `pjpv-architecture.md` — The four PJPV rules
- Scar #68 — URL wildcard conflict (leftshoe identity store)
