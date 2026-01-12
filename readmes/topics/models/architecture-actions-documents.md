# Actions and Documents: clean transaction core, flexible operations

This note clarifies our architecture pattern and the responsibilities across layers.

## Goals

- Keep the core transaction models and relationships clean and stable
- Represent operational work as Action records, gating and progress via `refs.depends_on`
- Store heavy and evolving detail as Documents, linked to transactions and actions
- Expose APIs that compose these layers while preserving a simple core

## Layers

- Transaction core (headers/lines)
  - Canonical state, totals, relationships
  - Minimal fields; JSON envelopes for refs/metadata/prefs
  - Transitions create Actions; core isn’t burdened with operational details
- Actions (activity)
  - One record per activity unit; normalized status; `refs.depends_on` for gating
  - Links to parents/lines via Linkage
  - Idempotent creation in transitions (by natural key) to prevent duplicates
- Documents (detail)
  - Rich, evolving details; external/internal references, tags, search
  - Linked to transactions and actions; independent lifecycle, ACLs

## Identity policy at API boundaries

- Internally, `uuid` is nullable; external systems may set them.
- At the API boundary, if a model instance has a `uuid` field and it is null upon create/update, we assign a UUIDv4.
  - This ensures external clients always receive a stable identifier without forcing internal defaults.
  - Implementation: `RoleAwareModelSerializer` hooks into `create`/`update` and best-effort assigns `uuid` if missing.
  - For deterministic identities, admins can backfill with UUIDv5 using the `populate_uuids` management command.

## Linking and search

- Linkage model is the canonical relation graph; BaseModel `refs.links` may be used as a cache/summary.
- Provide generic endpoints to fetch related Actions and Documents for any entity via Linkage.
- Add a DAG endpoint to traverse Action dependencies for orchestration/UIs.

## Security and audit

- Apply object-level permissions by following Linkage to the owning entity.
- Audit action status transitions and document changes; include request correlation IDs.
- NDJSON command logs exist for UUID population; we’ll extend auditing for runtime flows incrementally.

## Next steps

- Normalize Action status values + idempotent transitions
- Unify model registry keys for Document
- Add generic related endpoints and action graph endpoint
- Index hot filters for Action/Document
- Expand tests: depends_on cycles, link uniqueness, idempotency, and permissions
