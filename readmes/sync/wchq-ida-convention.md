# WCHQ Sync Convention — ida Prefix

**Established:** 2026-08-08

## The Rule

Records from WCHQ (WebClerk Headquarters) are identified by the `ida` prefix: **`wchq-*`**

No new fields. No migrations. `ida` is already on every BaseModel record, already indexed.

## Why ida, Not a New Field

Before adding a field, check if an existing field with a convention can do the job.
A named convention on an indexed field beats a new boolean — it carries meaning, not
just state. `wchq-schema-customer` tells you what it is AND where it came from.
`is_wchq = True` tells you nothing about what.

## Prefix Patterns

| Pattern | What | Example |
|---------|------|---------|
| `wchq-schema-{model}` | Schema map Settings | `wchq-schema-customer` |
| `wchq-conn-upstream` | The WCHQ Connection record | single record |
| `wchq-rpt-{name}` | Report templates from WCHQ | `wchq-rpt-pick-list-md` |
| `wchq-coaching-{model}` | Alice coaching tips from WCHQ | `wchq-coaching-contact` |
| `wchq-fa-{model}` | Field access Settings from WCHQ | `wchq-fa-order` |

## Querying

```sql
-- Any table
SELECT * FROM settings WHERE ida LIKE 'wchq-%';

-- wcapi
GET /wcapi/get/?model_name=setting&ida__startswith=wchq-

-- Django
Setting.objects.filter(ida__startswith='wchq-')
```

## Sync Cycle

Alice checks `wchq-*` records against upstream `dt_modified`:

1. If upstream is newer → pull update
2. If local is newer (user customized) → flag for review
3. If local-only (no `wchq-` prefix) → never synced

Company profile Setting controls sync level:

```
wchq_level: none | receive_only | send_only | full
```

## Local Records

Records without `wchq-` prefix are local. Never synced upstream.

| ida | What | Source |
|-----|------|--------|
| `company-profile` | Local company settings | Local |
| `conn-alice-claude` | Agent connection | Local |
| `HELP-SEARCH` | Help document | Local |

## Promotion Path

Local → WCHQ:

1. User creates a report, setting, or layout locally
2. User submits it for sharing (via Connection sync)
3. WCHQ reviews
4. WCHQ assigns `wchq-` ida
5. WCHQ distributes to all sites

This is the Wisdom of the Many loop. Contributions flow up, vetted
improvements flow down. No central authority decides what's good —
usage and adoption metrics do.

## Seed Commands

These commands create records with `wchq-*` idas:

| Command | ida Pattern |
|---------|-------------|
| `seed_model_definitions` | `wchq-schema-{model}` |
| `seed_connections` | `wchq-conn-upstream` |
| `seed_template_reports` | `wchq-rpt-{name}` |

## Implementation Notes

- `ida` is `CharField(max_length=40, db_index=True)` on CoreModel
- PostgreSQL B-tree index supports left-anchored `LIKE 'wchq-%'` efficiently
- No partial index needed unless table exceeds ~1M rows
- Seed scripts use `get_or_create` with `ida` — idempotent
