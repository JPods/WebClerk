<!-- Migrated from README_STATS.md (deleted at root). -->

# Stats & Relationship Stats Architecture

Lightweight in-row statistics facilities provided by `StatsMixin` / `RelationshipStatsMixin` plus supporting Celery tasks.

## Goals

- Fast access to small, frequently referenced metrics without analytical round-trips.
- Keep structures *bounded*; high-volume / historical data lives elsewhere.
- Provide generic helpers (`record_transaction`, `record_service_call`, `inc_stat`, etc.).
- Allow periodic normalization tasks to repair / populate structures.

## StatsMixin Structure

Field: `stats` (JSON)

```json
{
  "counts": { "tx_sale_count": 10, "service_calls": 3 },
  "values": { "tx_sale_total_value": 1234.50, "avg_margin_pct": 0.32 },
  "series": { "weekly_sales": [{"dt": 1693449600000, "v": 10}] },
  "last": { "dt_last_sale": 1698790000000, "dt_last_service_call": 1698791111111 }
}
```

Helpers: `inc_stat`, `set_value`, `push_series`, `record_transaction`, `record_service_call`.

## RelationshipStatsMixin

Field: `relationship_stats` (JSON)

```json
{
  "counts": { "customers": 42, "vendors": 5, "parents": 1, "children": 3 },
  "last_dt": { "customers": 1698789000000 }
}
```

Helpers: `set_relation_count`, `bulk_set_relation_counts`, `inc_relation`, `get_relation_count`, `top_relations`.

## Celery Tasks

- `common.tasks.recompute_relationship_counts` – derive simple relation counts.
- `common.tasks.recompute_basic_stats` – ensure containers exist; future derived rebuilds.

## Usage Examples

```python
item.record_transaction('sale', value=125.50, margin_value=0.30)
item.record_service_call(); item.save(update_fields=['stats'])
org.inc_relation('customers'); org.save(update_fields=['relationship_stats'])
```

## Offload Guidance

If a series grows unbounded, move historical points to a time-series table; keep last N (e.g. 50) samples inline.

## Extension Ideas

- Pluggable calculator registry.
- Partial indexes on JSON paths if query patterns emerge.
- Shallow stats update endpoints to avoid large payload PATCH.

## Caveats

- Batch writes; use `update_fields` to limit row write amplification.
- Stats are advisory; don't drive authoritative accounting from them.

## Periodic Schedule

See `settings.CELERY_BEAT_SCHEDULE` for cadences (hourly, 2h, 30m tasks).

## Backwards Compatibility

`atomic_append` instance alias retained for older code; new code should use `atomic_list_append` / `atomic_set`.

---

Keep lean; expand only when patterns justify.
