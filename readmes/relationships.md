# Relationships & Link Strategy


<!-- TOC START -->

## Table of Contents

- [Relationships & Link Strategy](#relationships-link-strategy)
  - [Table of Contents](#table-of-contents)
  - [Core Principles](#core-principles)
  - [Data Model Summary](#data-model-summary)
  - [Lifecycle of a Link](#lifecycle-of-a-link)
  - [Commands](#commands)
    - [reconcile_links](#reconcilelinks)
    - [Operational Guidance](#operational-guidance)
  - [Celery Strategy](#celery-strategy)
  - [Error Handling](#error-handling)
  - [Future Enhancements](#future-enhancements)
    - [Party Role Address/Contact Strategy (BillTo / ShipTo / SellTo / BuyFrom)](#party-role-addresscontact-strategy-billto-shipto-sellto-buyfrom)
  - [Rationale vs Join Tables](#rationale-vs-join-tables)
  - [Soft Limits](#soft-limits)
  - [Testing Notes](#testing-notes)

<!-- TOC END -->

Date: 2025-09-03
Review: 2025-12-15
Status: Draft (living design)
Owner: Bill

## Core Principles

1. Authoritative Source: **Contact refs** are the source of truth for lightweight cross-entity relationships.
2. Storage Shape: All links live under `refs.links.<table_name>[]` (arrays of integer primary keys).
3. Reciprocal Convenience: Communication & other target records (emails, phones, locations, domains, etc.) may also store `refs.links.contacts[]` as a **derived cache** to accelerate reverse lookups and related fetches.
4. API Semantics: `GET /wcapi/get/?table_name=<name>` returns a flat list (no `related`); `GET /wcapi/get/?table_name=<name>&id=<id>` returns a single record and MAY include `related` (resolved using contact authoritative refs + reciprocal cache when present).
5. Expandability: New link buckets are added by extending `STANDARD_LINK_KEYS` and (optionally) running a reconcile task.
6. Non-blocking Integrity: Missing reciprocal links should not 500 the API; integrity is restored asynchronously.

## Data Model Summary

```json
refs: {
  "links": {
    "contacts": [/* ids */],
    "emails": [/* ids */],
    "phones": [/* ids */],
    "locations": [/* ids */],
    "domains": [/* ids */],
    "orgs": [/* ids */],
    "orders": [/* ids */],
    "projects": [/* ids */],
    "documents": [/* ids */]
  },
  "keywords": [],
  "tags": [],
  "related_ids": []
}
```

## Lifecycle of a Link

1. Creation (seeding or user action) adds IDs into a contact's `refs.links.<bucket>` arrays.
2. Periodic reconcile (or immediate seed enrichment) ensures reciprocal objects contain the contact id in their `refs.links.contacts` list.
3. Reads use forward links (authoritative) + opportunistic reciprocal confirmation.
4. Cleanup tasks prune orphan reciprocal entries (contact removed or link dropped) – contacts remain authoritative.

## Commands

| Command | Purpose |
|---------|---------|
| `seed_relationships` | Randomized dev data linking (forward + reciprocal at seed time) |
| `reconcile_links` | Backfill / repair reciprocal links from authoritative contact refs (optional prune) |

### reconcile_links

```bash
python manage.py reconcile_links --batch 500 --limit 0 --prune --dry-run
```

Arguments:

- `--batch` chunk size (default 500)
- `--limit` max contacts processed (0 = all)
- `--prune` remove reciprocal contact IDs no longer referenced forward
- `--dry-run` report only

### Operational Guidance

- Run `reconcile_links` after large imports or schema resets.
- Schedule a Celery task (future) nightly with `--prune` for hygiene.
- Accept minor temporary drift; API stays functional.

## Celery Strategy

Planned tasks:

- `links.reconcile` (wraps management command logic for scheduling)
- `links.audit` (sample integrity check; logs discrepancy rates)
- Escalation path: If audit finds >X% missing reciprocal links, enqueue a full reconcile with prune.

## Error Handling

- Missing target row during reconcile => ignored (counts as implicit prune later).
- Invalid refs shape (non-dict/list) => reinitialized via `ensure_standard_links` (non-destructive to other keys).

## Future Enhancements

- Add `invoices`, `purchases`, `workorders` buckets once tables integrated.
- Optional cardinality caps (warn when > N link entries per bucket).
- Partial materialized reverse index (Postgres GIN on refs JSON) for faster `contains` queries.
- Versioned link diffs for audit / sync scenarios.

### Party Role Address/Contact Strategy (BillTo / ShipTo / SellTo / BuyFrom)

Many customer/manufacturer/rep/vendor interactions need lightweight party role blocks (bill-to, ship-to, sell-to, buy-from) mainly for document rendering (forms, PDFs) rather than active relational querying. To keep runtime cost low and avoid premature join complexity:

Recommended approach (initial):

1. Denormalize frequently printed fields into small string / scalar snapshots under `refs.party_roles` (or `refs.billto.*` style if flatter) – e.g.:

```json
"refs": {
  "party_roles": {
    "billto": {"name": "Acme Corp", "addr1": "123 Main", "city": "Austin", "state": "TX"},
    "shipto": {"name": "Acme Warehouse", "addr1": "500 Dock", "city": "Dallas", "state": "TX"}
  }
}
```

1. Optionally store originating entity IDs (contact/org/location) inside each role snapshot (`source_ids`: {"org": 17, "location": 55}).
1. When richer linkage or updates are needed, use forward contact/org `refs.links` buckets (e.g., org holds authoritative contact relationships; role snapshot just caches printable text).
1. Rebuild / refresh command can materialize these snapshots from canonical org/contact/location JSON if they drift.
1. Only introduce dedicated join tables if: a) role-specific querying emerges (e.g., filter orders by ship-to city), or b) snapshots exceed acceptable size or mutation frequency.

Rationale: Denormalized snapshots avoid extra joins for the 90% read/print path while preserving a migration-free evolution path during early iteration. Forward links remain canonical for entity graph traversal; role snapshots are ephemeral caches.

## Rationale vs Join Tables

| Aspect | JSON Links | Join Table |
|--------|-----------|------------|
| Dev Speed | Fast (no migrations for new buckets) | Heavier (migrations, models) |
| Query Simplicity | Simple id array access | Requires joins or subselects |
| Integrity | Needs reconcile job | Enforced via FK |
| Scale | Fine for moderate link counts | Better for very high fan-out |

Decision: JSON approach acceptable for early product iteration; revisit if any bucket routinely exceeds soft thresholds or complex filtering on link attributes emerges.

## Soft Limits

- Monitor typical counts; when a bucket > ~200 consistently, consider normalization or pagination inside refs.

## Testing Notes

- Unit test seeds should assert that after `reconcile_links --dry-run` report shows `comm_updates=0` for a freshly reconciled dataset.
- Edge test: Orphan a reciprocal reference manually → reconcile with `--prune` removes it.

---
This document is a living spec; update alongside any schema or process change affecting relationship governance.
