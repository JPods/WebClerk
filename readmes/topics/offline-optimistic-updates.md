# Offline & Optimistic Update Strategy

## Goals

- Keep list containers responsive when network connectivity fluctuates.
- Guarantee data integrity by reconciling staged changes before publish.
- Provide a predictable user experience across proposals, orders, invoices, purchases, and contact workflows.

## Vocabulary

- **Pending record**: client-staged mutation awaiting confirmation.
- **Publish**: server acknowledgement that commits the staged changes.
- **Reconciliation**: process that merges pending data with canonical server data when connectivity is restored.

## High-Level Flow

1. Capture user edits and persist them locally as pending records keyed by entity UUID and operation (create/update/delete).
2. Apply optimistic UI updates so containers reflect the staged state immediately.
3. Queue network requests; when connectivity is available, send batches to the authoritative API.
4. On successful publish, remove corresponding pending records and refresh the affected entity from the server.
5. If the server rejects a change, surface actionable error feedback and leave the pending record flagged for user review.

## Data Handling Guidelines

- **Storage**: persist pending records in IndexedDB (browser) or a shared service worker cache so state survives reloads.
- **Shape**: align payload schemas with server DTOs; include metadata (`sourceTimestamp`, `version`, `userId`) to aid reconciliation.
- **Idempotency**: attach deterministic request IDs so retries do not duplicate mutations.

## Conflict Resolution

- Before displaying an entity, clear stale pending records: fetch the latest server version, merge compatible fields, and drop pending entries that fully match canonical data.
- For conflicting updates (e.g., server version supersedes optimistic edits), mark the pending record as `conflict` and prompt the container to request manual resolution.
- Implement per-field merge strategies ( e.g., last-writer-wins for notes vs. append-only for comments) and document the behavior in each adapter.

## Container Integration

- Containers subscribe to a `usePendingState(entityId)` hook that exposes staged changes, conflict status, and publish progress.
- Bulk apply workflows create batch pending records; when the target list reloads, the container ensures all processed entities purge related pending entries before rendering.
- Telemetry events should record optimistic updates, publish latency, failures, and user overrides to monitor health.

## Testing Checklist

- Unit tests covering reducer logic for staging, publishing, and clearing pending records.
- Integration tests simulating offline edits, reconnect, and conflict resolution per major container.
- End-to-end coverage ensuring bulk apply with pending records behaves consistently across proposals, orders, invoices, and purchases.

## Open Items

- Define service worker responsibilities for background sync and retry cadence.
- Decide whether to expose a user-facing pending queue UI for manual review.
- Align error message patterns with design team to keep feedback consistent across containers.
