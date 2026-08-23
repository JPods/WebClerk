# Sync WCReact — r25 ↔ wc3 Data Synchronization

## Overview

`common/sync_wcreact/` centralizes canonical data definitions and sync logic for keeping the React2025 frontend (r25) and WebClerk3 backend (wc3) aligned. It covers payment terms, select lists, and any future data that must stay consistent across both systems.

Other `common/sync_*` packages may exist for different sync categories (e.g. `sync_foreign` for external integrations).

---

## Architecture

```
common/sync_wcreact/           ← Shared logic + canonical data
├── __init__.py                 ← Barrel exports
├── terms.py                    ← Payment term definitions + sync
└── selectlists.py              ← Select list definitions + sync

apps/core/management/commands/  ← Thin management-command wrappers
├── sync_terms.py               → common.sync_wcreact.terms
└── sync_selectlists.py         → common.sync_wcreact.selectlists

src/config/                     ← r25 counterparts
├── selectLists.ts              ← TERM_RECORDS, DYNAMIC_LISTS
└── syncSelectLists.ts          ← Fetch/push/merge functions
```

Django management commands must live in `<app>/management/commands/` for auto-discovery. The commands in `apps/core/` are thin wrappers that import all logic from `common/sync_wcreact/`.

---

## Modules

### terms.py — Payment Terms

Defines `TERM_DEFS`, a list of 10 canonical payment terms mirroring `TERM_RECORDS` in r25's `selectLists.ts`.

**Exported functions:**

| Function | Purpose |
|----------|---------|
| `sync_terms(stdout, style, dry_run)` | Create/update Term model records to match `TERM_DEFS`. Idempotent. Returns `(created, updated, unchanged)`. |
| `list_terms(stdout)` | Print all Term records currently in the database. |

**Exported data:**

| Name | Type | Description |
|------|------|-------------|
| `TERM_DEFS` | `list[dict]` | Canonical term definitions (name, description, days_due, etc.) |
| `SYNC_FIELDS` | `list[str]` | Fields compared/updated during sync |

### selectlists.py — Select Lists

Defines `R25_DYNAMIC_LISTS`, a list of 16 select list definitions mirroring `DYNAMIC_LISTS` in r25's `selectLists.ts`. Each list is stored as a wc3 Setting record with `purpose="admin_selectlist"`.

**Exported functions:**

| Function | Purpose |
|----------|---------|
| `push_selectlists_to_wc3(stdout, style, keys, dry_run)` | Push r25 lists → wc3 Setting records. Idempotent. Returns `(created, updated, unchanged)`. |
| `show_selectlists_for_r25(stdout, keys)` | Output wc3 settings formatted as r25 `toOptions()` code. |
| `list_selectlist_settings(stdout, keys)` | Print all `admin_selectlist` Setting records in the database. |

**Exported data:**

| Name | Type | Description |
|------|------|-------------|
| `R25_DYNAMIC_LISTS` | `list[dict]` | Canonical list definitions (key, label, options) |
| `PURPOSE` | `str` | `"admin_selectlist"` — the Setting.purpose value |

---

## Management Commands

### sync_terms

```bash
# Create/update Term records (idempotent)
python manage.py sync_terms

# Preview without saving
python manage.py sync_terms --dry-run

# Show current terms in the database
python manage.py sync_terms --list
```

### sync_selectlists

```bash
# Push r25 lists → wc3 Setting records
python manage.py sync_selectlists --direction to-wc3

# Preview without saving
python manage.py sync_selectlists --direction to-wc3 --dry-run

# Show wc3 settings as r25 toOptions() code (paste into selectLists.ts)
python manage.py sync_selectlists --direction to-r25

# List current admin_selectlist settings
python manage.py sync_selectlists --direction list

# Limit to specific list(s)
python manage.py sync_selectlists --direction to-wc3 --key terms --key priority
```

---

## r25 Sync Service (syncSelectLists.ts)

