# Schema iteration workflow (temporary, September 2025)


<!-- TOC START -->

## Table of Contents

- [Schema iteration workflow (temporary, September 2025)](#schema-iteration-workflow-temporary-september-2025)
  - [Table of Contents](#table-of-contents)
  - [Daily flow](#daily-flow)
  - [Commands](#commands)
- [Rebaseline (drop DB, migrate, create admin)](#rebaseline-drop-db-migrate-create-admin)
- [Keep DB, just migrate](#keep-db-just-migrate)
- [Skip admin creation](#skip-admin-creation)
  - [CI](#ci)
  - [Exit plan](#exit-plan)

<!-- TOC END -->

Goal: move fast on model changes without fighting migrations. We keep one 0001_initial.py per app during this spike and rebaseline local DBs as needed.

## Daily flow

1. Edit models freely (prefer JSONField for evolving shapes). Avoid circular cross-app FKs; use string refs or temporary IDs if needed.
2. Keep a single 0001 per app:
   - If you change models in an app, regenerate that app's 0001.
   - Do not add 0002+ during this period.
3. Rebaseline your DB:
   - Use Scripts/rebaseline.sh (drops DB, migrates, creates admin).
   - Seed optional demo data when we stabilize (disabled by default here).
4. Verify quickly:
   - pytest -m fast
   - python manage.py check
5. Commit & push:
   - Commit model changes together with the regenerated 0001s.
   - Push to the shared branch and teammates rebaseline.

## Commands

Optional commands (from repo root):

```bash
# Rebaseline (drop DB, migrate, create admin)
Scripts/rebaseline.sh

# Keep DB, just migrate
Scripts/rebaseline.sh --no-drop

# Skip admin creation
Scripts/rebaseline.sh --no-seed
```

Requires a local Postgres server. Env vars honored: DATABASE_NAME, DATABASE_USER, DATABASE_HOST, DATABASE_PORT, DATABASE_PASS.

## CI

- Auto CI triggers are paused. Run manual smoke if you need a fresh validation; CI will create a clean DB and run a fast subset.
- When we freeze schema, we’ll re-enable normal incremental migrations and CI.

## Exit plan

When model churn slows:

1) Ensure each app’s 0001 matches models.
2) Re-enable CI triggers.
3) From then on, add incremental migrations (0002, 0003, …) as usual.
