<!-- MOVED from docs/debug.md on rename. Original left with stub notice. -->

# Development & Debug Configuration Overview


<!-- TOC START -->

## Table of Contents

- [Development & Debug Configuration Overview](#development-debug-configuration-overview)
  - [1. Core Environment Flags](#1-core-environment-flags)
  - [2. Field Access & Bypass Mechanics](#2-field-access-bypass-mechanics)
  - [3. Authentication Endpoints](#3-authentication-endpoints)
  - [4. Serialization Sanitization](#4-serialization-sanitization)
  - [5. Data Seeding Strategy](#5-data-seeding-strategy)
  - [6. Stats & Periodic Tasks](#6-stats-periodic-tasks)
  - [7. Removed / Deferred Concepts](#7-removed-deferred-concepts)
  - [8. Secure Mode Switch](#8-secure-mode-switch)
  - [9. Quick Debug Commands](#9-quick-debug-commands)
  - [10. Future Cleanup Targets](#10-future-cleanup-targets)
  - [11. Summary Snapshot](#11-summary-snapshot)

<!-- TOC END -->

Purpose: Central reference for the temporary / development-only switches, shortcuts, and architectural choices currently active so they are visible, intentional, and easy to revert.

## 1. Core Environment Flags

| Flag | Current Intent | Effect | How to Disable |
|------|----------------|--------|----------------|
| `VIEW_EDIT_DEV_BYPASS=1` | ENABLED during active UI/API build | Field-level access control bypassed; all model concrete fields exposed; edit filtering relaxed | Unset or set to `0` then restart server |
| `WCAPI_OPEN_READ=1` | ENABLED for frictionless GET tests | Allows unauthenticated GET to `/wcapi/get` & related read endpoints (role treated as PUBLIC) | Unset or set to `0` |
| `WCAPI_JWT_ONLY=0` | DISABLED (default) | Session auth OR JWT accepted (plus open read if enabled) | Set to `1` to require Bearer tokens |

Notes:

- If both `WCAPI_OPEN_READ=1` and `WCAPI_JWT_ONLY=1`, the JWT requirement wins for authenticated contexts; unauthenticated read still allowed only if `WCAPI_OPEN_READ=1` AND `WCAPI_JWT_ONLY=0`.
- Bypass is evaluated dynamically each request; toggle the env var then restart to switch behavior.

## 2. Field Access & Bypass Mechanics

See `apps/core/services/view_edit_access.py` – dev bypass returns `['*']` wildcard which is expanded; fail‑open safety returns full record if config rows absent (development only).

## 3. Authentication Endpoints

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `POST /wcapi/login/` | JWT login (alias of `/api/auth/login/`) | Returns access/refresh & user claims |
| `POST /wcapi/signup/` | User registration + tokens | Development convenience |
| `POST /api/token/refresh/` | Refresh JWT | SimpleJWT |
| `GET /login/` | Session (HTML form) | Django sessions |

## 4. Serialization Sanitization

`apps/core/views/get_view.py` – `_sanitize()` coerces non-JSON-safe values (Decimal, datetime, model instances) to primitives.

## 5. Data Seeding Strategy

Single canonical command: `reseed_all_models` (see `manage.md` for options). Legacy multi-command chain removed.

## 6. Stats & Periodic Tasks

Configured in `settings.py` (`CELERY_BEAT_SCHEDULE`): `recompute-basic-stats-hourly`, `recompute-relationship-counts-2h`, `refresh-keywords-30m`.

## 7. Removed / Deferred Concepts

| Concept | Status | Notes |
|---------|--------|-------|
| Verb-style wcapi endpoints | Removed | Consolidated into `/wcapi/get\|save\|query` |
| Multi-command demo rebuild chain | Removed | One reseed command |
| Mutable JSONField default warnings | Addressed | Use callable factories |

## 8. Secure Mode Switch

Unset dev flags, restart, create `Setting` rows per table/role.

## 9. Quick Debug Commands

See quick table in original file; condensed here:

| Goal | Command |
|------|---------|
| Reseed dataset | `python manage.py reseed_all_models --per-model 3` |
| Inspect model counts | One-liner in README root (search `Inspect model counts`) |
| Test open read | `curl http://localhost:8000/wcapi/get/?table_name=contacts` |
| JWT login | cURL POST to `/wcapi/login/` |

## 10. Future Cleanup Targets

- Remove fail-open bypass once matrices complete.
- Replace `WCAPI_OPEN_READ` with scoped allowlist or signed token.
- Add structured audit log for field exposure (optional).
- Add `/wcapi/debug/config` (non-prod) endpoint for effective flags.

## 11. Summary Snapshot

| Area | Choice | Temporary? |
|------|--------|------------|
| Field ACL | Global bypass | YES |
| Auth | Mixed session/JWT + open read | YES |
| Data seeding | Single command | STAYS |
| Serialization | Sanitize non-JSON values | STAYS |
| Logging | One-time debug for missing Setting | MAY CHANGE |
| Stats recompute | Lightweight beat tasks | STAYS |

---

Keep updated whenever a debug flag or development shortcut changes.
