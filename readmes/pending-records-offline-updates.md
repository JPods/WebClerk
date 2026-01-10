# Pending Records & Offline Handling

## Objectives

- Support optimistic workflows shared with React2025 containers while preserving authoritative database state.
- Provide deterministic reconciliation between staged mutations and committed records.
- Give API consumers predictable lifecycle events for proposals, orders, invoices, purchases, and contacts.

## Key Concepts

- **Pending record**: serialized mutation stored by the client until the server confirms persistence.
- **Publish**: successful API response that finalizes a pending record and emits downstream signals (webhooks, audit logs).
- **Reconciliation**: comparison between a client's pending payload and the canonical record to resolve differences.

## API Responsibilities

1. **Submission**
   - Accept idempotent request tokens (e.g., `X-Request-Id`) to guard against duplicate processing.
   - Validate payload versions and reject stale updates with actionable error codes (`409_CONFLICT`).
   - Persist provisional state when necessary (e.g., draft rows) with a flag marking them as pending.
2. **Status Reporting**
   - Provide endpoints to list pending records by entity UUID, operation, and timestamp.
   - Include pending metadata in primary fetch responses so containers can decide whether to clear staged data.
3. **Publishing**
   - On success, remove pending flags, write audit entries, and enqueue events for integrations.
   - On failure, return structured errors describing conflicting fields or required follow-up.

## Data Model Considerations

- Add `pending_status` columns or JSONB fields where lightweight flags are insufficient.
- Track `source_timestamp` and `user_id` for each mutation to reconstruct the optimistic path.
- Guarantee UUID stability; containers rely on it to correlate pending records across single-tenant deployments.

## Conflict Resolution Flow

1. Client requests entity; API returns canonical data plus any pending mutations.
2. If canonical data supersedes the pending payload, flag the mutation as `conflict` and expose field-level diffs.
3. Provide endpoints to clear or merge conflicts; avoid silent overwrites.
4. Emit domain events so external processors (sync jobs, notifications) can react to conflict resolution.

## Background Sync & Retries

- Implement exponential backoff with jitter for retry queues owned by service workers or background jobs.
- Offer a bulk reconciliation endpoint that accepts multiple UUIDs to streamline reconnect flows.
- Consider a cron task that expires abandoned pending records and notifies operators.

## Testing Checklist

- Unit tests covering rejection of stale request tokens and version mismatches.
- Integration tests validating that pending metadata surfaces through standard fetch endpoints.
- Contract tests with the React2025 client to ensure optimistic updates resolve as documented.

## Documentation Links

- Frontend container workflow: [../../React2025/readmes/offline-optimistic-updates.md](../../React2025/readmes/offline-optimistic-updates.md)
- API response envelope expectations: [api_response_envelope.md](api_response_envelope.md)
- Transaction flow responsibilities: [transaction-flow-responsibilities.md](transaction-flow-responsibilities.md)

## Next Actions

- [ ] Confirm idempotent request handling and conflict-resolution endpoints with React2025 container requirements captured in [../../React2025/readmes/containers.txt](../../React2025/readmes/containers.txt).
- [ ] Schedule cross-project integration tests that validate pending-record reconciliation between the WebClerk3 APIs and the React container workflows.
