# Work Orders TODO


<!-- TOC START -->

## Table of Contents

- [Work Orders TODO](#work-orders-todo)
  - [Table of Contents](#table-of-contents)
  - [P1 — Next Up](#p1-next-up)
  - [P2 — Performance & Queryability](#p2-performance-queryability)
  - [P3 — Admin UX & Guardrails](#p3-admin-ux-guardrails)
  - [Hygiene](#hygiene)

<!-- TOC END -->

A focused backlog for Work Orders and Universal API integration. Keep items small, testable, and docs-friendly.

## P1 — Next Up

- [ ] WorkOrderLine status choices + transitions
  - Define strict choices (likely: planned → released → in_progress → done; cancel allowed from planned/released).
  - Enforce allowed transitions in model `save()` with clear `ValidationError` messages.
  - Add completion guard at line-level where relevant (e.g., prevent reverting `done` without admin override).
  - Tests: happy transitions, invalid transitions, filter by `status`.
  - Admin: add bulk actions mirroring header actions, routed via `save()`.
  - Docs: update `readmes/workorders.md` with line status matrix and examples.

- [ ] Transition endpoints with audit
  - Add lightweight endpoints for transitions (release, start, hold, complete, cancel).
  - Route through model validation; record audit trail in `metadata.history` (who/when/what/reason).
  - Response includes previous_status, new_status, and any guard messages.
  - Tests: endpoint contract (envelope), auth, allowed/blocked transitions.
  - Postman: sample requests; Docs updated with examples.

## P2 — Performance & Queryability

- [ ] Extend indexes as fields materialize
  - Headers: add composite indexes on `(org_id, status, dt_created)` and `(item_id, status)` once fields exist.
  - Lines: add indexes for common filters `(parent_ref_id, status)`, `(org_id, item_id)` when present.
  - Validate with `EXPLAIN` on representative queries.

## P3 — Admin UX & Guardrails

- [ ] Richer admin actions & safeguards
  - Confirmation prompts with summary of effects.
  - Disable actions when selected objects are in invalid states (server‑side filter & messaging).
  - Per-object success/error feedback already exists—add aggregate summary and exportable CSV for failures.

- [ ] Observability & Ops
  - Basic metrics: counts by status, avg time in status, completion lag.
  - Optional Prometheus-style counters; surface simple dashboard in admin.

## Hygiene

- [ ] Keep wcapi strict mode parity for headers/lines (filters, projections).
- [ ] Update docs index after any README change (`Scripts/gen_docs_index.py`).
