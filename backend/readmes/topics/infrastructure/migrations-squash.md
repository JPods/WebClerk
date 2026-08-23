# Migration Squash (September 2025)


<!-- TOC START -->

## Table of Contents

- [Migration Squash (September 2025)](#migration-squash-september-2025)
  - [Table of Contents](#table-of-contents)
  - [Strategy](#strategy)
  - [Operational Notes](#operational-notes)
  - [Caution](#caution)
  - [Next Steps](#next-steps)
  - [Baseline (2025-09-03)](#baseline-2025-09-03)
    - [What Changed](#what-changed)
    - [Fresh Clone / Environment Reset](#fresh-clone-environment-reset)
    - [Existing Developer Instances](#existing-developer-instances)
    - [Rationale](#rationale)
    - [Policy Going Forward](#policy-going-forward)
    - [Verifications Performed](#verifications-performed)
    - [Troubleshooting](#troubleshooting)
    - [Contact](#contact)

<!-- TOC END -->

We introduced substantial model refactors across `orgs`, `products`, and `transactions` (catalog roles, OrgItem metrics & scheduling, delivery & inventory workflow models, metrics JSON envelopes, constraints). The legacy migration history had empty placeholder files and inconsistent application order, producing `InconsistentMigrationHistory` and conflicting leaf nodes.

## Strategy

- Added `MIGRATION_MODULES` override in `settings.py` pointing the three apps to `squashed_migrations` packages.
- Generated fresh `0001_initial` migrations for each target app under the new module paths using SQLite for speed.
- Left legacy migration files in place but replaced contents with inert stubs (no operations) so the filesystem diff is minimal while Django ignores them.
- Other apps (core, sync, communications, etc.) retain their original migrations.

## Operational Notes

- SQLite (`USE_SQLITE_TEST=1`) is the active dev path for rapid iteration. Postgres re‑enable later by removing the env flag (and ensuring DB exists) before sharing or deploying.
- Data in current phase is disposable; baseline can be regenerated freely until stabilization.
- When ready to finalize, you MAY: (a) delete the stubbed legacy files, (b) keep `MIGRATION_MODULES` permanently, or (c) copy the squashed migrations back into the default `migrations` directories and remove the override.

## Caution

If any teammate still has an old DB with the legacy chain applied, they must drop and recreate their database (or flush + fake-initial) before pulling this branch.

## Next Steps

- Continue model iteration normally; new migrations will append to the squashed baseline.
- Prior to production stabilization, decide whether to collapse back to default migration module paths.

## Baseline (2025-09-03)

This project intentionally squashed historical migrations for a cleaner onboarding and faster test/db setup.

### What Changed

Apps impacted:

- `orgs`: Legacy migrations collapsed into `0001_initial` with final `OrgBase` schema (connections JSON replaces older access constructs, stats + relationship_stats present).
- `products`: Former chain `0001`-`0006` merged into a single authoritative `0001_initial` capturing all current models and fields (Item `qr_code`, `base_uom`, BillOfMaterial extended fields, Serial unified on `serial_ida` with `model_ida`, `warranty`, `data`, `qr_code`, plus OrgItem (renamed from ItemCarried) uniqueness, JSON price/cost factories, all indexes & constraints).

Intermediate migrations (`0002`–`0006` in products) were converted to explicit no-op stubs (empty `operations = []`) to satisfy any stale dependency references during local dev without applying duplicate DDL.

### Fresh Clone / Environment Reset

```bash
psql -c 'DROP DATABASE IF EXISTS commerce_expert;' -d postgres
psql -c 'CREATE DATABASE commerce_expert;' -d postgres
find apps -path '*/migrations/*.pyc' -delete
python manage.py migrate
python create_superuser.py
pytest -q
```

### Existing Developer Instances

If you previously had the old migrations applied:

1. Dump any data you need to preserve (if any). This squash expects a reset.
2. Drop and recreate the database (see commands above) OR use `manage.py flush` if you only had test data.
3. Ensure no legacy migration files remain uncommitted locally.
4. Re-run migrations; only `0001_initial` per app should apply.

### Rationale

- Reduced migration graph complexity lowers cognitive load for new contributors.
- Eliminated duplicate column errors stemming from layered experimental migrations.
- Aligns migration history tightly with actual model definitions at squash date.

### Policy Going Forward

- Favor small, reviewable migrations but avoid excessive churn.
- When large refactors accumulate, consider another squash only before a tagged release and after team consensus.
- Never edit a past committed migration except during an intentional, coordinated squash like this.

### Verifications Performed

- BOM extended fields present directly in `0001_initial`; no subsequent AddField attempts.
- Serial only defined once with `serial_ida` (no legacy `serial_number`).
- Tests pass on a clean DB after squash fix.

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| DuplicateColumn on BillOfMaterial.* | Old non-noop 0002+ migrations still present | Git clean/reset, ensure no-op stubs, drop DB, migrate |
| serial_number column missing | Code expecting old name | Update code; schema now uses serial_ida |
| Migration order errors | Local stray migration file edits | Revert or sync with main branch |

### Contact

Add notes or adjustments here if further schema consolidation occurs.
