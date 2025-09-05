# Codebase Cleanup & Deprecation Roadmap


<!-- TOC START -->

## Table of Contents

- [Codebase Cleanup & Deprecation Roadmap](#codebase-cleanup-deprecation-roadmap)
  - [Table of Contents](#table-of-contents)
  - [Legend](#legend)
  - [Active / Upcoming Cleanup Items](#active-upcoming-cleanup-items)
  - [Recently Completed](#recently-completed)
  - [Decisions Needed](#decisions-needed)
  - [Proposed Next Sprint Targets](#proposed-next-sprint-targets)
  - [Automation Hooks (Planned)](#automation-hooks-planned)
  - [Removal Playbook](#removal-playbook)
  - [Tracking Format](#tracking-format)

<!-- TOC END -->

Purpose: Track removal / consolidation tasks that surfaced during refactors (OrgItem, Inventory, Catalog, Reservations, Migration squash). Use this doc to coordinate safe deletion, rename, or hardening passes. Keep it SHORT + ACTIONABLE.

## Legend

- Status: ✅ done / 🟡 in progress / ⏳ planned / ❓ decision needed
- Impact: L (low), M (moderate), H (high) – relative developer confusion or runtime risk
- Owner: (assign initials when picked up)

## Active / Upcoming Cleanup Items

| Area | Item / File / Pattern | Action | Rationale | Status | Impact |
|------|-----------------------|--------|-----------|--------|--------|
| Products | `items_carried.py` | (Removed) verify branch parity & purge from stale feature branches | Legacy alias; replaced by `OrgItem` | ✅ | M |
| Products → Item model | Duplicate scalar + JSON pricing/cost: `default_price`, `default_cost` vs `price.base` / `cost.avg/last/standard` | Decide: keep both (cache) OR mark decimals deprecated & add sync invariant test | Prevent drift / confusion | ❓ | M |
| Products → Item model | Field naming: `is_print_not` | Rename to `is_print_suppressed` (backwards compat alias for one release) | Clarity | ⏳ | L |
| Products → Item model | JSON schema enforcement for `price.qty_breaks` & `cost.breaks` | Add Django `clean()` validations + unit tests; raise actionable errors | Data quality | ⏳ | M |
| Products → Item model | Add constraint: currency codes length=3 in `price.currency` & `cost.currency` | DB constraint or validator; add default normalization | Prevent garbage | ⏳ | L |
| Products → Item model | Index optimization | Consider partial index (is_active=1 AND kind='physical'); add trigram/GiST (Postgres only) later | Query perf (catalog browse) | ⏳ | M |
| Products → Item model | Prefs merge helper `ensure_item_prefs` missing doc entry | Add to item README & developer docs | Discoverability | ⏳ | L |
| Org/Catalog | Catalog + OrgItem metrics docs vs implementation parity | Run drift audit: ensure descriptors list matches live keys | Avoid stale docs | ⏳ | M |
| Inventory | Reservation / pending adjustment management commands | Confirm both documented and covered by smoke test | Operational trust | 🟡 | M |
| Core | Deprecated dynamic query endpoints (commented in `apps/core/urls.py`) | Remove commented code after 1 more sprint; link to wcapi registry doc instead | Reduce noise | ⏳ | L |
| Core Save View | Deprecated `expected_version` support | Add warning counter metric; schedule removal date; update client guidance | Simplify API | ⏳ | M |
| Tests | `tests/test_wcapi_invalid_filters.py` placeholder deprecated test | Delete or repurpose as positive contract test | Cut noise | ⏳ | L |
| Tests | Ensure invariant test for Item JSON merges | Add `test_item_json_schema_invariants` | Prevent silent schema drift | ⏳ | M |
| GL Mapping | `gls` JSON keys normalization | Define canonical key set + doc + validator | Accounting alignment | ⏳ | M |
| Naming | Flags cluster (`is_linked`, `is_not_tracked`, `is_tally_by_type`, `is_pacing`) | Audit usage counts; collapse or namespace in `flags` JSON | Reduce field sprawl | ❓ | M |
| Migrations | Legacy stubbed migrations (overrides) | Schedule real deletion once all active branches rebased to squash baseline | Repo hygiene | ⏳ | M |
| Docs | Ensure each complex model group has README: (OrgItem/Catalog ✅, Inventory ✅, Reservations ✅ inline section, Delivery/Checks partial) | Add `delivery-workflow.md` & `inventory-health.md` | Onboarding | ⏳ | M |
| Automation | Health management command for catalog/orgitem/inventory invariants | Implement `python manage.py system_health --section=products` | Faster QA | ⏳ | H |

## Recently Completed

- Migration squash (orgs/products/transactions) with MIGRATION_MODULES override baseline.
- Removal of `items_carried.py` stub (dated 2025-09-04). Updated `org-items.md`.
- Added sample data seeding command (`seed_sample_products`).
- Inventory layering & reservation docs added (`inventory.md`).

## Decisions Needed

1. Keep or deprecate `default_price` / `default_cost` scalar fields? (If deprecating: add shadow write on save + data backfill, then removal migration after 2 cycles.)
2. Collapse boolean flags into a `flags` JSON section for future growth? (Would mirror catalog `flags` pattern.)
3. Trigram / full-text search approach for Items: PostgreSQL native (GIN on tsvector) vs external search service—pick path before adding migrations.

## Proposed Next Sprint Targets

1. Add invariant tests (price & cost break normalization, currency length, duplicate min_qty block).
2. Implement cleanup of deprecated dynamic query commented code.
3. Decide + document scalar price/cost field fate.
4. Add health command skeleton with one check (OrgItem quantity_minimum <= quantity_maximum) as pattern.

## Automation Hooks (Planned)

- pytest: `test_item_invariants.py` (schema & normalization) + `test_catalog_orgitem_invariants.py`.
- management command: `system_health` aggregator returning JSON (exit non-zero on violations in CI mode).
- optional Celery periodic: emit metric counts (deprecated field usage, expected_version usage) to logs or stats backend.

## Removal Playbook

1. Mark: Add doc + warning/log metrics.
2. Shadow: Maintain compatibility but enforce logging + tests.
3. Backfill: Data migration / script to move fields → new structure.
4. Cut: Remove code + migration; update README index.
5. Guard: Keep invariant tests + a contract test verifying absence.

## Tracking Format

Update this file in PRs that touch cleanup items. Keep diff small and scannable. Avoid turning it into a narrative—tables + bullets only.

---
Last updated: 2025-09-04
