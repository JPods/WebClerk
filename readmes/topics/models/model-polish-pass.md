# Model polish pass (queued)

This pass focuses on tightening contracts, consistency, and performance before we add more endpoints and services.

## Scope

- Action model
  - Normalize statuses to a small set with lifecycle mapping (open, in_progress, blocked, done, canceled)
  - Idempotent creation in transitions using a natural key (source model + source id + action_type [+ step key])
  - Indexes: status, action_type, assigned_to
- Document model
  - Confirm registry maps `document` to `apps.docs.models.document.Document` (done)
  - Ensure indexes: model_name, slug, status, level, tags (GIN where appropriate)
  - Standardize external refs (uri, checksum, size, mime)
- Linkage model
  - Make Linkage canonical; keep refs.links as cache/summary
  - Add uniqueness to prevent duplicate edges (from_model, from_id, to_model, to_id, kind)
  - Maintenance command to reconcile invalid edges
- Identity
  - Keep internal uuid nullable; enforce uuid assignment at API boundary (done)
  - For Action/Document in prod, consider setting NOT NULL constraint and backfill via command with v5 keys
- Security
  - Centralize object-level perms for Action/Document by resolving to owning entity via Linkage
  - Backstop search endpoints to respect security level/org ownership
- Audit
  - Emit audit records on Action status changes and Document create/update with correlation IDs
- Migrations & runbook
  - Prepare runbook for live DB ordering (contenttypes and SeparateDatabaseAndState patterns)
  - Add CI smoke test for migrations on a clean DB

## Deliverables

- Migration(s) for indexes and constraints
- Small utility helpers for idempotent Actions and Linkage creation
- Tests for: depends_on cycles, idempotency, link uniqueness, permissions, document search security
- Docs updates in architecture-actions-documents.md

## After this pass

- Add generic related endpoints:
  - GET /{model}/{id}/actions
  - GET /{model}/{id}/documents
- Add action graph endpoint: GET /actions/{id}/graph?depth=N
- Wire services for orchestration flows without cluttering core transactions