Six functions for syncing select lists from the React side:

| Function | Purpose |
|----------|---------|
| `fetchSelectListsFromWc3()` | Pull all `admin_selectlist` settings → `Record<key, {options, label, settingId}>` |
| `fetchSelectListFromWc3(key)` | Pull a single list by key |
| `pushSelectListToWc3(key)` | Push one r25 list → wc3 Setting (create or update) |
| `pushAllSelectListsToWc3()` | Push all editable r25 lists → wc3 |
| `mergeWc3SelectLists()` | Fetch from wc3 and override runtime `SELECT_LIST_MAP` — call on app init |
| `diffSelectList(key)` | Compare r25 vs wc3 for a given key — useful for admin UI |

**Typical usage:**

```ts
import { mergeWc3SelectLists, pushSelectListToWc3 } from '@/config/syncSelectLists';

// On app init — merge wc3 overrides into runtime
await mergeWc3SelectLists();

// Admin saves a list — push back to wc3
await pushSelectListToWc3('terms');
```

---

## Data Flow

```
┌──────────────────────────────────────┐
│  r25  selectLists.ts                 │  Source of truth for list shapes
│       DYNAMIC_LISTS / TERM_RECORDS   │  and term metadata
└──────────┬───────────────────────────┘
           │  pushSelectListToWc3()
           │  (or manage.py sync_selectlists --direction to-wc3)
           ▼
┌──────────────────────────────────────┐
│  wc3  Setting records                │  purpose = "admin_selectlist"
│       Term records                   │  name = list key
│       (PostgreSQL)                   │  data = {options, label}
└──────────┬───────────────────────────┘
           │  mergeWc3SelectLists()
           │  (or manage.py sync_selectlists --direction to-r25)
           ▼
┌──────────────────────────────────────┐
│  r25  runtime SELECT_LIST_MAP        │  Admin-edited options override
│       (in-memory)                    │  the compiled defaults
└──────────────────────────────────────┘
```

---

## Setting Record Convention

Select lists are stored as Setting records with:

| Field | Value |
|-------|-------|
| `purpose` | `"admin_selectlist"` |
| `name` | The list key (e.g. `"terms"`, `"priority"`, `"job_list"`) |
| `data` | `{"options": [{value, label}, ...], "label": "Human Name"}` |

This purpose value is registered in `apps/core/choices.py` → `SETTING_PURPOSE_CHOICES`.

---

## Adding a New Sync Target

1. **Create the module** in `common/sync_wcreact/` (e.g. `warehouses.py`).
2. **Add exports** to `common/sync_wcreact/__init__.py`.
3. **Create a thin wrapper** command in `apps/core/management/commands/`.
4. **Create the r25 counterpart** in `src/config/` if the frontend needs sync functions.
5. **Update this readme**.

---

## Current Database State (DEV)

| Data | Count | Command |
|------|-------|---------|
| Term records | 10 (ids 1–10) | `python manage.py sync_terms --list` |
| Select list settings | 16 (ids 116–131) | `python manage.py sync_selectlists --direction list` |

---

## File References

**wc3:**
- [common/sync_wcreact/__init__.py](../../../common/sync_wcreact/__init__.py)
- [common/sync_wcreact/terms.py](../../../common/sync_wcreact/terms.py)
- [common/sync_wcreact/selectlists.py](../../../common/sync_wcreact/selectlists.py)
- [apps/core/management/commands/sync_terms.py](../../../apps/core/management/commands/sync_terms.py)
- [apps/core/management/commands/sync_selectlists.py](../../../apps/core/management/commands/sync_selectlists.py)
- [apps/core/choices.py](../../../apps/core/choices.py) — `SETTING_PURPOSE_CHOICES`

**r25:**
- `src/config/selectLists.ts` — `TERM_RECORDS`, `DYNAMIC_LISTS`, `SELECT_LIST_MAP`
- `src/config/syncSelectLists.ts` — Fetch/push/merge/diff functions
