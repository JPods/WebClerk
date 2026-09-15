# Model polish pass
**Status:** In progress — audited 2026-08-31
**Review date:** 2026-08-31

This pass focuses on tightening contracts, consistency, and performance before we add more endpoints and services.

## Scope

- Action model
  - Normalize statuses to a small set with lifecycle mapping (open, in_progress, blocked, done, canceled)
  - ~~Idempotent creation in transitions using a natural key~~ (done — `metadata__idempotency_key` in `transactions/views/actions.py`)
  - Indexes: status (done), action_type (done), assigned_to (pending — JSONField, needs GIN or functional index)
- Document model
  - ~~Confirm registry maps `document` to `apps.docs.models.document.Document`~~ (done — `model_registry.py` line 76)
  - Indexes: slug (done, unique), status (done, `doc_status_idx`), name (done), search_vector (done, GIN). Missing: tags (no field exists), model_name (N/A for Document)
  - Standardize external refs: checksum (done), size_bytes (done), mime_type (done). Missing: uri (only `path` JSONField exists)
- Linkage model
  - Make Linkage canonical; keep refs.links as cache/summary — partially done (LinkageEntry uses group-based model, not edge-based; both patterns coexist)
  - ~~Add uniqueness to prevent duplicate edges~~ (done — `UniqueConstraint` on `model_name, record_id` per group)
  - Maintenance command to reconcile invalid edges
- Identity
  - ~~Keep internal uuid nullable; enforce uuid assignment at API boundary~~ (done — `CoreModel.uuid` nullable, unique)
  - For Action/Document in prod, consider setting NOT NULL constraint and backfill via command with v5 keys
- Security
  - Centralize object-level perms for Action/Document by resolving to owning entity via Linkage
  - Backstop search endpoints to respect security level/org ownership
- Audit
  - Emit audit records on Action status changes (done — `audit_signals.py` registers Action) and Document create/update (pending — Document not in `AUDITED_MODELS`) with correlation IDs (pending — `AuditLog` has no `correlation_id`)
- Migrations & runbook
  - Prepare runbook for live DB ordering (contenttypes and SeparateDatabaseAndState patterns)
  - Add CI smoke test for migrations on a clean DB

## Deliverables

- Migration(s) for indexes and constraints — partially done (LinkageEntry constraint, Document indexes exist; missing: assigned_to, tags GIN, uri field)
- ~~Small utility helpers for idempotent Actions and Linkage creation~~ (done — `LinkageEntry.create_group()`, `next_group_id()`, `add_to_group()`)
- Tests: linkage tests exist (`test_comments_mixin_linkage.py`, `test_flow_linkage_chain.py`, `test_linkage_comments.py`). Missing: depends_on cycles, Action idempotency, permissions, document search security

## After this pass

- Add generic related endpoints:
  - GET /{model}/{id}/actions
  - GET /{model}/{id}/documents
- Add action graph endpoint: GET /actions/{id}/graph?depth=N
- Wire services for orchestration flows without cluttering core transactions
