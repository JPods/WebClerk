<!-- Authoritative reset workflow documentation -->

# Destructive Full Reset and Baseline Rebuild

<!-- TOC START -->

## Table of Contents

- [Destructive Full Reset and Baseline Rebuild](#destructive-full-reset-and-baseline-rebuild)
  - [Table of Contents](#table-of-contents)
  - [1. When To Use](#1-when-to-use)
  - [2. What Happens Under The Hood](#2-what-happens-under-the-hood)
  - [3. Usage Cheatsheet](#3-usage-cheatsheet)
  - [3.1. Quick reseed-only (no DB drop)](#31-quick-reseed-only-no-db-drop)
  - [4. Programmatic Invocation](#4-programmatic-invocation)
  - [5. Environment Guards and Safety](#5-environment-guards-and-safety)
  - [6. Post-Reset Checklist](#6-post-reset-checklist)
  - [7. Troubleshooting](#7-troubleshooting)
  - [8. Migration Baseline Policy](#8-migration-baseline-policy)
  - [9. Extending Seeding](#9-extending-seeding)
  - [10. Minimal One-Liner](#10-minimal-one-liner)
  - [11. Data Export (Optional)](#11-data-export-optional)
  - [12. FAQ](#12-faq)
  - [13. Quick Reference](#13-quick-reference)
    - [Safety alert Connection](#safety-alert-connection)
    - [Targeted reseeds (per model)](#targeted-reseeds-per-model)

<!-- TOC END -->

Date: 2025-09-03
Review: 2025-12-15
Status: -- status --
Owner: Bill

This guide documents the **single supported way** to perform a destructive local reset of the development database and re-seed domain data using the unified `reseed` command. Use it sparingly and never on shared / staging / production environments.

Creates 3 SuperUsers (patterned):

| Email | Password |
|-------|----------|
| `1@1.com` | `1111pass` |
| `2@2.com` | `1111pass` |
| `3@3.com` | `1111pass` |

---

## 1. When To Use

Use `reseed --full` only when:

- Migration history has been squashed and you need a clean slate.
- Local schema drift / abandoned experimental migrations cause failures.
- You want freshly seeded synthetic + sample domain data and patterned superusers.
- Tests should run against a pristine baseline state.

Do NOT use:

- To “refresh” production-like data (prefer targeted data loads instead).
- Inside active feature branches just to clear minor local fixtures—resetting is heavy.

---

## 2. What Happens Under The Hood

`python manage.py reseed --full` orchestrates:

1. Environment guard: verifies interpreter matches project `bin/python` & Django 5.x (override with `ALLOW_SYSTEM_PY=1`).
1. Terminates existing PostgreSQL sessions for the target DB.
1. Drops and recreates the database (name from `DATABASE_NAME` / settings).
1. Runs migrations (expects committed `0001_initial` baselines + any new deltas, or freshly regenerated if using `--nuke-migrations --auto-make`).
1. Executes seed commands (idempotent best-effort): `load_default_company`, `load_default_access`, `seed_orgs`, `seed_documents`, `seed_projects`, `seed_transactions`, and `seed_relationships`.
1. Performs a light synthetic backfill via `reseed_all_models` to add sample rows across sparse tables. By default `reseed_all_models` will flush and seed all models and create 3 patterned superusers, unless you target a specific model.
1. Creates 1–N patterned superusers: `i@i.com` / `1111pass` with names `first_i` / `last_i`.
1. Ensures default `sync.Connection` entries exist (safety alert + verification stubs). Currency records can link to a provider `Connection` for external rate updates.
1. Backfills `Location.metadata.display` by saving each Location (ensures `full_location` is populated).
1. Summary output printed with seeds actually applied.

---

## 3. Usage Cheatsheet

Full destructive reset + seed (default 3 superusers):

```bash
python manage.py reseed --full
# end of header block

Reset with 5 superusers and an extra seed command:

```bash
python manage.py reseed --full --superusers 5 --seed-cmd refresh_keywords
```

Regenerate migrations first (dangerous; local dev only):

```bash
python manage.py reseed --full --nuke-migrations --auto-makemigrations
```

Bypass environment guard (e.g., container wrapper):

```bash
ALLOW_SYSTEM_PY=1 python manage.py reseed --full
```

---

### 3.1. Quick reseed-only (no DB drop)

Use this when you want to quickly re-populate synthetic rows across models without recreating the database:

```bash
python manage.py reseed_all_models               # flushes DB, seeds, creates 3 superusers
python manage.py reseed_all_models --dry-run     # show actions without writing
```

Target a single model without flushing and without superusers by default:

```bash
python manage.py reseed_all_models --model apps.core.models.Contact --per-model 5
# or by DB table
python manage.py reseed_all_models --table contacts --per-model 5
```

Overrides:

- Prevent flush: `--no-flush`
- Control superusers: `--superusers N` (negative = auto: 3 for full reseed, 0 when targeting one model)
- Skip relationship pass: `--no-relate`

---

## 4. Programmatic Invocation

```python
from common.rebuild import full_reset_and_seed
res = full_reset_and_seed(create_superusers=2, seed_commands=("seed_orgs",))
print(res)
```

The returned `ResetResult` dataclass exposes: `db_name`, `recreated`, `migrations_applied`, `superusers`, `seed_commands_run`.

---

## 5. Environment Guards and Safety

| Guard | Purpose | Override |
|-------|---------|----------|
| Interpreter match | Prevent running with system Python (wrong Django) | `ALLOW_SYSTEM_PY=1` |
| Django 5.x check | Avoid applying migrations with incompatible version | `ALLOW_SYSTEM_PY=1` |
| DEBUG True | Block accidental destructive ops in prod-like config | `FORCE_FULL_RESET=1` |

The command still refuses if `DJANGO_SETTINGS_MODULE` suggests a production module (contains `prod`).

---

## 6. Post-Reset Checklist

| Step | Command | Notes |
|------|---------|-------|
| Run tests | `./bin/python -m pytest -q` | Should be green (baseline). |
| Create extra admin | `./bin/python create_superuser.py --email admin2@example.com` | Optional. |
| Inspect seed data | `./bin/python manage.py shell` | Sanity-check orgs, items. |
| Envelope telemetry | `./bin/python manage.py storage_load_report --json` | Optional size snapshot. |

---

## 7. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `OperationalError: server closed the connection` | Using stale DB connection handle after drop | Fixed by function (ensure upgraded code). Re-run. |
| `column "name" of relation "django_content_type" does not exist` | Ran migrations with older Django then switched versions | Drop DB & rerun via correct venv. |
| `psql binary not found` | PostgreSQL client tools missing in PATH | Install `psql` / adjust PATH. |
| Seed command missing file warnings | Optional JSON seeds not present | Supply JSON or ignore (non-fatal). |
| Superusers not created | Email collision from prior import | Use higher `--superusers` or drop again. |

Log still shows intermediate product migrations (0002–0006)? They are **no-op stubs**—this is expected.

---

## 8. Migration Baseline Policy

- Historical squashes (e.g., 2025‑09‑03) and subsequent "nukes" produce a single authoritative `0001_initial` per app.
- `--nuke-migrations` is a local developer convenience; DO NOT use on a shared branch without team agreement.
- Never hand-edit applied migration files post-commit; prefer new migration deltas or an intentional coordinated nuke.
- Only re-squash / nuke just before a release boundary or when pruning experimental churn.
- CI Guard: A GitHub Action (`migration_guard`) enforces that each first-party app has at most one numbered migration (the baseline). Set `ALLOW_MULTIPLE_MIGRATIONS=1` secret to temporarily bypass.
- Standalone script: `./bin/python -m common.rebuild.nuke_migrations` performs the same deletion/regeneration outside the full reset command.

---

## 9. Extending Seeding

Add a new management command and chain it by passing `--seed-cmd new_command` or programmatically supplying a tuple. Keep seeds:

- Idempotent (safe to re-run).
- Fast (< a few seconds) to keep reset cycles tight.
- Resilient to partial existing data (use get_or_create / try/except guards).

---

## 10. Minimal One-Liner

```bash
FORCE_FULL_RESET=1 ALLOW_SYSTEM_PY=1 python manage.py reseed --full
```

Fast local reset with defaults (seeds + 3 superusers).

---

## 11. Data Export (Optional)

If you maintain evolving demo snapshots, run an export immediately after a clean reset *before* hand edits:

```bash
python manage.py demo_data_import_export --export demo_snapshot.json
```
Commit only if intentionally curating a shared demo baseline.

---

## 12. FAQ

Q: Why not call `makemigrations` automatically?
A: Reset assumes committed, reviewed migration files. Auto-generation inside a destructive reset risks unreviewed schema drift.

Q: Why do we still see product migrations 0002–0006 apply?
A: They are zero-op placeholders retained only to satisfy Django’s dependency graph for any stale references; they do nothing.

Q: Can I run only the seeding portion?
A: Use existing seed commands directly (e.g., `python manage.py seed_orgs`). `full_reset_seed` always recreates the DB first.

---

## 13. Quick Reference

| Action | Command |
|--------|---------|
| Full reset + seed + 3 superusers | `python manage.py reseed --full` |
| Full reset with 5 superusers | `python manage.py reseed --full --superusers 5` |
| Programmatic call | `from common.rebuild import full_reset_and_seed` |
| Bypass env guard | `ALLOW_SYSTEM_PY=1 python manage.py reseed --full` |

### Safety alert Connection

`reseed --full` also ensures a safety alert connection exists and performs location display backfill:
 
### Targeted reseeds (per model)

Use the unified command to reseed only a specific model/table without flushing:

```bash
python manage.py reseed --no-flush --per-model 3 --model communications.Location
# or by db table name
python manage.py reseed --no-flush --per-model 3 --table locations
```

Relationship building and `seed_relationships` run automatically for both `reseed --full` and targeted reseeds.

- `sync.Connection`: name=`alert`, type=`safety_alert`, purpose=`webclerk.com`, status=`safe`.
- Used to signal assaults/incidents to webclerk.com for verification and coordinated communication.

Smoke test:

```bash
python manage.py test_alert_connection --event assault_detected --severity warning
```


---

End of reset guide.



