# Stats & Relationship Stats Architecture

This document explains the lightweight statistics facilities provided by `StatsMixin` and `RelationshipStatsMixin` plus the supporting Celery tasks.

## Goals

- Fast in-row access to small, frequently referenced metrics (counts, last timestamps, running averages) without round-trips to analytical stores.
- Keep structures *bounded* and simple; anything high‑volume or historical belongs in a warehouse / fact tables.
- Provide generic helpers (`record_transaction`, `record_service_call`, `inc_stat`, etc.) to standardize metric updates.
- Allow periodic normalization / recomputation tasks to repair / populate structures without manual intervention.

## StatsMixin

Field: `stats` (JSON)

Structure:

```json
{
  "counts": { "tx_sale_count": 10, "service_calls": 3 },
  "values": { "tx_sale_total_value": 1234.50, "avg_margin_pct": 0.32 },
  "series": { "weekly_sales": [{"dt": 1693449600000, "v": 10}] },
  "last": { "dt_last_sale": 1698790000000, "dt_last_service_call": 1698791111111 }
}
```

Reserved keys (suggested; optional):

- counts: `tx_total`, `tx_sale_count`, `tx_purchase_count`, `tx_return_count`, `tx_adjust_count`, `service_calls`
- values: `tx_sale_total_value`, `tx_purchase_total_value`, `tx_return_total_value`, `avg_margin_pct`, `last_margin_pct`, `last_sale_value`
- last: `dt_last_sale`, `dt_last_purchase`, `dt_last_return`, `dt_last_service_call`

Helper methods:

- `inc_stat(key, delta=1)` – increment an arbitrary counter.
- `set_value(key, value)` – set a scalar value.
- `push_series(key, value, max_len=50)` – append a time/value sample with automatic capping.
- `record_transaction(tx_type, value=None, margin_value=None)` – unified transaction update (counts, totals, margin averages, last timestamps).
- `record_service_call()` – increment service call count & last timestamp.

## RelationshipStatsMixin

Field: `relationship_stats` (JSON)

Structure:

```json
{
  "counts": { "customers": 42, "vendors": 5, "parents": 1, "children": 3 },
  "last_dt": { "customers": 1698789000000 }
}
```

Helper methods:

- `set_relation_count(type, count, dt_ms=None)`
- `bulk_set_relation_counts(mapping, dt_ms=None)`
- `inc_relation(type, delta=1, dt_ms=None)`
- `get_relation_count(type)` / `top_relations(limit=5)`

## Celery Tasks

`common.tasks.recompute_relationship_counts`

- Scans models with `RelationshipStatsMixin` (e.g., `OrgBase`)
- Derives simple counts from `relations` JSON (parents / children / linked_ids)
- Updates only when counts change.

`common.tasks.recompute_basic_stats`

- Scans `StatsMixin` subclasses.
- Ensures required containers exist; placeholder for future derived recomputations (e.g., rebuild running averages from authoritative transaction lines table).

## Usage Examples

```python
item.record_transaction('sale', value=125.50, margin_value=0.30)
item.record_service_call()  # if item-level service events exist
item.save(update_fields=['stats'])

org.inc_relation('customers')
org.set_relation_count('vendors', 5)
org.save(update_fields=['relationship_stats'])
```

## When to Offload

If any series approaches unbounded growth, move historical points to a separate time-series table and keep only a small trailing window (e.g., last 50 samples) in `series` for UI quick display.

## Extension Ideas

- Add pluggable calculator registry so `recompute_basic_stats` can invoke domain-specific rebuild functions.
- Introduce partial indexes on JSON paths if query patterns emerge (e.g., `stats->'counts'->>'tx_sale_count'::int > 0`).
- Add API endpoints for shallow stats updates to avoid large object payloads on every PATCH.

## Caveats

- Avoid writing stats inside hot loops one row at a time; batch and use `update_fields` to minimize contention.
- Stats are *advisory* and may lag real transactional data; do not drive critical accounting logic from them.

---

This design keeps core models lean while offering a consistent place to surface lightweight metrics for UI and quick filtering.

## Scheduled Execution (Celery Beat)

The following periodic tasks are configured in `settings.py` (using `CELERY_BEAT_SCHEDULE`):

- `recompute-basic-stats-hourly` – hourly normalization of `stats` blobs.
- `recompute-relationship-counts-2h` – every 2 hours, refresh denormalized relationship counts.
- `refresh-keywords-30m` – keyword refresh sweep every 30 minutes (task self-limits work each run).

Adjust cadences as operational load clarifies (e.g., move to 15m for keywords if UI freshness demands it).

## Backwards Compatibility Note

Legacy code (and older tests) referenced an instance method `atomic_append`. The canonical name is now
`atomic_list_append` (classmethod) with an instance convenience alias `atomic_append` retained for compatibility.
New code should prefer `atomic_list_append` / `atomic_set` patterns; the alias may be removed in a future major revision.
