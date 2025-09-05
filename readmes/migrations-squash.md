# Migration Squash (September 2025)


<!-- TOC START -->

## Table of Contents

- [Migration Squash (September 2025)](#migration-squash-september-2025)
  - [Table of Contents](#table-of-contents)
  - [Strategy](#strategy)
  - [Operational Notes](#operational-notes)
  - [Caution](#caution)
  - [Next Steps](#next-steps)

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
