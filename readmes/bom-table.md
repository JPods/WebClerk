# Bill of Material (BOM) Table README


<!-- TOC START -->

## Table of Contents

- [Bill of Material (BOM) Table README](#bill-of-material-bom-table-readme)
  - [Core Fields](#core-fields)
  - [Constraints & Indexes](#constraints-indexes)
  - [Cost Snapshot Strategy](#cost-snapshot-strategy)
  - [Roll-up Helper](#roll-up-helper)
  - [Setup / Implementation Checklist](#setup-implementation-checklist)
  - [Future Enhancements (Optional)](#future-enhancements-optional)
  - [Notes](#notes)

<!-- TOC END -->

Purpose: Represents component relationships for bundle/assembly (parent -> component) lines with quantity, scrap/yield, alternates, and optional effective dating.

## Core Fields

- parent_id / component_id: Item FK (component protected, parent cascades)
- quantity: Decimal(14,4) > 0
- scrap_factor: 0 <= scrap < 1 (inflates required quantity)
- yield_pct: Optional explicit yield (derivable from scrap)
- is_alternate / alternate_group: Substitution grouping
- is_optional: Non-mandatory component
- cost_snapshot: Captured unit cost at creation
- revision + effective_from/to: Phased BOM support (future expansion)
- op_data: Lightweight JSON for routing/tooling

## Constraints & Indexes

- Unique (parent, component)
- Check parent != component
- Check 0 <= scrap_factor < 1
- Indexes: parent, component, (parent, revision, sequence)

## Cost Snapshot Strategy

On create we capture `cost_snapshot` from the component's `cost` JSON using the first non-null among:

Order: avg → standard → last → landed

Rationale:

1. avg: Rolling actual/moving average provides most current blended cost.
2. standard: Policy/GL aligned fallback.
3. last: Most recent receipt if avg & standard absent.
4. landed: Potentially noisy (freight/duty allocations) used only if nothing earlier available.

To change precedence, reorder the tuple in `BillOfMaterial.save` without schema changes.

## Roll-up Helper

`BillOfMaterial.recalc_parent_cost(parent_id)` aggregates `cost_snapshot * qty * (1 + scrap_factor)` into `parent.cost.components.snapshot_total`.

Not transactional with live inventory; it's a lightweight view refresh.

## Setup / Implementation Checklist

- [ ] Confirm cost precedence order matches costing policy (adjust order if different priority).
- [ ] Decide if effective dating (effective_from/to) should gate queries; currently not enforced in code.
- [ ] Decide on revision semantics (free text vs controlled vocabulary).
- [ ] Add periodic job / signal to call `recalc_parent_cost` after BOM mutations if automatic maintenance desired.
- [ ] Add API doc for snapshot_total consumption (margin reporting, etc.).
- [ ] Ensure Item.cost JSON includes keys used in precedence (avg, standard, last, landed). Missing keys are harmless.
- [ ] Consider adding component cost currency normalization if multi-currency environment.
- [ ] Add tests for alternate group mutual exclusivity / selection logic if business rules expand.

## Future Enhancements (Optional)

- Effective window filtering (`as_of` date logic in queries/services).
- Multi-level explosion & cached flattened BOM for performance.
- Phantom / reference components (non-costed ops)
- Operation routing integration (sequence groups -> workstation steps).
- Change history / audit for engineering change control.

## Notes

- Removal of legacy scalar cost/price fields means BOM is fully JSON-cost driven.
- `cost_snapshot` is deliberately not re-written on component cost changes; use roll-up to recalc aggregated totals, or design a recalc policy.

