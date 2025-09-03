# Upgrade / Schema Change Guide

## Post-Squash Baseline

As of 2025-09-03, `orgs` and `products` migrations were squashed. Treat current `0001_initial` as the authoritative baseline.

## Adding Fields

1. Add the field to the model.
2. Run `python manage.py makemigrations <app>`.
3. Inspect the migration for unintended alterations.
4. Run `pytest -q` to ensure no regressions.

## Removing / Renaming Fields

- Prefer two-step approach (add new field, migrate data, drop old) unless trivial.
- Use `RunPython` for data migrations; keep them idempotent where feasible.

## When To Squash Again

Only before a tagged release or major refactor, after confirming all environments can reset or fake forward. Document rationale in `MIGRATIONS_SQUASH.md`.

## Data Migrations Tips

- Guard with `apps.get_model` to avoid import-time model state drift.
- Keep operations small; chain multiple `RunPython` blocks if needed.

## Testing Strategy

- Always test on a fresh DB after structural changes: drop, migrate, run key suites.
- Validate indexes/constraints exist (Django migration graph should reflect them).

## Rollback Considerations

Django permits reversing most schema ops; complex JSON/data transforms may need explicit reverse code (or set `reverse_code=migrations.RunPython.noop`).

## Gotchas

| Scenario | Issue | Mitigation |
|----------|-------|------------|
| Editing past migration | Divergent graphs | Create new migration instead |
| DuplicateColumn errors | Legacy non-noop intermediate files | Ensure only squashed + no-op stubs remain |
| Large data migration slow | Table scans | Batch with primary key ranges |

## Contact

Add upgrade notes here as conventions evolve.
