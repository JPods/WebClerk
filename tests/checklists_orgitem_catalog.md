# OrgItem & Catalog Data Review Checklist

Purpose: Enable domain experts to review real (not seeded-only) data for defects in handling catalog + org item logic.

## Preparation

1. Load a representative dataset (import, ETL, or real extract) into a dev environment (SQLite acceptable for structure; Postgres preferred for JSONB perf if available).
2. Run: `USE_SQLITE_TEST=1 python manage.py seed_sample_products` (optional) to confirm baseline objects create successfully (does NOT replace your real data).

## Catalog Checks

- [ ] Each active catalog has non-null `effective_dt_start` and (when present) `effective_dt_end >= start`.  
	Rationale: Prevents invalid temporal ranges that could exclude items from pricing or availability windows.
- [ ] Codes unique per vendor (no duplicate `(code, vendor_org)` pairs).  
	Rationale: Uniqueness simplifies integration lookups and avoids ambiguous price or mapping collisions.
- [ ] `metrics.item_count` matches actual count of `CatalogLine` rows for that catalog.  
	Rationale: Detects stale or failed denormalized metric refresh jobs.
- [ ] `metrics.active_item_count` <= `metrics.item_count` and equals count of active catalog lines (if line flag exists).  
	Rationale: Ensures active subset is not inflated, which would distort availability / fulfillment KPIs.
- [ ] For any catalog with pricing changes just made, `metrics.dt_last_priced` updated (epoch ms reasonable—within last hour if recent change).  
	Rationale: Validates pricing mutation hooks correctly touch metrics for downstream analytics.
- [ ] When an external sync job ran recently, `metrics.dt_last_sync` reflects that (optional integration).  
	Rationale: Confirms sync instrumentation is writing heartbeat timestamps.

## OrgItem Checks

- [ ] No OrgItem has `quantity_minimum > quantity_maximum`.  
	Rationale: Guards against inverted thresholds that would invalidate replenishment logic.
- [ ] Thresholds (if both present) are reasonable (e.g., max not 1000x min unless bulk item).  
	Rationale: Flags data-entry or import anomalies skewing reorder or planning models.
- [ ] `availability_state` only in {enabled, paused, retired}.  
	Rationale: Prevents silent introduction of undocumented states that UI / API logic may not handle.
- [ ] `dt_next_check` populated for items with `inventory_frequency` set; null otherwise.  
	Rationale: Ensures scheduling compute hook is firing (prevents inventory verification drift).
- [ ] For items past their `dt_next_check` by > expected frequency interval, confirm process flagged or queued for re-check.  
	Rationale: Validates monitoring & job orchestration path.
- [ ] `metrics` JSON present (dict) and keys match descriptor list (ignore future additional keys).  
	Rationale: Detects serialization regression or missing default factory on creation.

## Cross-Entity Checks

- [ ] Every OrgItem with a `catalog` reference points to a catalog where the vendor vs customer assignment aligns with organizational expectations.  
	Rationale: Prevents cross-tenant leakage and mis-priced associations.
- [ ] No orphan `CatalogLine` pointing to deleted `Item` or `Catalog` (FK enforcement should prevent; double-check via query if needed).  
	Rationale: Early detection of any accidental raw SQL / manual deletion bypassing FK integrity.

## Sample Queries (Django shell or SQL)

```python
# Orgs with any OrgItem missing next check despite frequency
from apps.products.models import OrgItem
needs_next = OrgItem.objects.filter(inventory_frequency__isnull=False, dt_next_check__isnull=True)

# Catalog code collisions (should be empty)
from django.db.models import Count
from apps.products.models import Catalog
collisions = Catalog.objects.values('code', 'vendor_org').annotate(c=Count('id')).filter(c__gt=1)

# OrgItems where min > max (should be empty)
bad_thresholds = OrgItem.objects.filter(quantity_minimum__isnull=False, quantity_maximum__isnull=False, quantity_minimum__gt=quantity_maximum)
```

## Red Flags


## Automation & Tooling Options

1. Pytest guard (e.g. `test_catalog_orgitem_invariants.py`) asserting zero violations of: threshold inversion, catalog metric drift, orphan lines.  
	Rationale: Provides early CI failure before defects propagate to staging.
2. Management command (proposed: `python manage.py catalog_orgitem_health --json`) summarizing counts & first 10 offending IDs.  
	Rationale: Lightweight manual health snapshot for product / data reviewers without running full test suite.
3. Extended checklist module for delivery & inventory verification (future `checklists_delivery_inventory.md`).  
	Rationale: Aligns related operational workflows (inventory check cadence, delivery variance) under consistent review discipline.
4. Optional periodic task to recompute and log drift deltas (warn if > threshold).  
	Rationale: Continuous monitoring vs. ad‑hoc inspection.

## Suggested Assistant Prompts (For Testers)

Use these when seeking clarification or deeper dives during review:


## Final Sign-Off

Reviewer initials & date: ________
Issues logged (IDs / links): ________
