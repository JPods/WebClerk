<!-- Migrated from README_RESET.md (deleted at root). -->

# Full Reset & Migration Baseline

This project supports a **full destructive local reset** to simplify development when migrations drift or demo data needs refreshing.

## When To Use

- Local schema churn made historical migrations noisy.
- You intentionally reset migration history (never do this on a shared/staging/prod DB).
- You want a clean dataset identical to `rebuild_demo_data` export snapshot.

## What It Does

`scripts/full_reset_and_rebuild.sh` will:

1. Confirm (or auto-confirm with `-y`).
2. Terminate active DB connections.
3. Drop & recreate the target database (`$DATABASE_NAME` or default `commerce_expert`).
4. Delete all migration files for domain apps (defined in the script).
5. Run `makemigrations` to produce a single `0001_initial.py` per app.
6. Apply migrations.
7. Attempt superuser creation (skipped in non‑TTY).
8. Load default company & access (non-fatal if JSON absent).
9. Run `rebuild_demo_data --export-after` to seed and snapshot.

## Safety Guards

- Refuses to run if `DJANGO_SETTINGS_MODULE` contains `prod`.
- Requires `DEBUG=1` (default) OR explicit `FORCE_FULL_RESET=1` override.
- Interactive yes/no unless `-y` used (or running under CI sets auto-confirm).

## Usage

```bash
./scripts/full_reset_and_rebuild.sh        # interactive
./scripts/full_reset_and_rebuild.sh -y     # no prompt
FORCE_FULL_RESET=1 DEBUG=0 ./scripts/full_reset_and_rebuild.sh -y  # explicit outside DEBUG
```

## Post-Reset

- Run tests: `./bin/python -m pytest -q`.
- Optionally create a superuser: `./bin/python manage.py createsuperuser`.

## Version Control Strategy

- We committed the new `0001_initial.py` per app as the fresh baseline.
- Old multi-step migrations were removed; consumers must drop & recreate local DBs after pulling.
- Coordinate with teammates before merging this baseline.

## Export Snapshot

`common/management/commands/all_tables_export.json` is produced by the rebuild step. It is ignored by default (see `.gitignore`); remove that line if you wish to track snapshot evolution.

## Caveats

- Never run against production data.
- If you later add apps, update the `APPS` array in the script.
- If default JSON seeds become required, ensure they are added to repo to avoid warning noise.

---

_This document was migrated into `docs/` on 2025‑09‑02._
