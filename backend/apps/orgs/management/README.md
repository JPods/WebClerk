# Org Management Command Registry

This registry tracks permanent org maintenance commands so critical operations remain discoverable and are not lost during iterative development.

## Command Catalog

### org_financial_maintenance
- File: `apps/orgs/management/commands/org_financial_maintenance.py`
- Service: `apps/orgs/services/financial_maintenance.py`
- Purpose:
  - One-time financial population/backfill for existing org records
  - Recurring financial scrub/reconciliation pass
  - Processing queued pending updates created when org records are locked
  - Daily integrity run with Alice observation log output
- Modes:
  - `--mode populate`
  - `--mode scrub`
  - `--mode process_pending`
  - `--mode daily`

### migrate_financial_structure
- File: `apps/orgs/management/commands/migrate_financial_structure.py`
- Purpose: Migrate legacy flat financial JSON payloads into current type-keyed structure.

### fix_null_mixin_values
- File: `apps/orgs/management/commands/fix_null_mixin_values.py`
- Purpose: Normalize null numeric leaves to `0` in org JSON fields (`financial`, `stats`, etc.).

### populate_org_contacts
- File: `apps/orgs/management/commands/populate_org_contacts.py`
- Purpose: Backfill contacts payloads for org records.

### customer_transaction_maintenance
- File: `apps/orgs/management/commands/customer_transaction_maintenance.py`
- Service: `apps/orgs/services/customer_transaction_maintenance.py`
- Purpose:
  - Reconcile customer linkage between transaction `customer_id` and refs links.
  - Optionally assign missing transaction `customer_id` randomly from configured customer ids.
  - Keep `transaction.refs.links.customer` and `customer.refs.links.<transaction_model>` connected.
- Defaults:
  - Assigns missing customer ids from `82 84 86` unless overridden by `--target-customers`.

## Operational Standard

- Treat listed commands as permanent maintenance interfaces.
- Prefer adding new org maintenance capabilities as:
  1. Reusable service function in `apps/orgs/services/`
  2. Option/mode in an existing permanent command (or add a new command if needed)
  3. Entry in this registry with purpose and usage notes
- Keep command behavior idempotent whenever practical.
- Include `--dry-run` for any new command that mutates many records.

## Recommended Cadence

- One-time after deploy/migration:
  - `python manage.py org_financial_maintenance --mode populate`
- Scheduled recurring scrub:
  - `python manage.py org_financial_maintenance --mode scrub`
- Scheduled pending drain:
  - `python manage.py org_financial_maintenance --mode process_pending --limit 500`
- Daily full audit + observation log:
  - `python manage.py org_financial_maintenance --mode daily --activity-hours 24`

## Daily Observation Record

`--mode daily` writes an `alice_log` (`role=health_check`) record containing:
- Receivables aging refresh counts (`customer` + `vendor` updates)
- Recent transaction activity summary (default last 24 hours)
- Pending processing result counts
- Unusual conditions requiring attention:
  - locked queued/skipped orgs
  - scrub errors
  - pending errors/missing-org conditions

Console output also includes lightweight badges so users can triage quickly:
- `ACTIVITY[LOW|MEDIUM|HIGH|VERY_HIGH]`
- `STATUS[OK|WATCH|ATTENTION|CRITICAL]`

The badges are one-line indicators and are designed to stay lightweight so they do not interfere with normal operational actions.

## Examples

```bash
# One org dry-run
python manage.py org_financial_maintenance --mode scrub --org-id 42 --dry-run

# Process all orgs and queue locked records for later
python manage.py org_financial_maintenance --mode scrub

# Skip queueing and just report locked as skipped
python manage.py org_financial_maintenance --mode scrub --no-queue-locked

# Drain queued locked updates
python manage.py org_financial_maintenance --mode process_pending --limit 1000

# Daily run + Alice observation log
python manage.py org_financial_maintenance --mode daily --activity-hours 24

# Daily run without writing Alice observation
python manage.py org_financial_maintenance --mode daily --no-alice-log
```
