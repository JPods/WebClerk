# UUID population and reconciliation (admin)

This management command lets admins safely populate or overwrite `uuid` fields across any model that has one. By default it fills only rows where `uuid IS NULL` using random UUIDv4; you can optionally use deterministic UUIDv5 derived from a namespace and key, and you can overwrite existing UUIDs with strict guardrails.

## Why

- Keep UUIDs externally controlled (or empty) by default
- Backfill legacy rows with a consistent strategy when needed
- Deterministically align UUIDs across environments/vendors using UUIDv5
- Produce an audit log of every change

## Usage

- Preview (no writes): add `--dry-run`
- Confirmation: all non-dry runs require `--yes`
- Overwrite safety: global overwrites require `--allow-overwrite-all`

### Examples

- Fill null UUIDs with v4 for active items (preview):

```
python manage.py populate_uuids \
  --model products.Item \
  --filter 'is_active=True' \
  --limit 100 \
  --dry-run
```

- Deterministic v5 using DNS namespace and `sku` field as key:

```
python manage.py populate_uuids \
  --model products.Item \
  --strategy v5 \
  --namespace dns \
  --key-field sku \
  --yes
```

- Deterministic v5 with a composite key template:

```
python manage.py populate_uuids \
  --model transactions.Invoice \
  --strategy v5 \
  --namespace 6ba7b810-9dad-11d1-80b4-00c04fd430c8 \
  --key-template '{org_id}:{external_id}:{id}' \
  --filter 'status=PAID' \
  --yes
```

- Overwrite existing UUIDs for a filtered subset only:

```
python manage.py populate_uuids \
  --model transactions.Proposal \
  --filter 'status=OPEN' \
  --overwrite \
  --yes
```

- Global overwrite (dangerous: requires explicit allow):

```
python manage.py populate_uuids \
  --model core.Contact \
  --overwrite \
  --allow-overwrite-all \
  --yes
```

### Raw SQL predicate with `--where-sql`

You can further constrain the selection with a raw SQL `WHERE` clause. This is applied by selecting matching primary keys via SQL and AND-ing with the ORM filters.

- Example:

```
python manage.py populate_uuids \
  --model transactions.Invoice \
  --where-sql "status IN ('OPEN','HOLD') AND total > 0" \
  --limit 500 \
  --dry-run
```

Notes:
- The `--where-sql` string is interpolated directly into a `SELECT pk FROM <table> WHERE <where-sql>`; ensure it is safe and vetted.
- If `--limit` is used alongside `--where-sql`, the limit is applied in SQL during PK selection; we avoid double-limiting later.

## Audit log (NDJSON)

Every non-dry run writes an audit trail line for the run and for each row updated.

- Default location: `local/audit/populate_uuids/<model>_<timestamp>.ndjson`
- Override with: `--audit-file /path/to/file.ndjson`

Each line is a JSON object:
- Run header: `{ "type": "run", "run_id": "…", "ts": "…", "model": "…", "mode": "fill-null|overwrite", "strategy": "v4|v5", … }`
- Row change: `{ "type": "row", "run_id": "…", "pk": 123, "old_uuid": "…", "new_uuid": "…", "strategy": "…", "namespace": "…", "key": "…", "overwrite": true }`

Use standard tooling to analyze:
- Count rows: `jq 'select(.type=="row")' -c file.ndjson | wc -l`
- List pks: `jq -r 'select(.type=="row") | .pk' file.ndjson`

## Options reference

- `--model` app_label.ModelName (required)
- `--filter` Django ORM filters as `key=value` pairs, comma-separated
- `--where-sql` raw SQL WHERE predicate to preselect pk values
- `--ids` comma-separated pk list
- `--limit` max rows
- `--dry-run` preview changes
- `--commit-chunk` bulk update chunk size (default 500)
- `--strategy` v4 (default) or v5
- `--namespace` v5 namespace: dns|url|oid|x500 or UUID
- `--key-field` model field to use as v5 key
- `--key-template` Python format template, e.g. `{org_id}:{external_id}:{id}`
- `--overwrite` also update rows that already have a uuid
- `--yes` required to execute writes
- `--allow-overwrite-all` required for global overwrite without filters
- `--sample` number of example pks to show before executing (default 10)
- `--audit-file` where to write NDJSON audit log

## Safety and best practices

- Prefer `--dry-run` first and inspect sample IDs
- Use `--filter`/`--ids`/`--limit` to scope updates
- For v5, choose a stable namespace and key that are immutable for the entity
- Store audit logs in versioned storage if possible
- If using `--where-sql`, review the predicate; it is executed as-is
