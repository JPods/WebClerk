# Contact Verification

This document covers the unified submission and verification flow for all communication record types: Email, Phone, Address, and Domain.

---

## Overview

Communications models (Address, Email, Phone, Domain) share a provider-agnostic verification architecture built on the `sync` app. Each verification:

1. Uses a `sync.Connection` record for provider configuration
2. Logs every attempt as a `sync.Bundle` with masked config and normalized response
3. Starts with `response.review.status=pending` — a reviewer must accept or reject before changes are committed
4. Updates model metadata on acceptance

---

## Submission Snapshot

On create, the original client payload is captured for traceability:

- A generic helper `BaseModel.record_submission_snapshot(data, actor_id)` stores a bounded snapshot under `prefs.submission.as_submitted = { data, dt, by }`
- This is added during create in: `EmailView`, `PhoneView`, `AddressView`

After successful validation, call `Address.clear_submission_snapshot(keep_copy_in_versioning=False)` (optionally archives a copy into `metadata.versioning.submission_archived`).

---

## Email Verification

### Connection

- type: `email_verification`
- config example: `{ "provider": "stub", "mode": "stub" }`

### Flow

1. Trigger: Celery task `validate_email_format(email_id)` after creating an Email, or from the admin.
2. Task calls `apps.sync.services.email_verification.verify_email_via_connection(email)`, which:
   - Picks a `Connection` with `type='email_verification'` (by name if specified)
   - Performs a stubbed provider call (no network by default)
   - Creates a `Bundle` row with masked config and response
   - Returns a normalized result for the task to persist on `Email`

### Result Schema

```json
{"provider": "stub", "status": "stubbed", "deliverability": "unknown", "reason": "stub_mode"}
```

### Apply

Communications tasks update `Email.metadata.versioning.validation` and set `Email.is_verified` based on the normalized result.

### Going Beyond Stub

- Add real provider calls inside `verify_email_via_connection()`
- Normalize provider responses to `{provider, status, deliverability, reason}`
- Keep secrets in `Connection.config` — they will be masked when logged to `Bundle.config`

---

## Phone Verification

### Connection

- type: `phone_verification`
- config example: `{ "provider": "stub", "mode": "stub" }`

### Flow

1. Model helper: `phone.queue_verification()` enqueues `validate_phone_basic`.
2. Task calls `apps.sync.services.phone_verification.verify_phone_via_connection(number)`.
3. A `Bundle` is created with `payload.phone`, masked `config`, and normalized `result` (status/valid/reason).

### Apply

Use Bundles admin to inspect and accept/reject. A future decision service can set metadata flags or derived fields (e.g., normalized E.164) upon acceptance.

### Next Steps

- Add real providers and E.164 normalization.
- Add admin actions mirroring email decisions for phone.

---

## Address Verification

### Connection

- type: `address_verification`
- config example: `{ "provider": "stub", "mode": "stub" }`

### Flow

1. `address.queue_verification('osm')` enqueues `validate_address_osm`.
2. Task uses `apps.sync.services.address_verification.verify_address_via_connection({address1,...})`.
3. Bundle captures masked `config`, normalized `result` (status/match_score), and `payload.address`.

### Apply

`Address.apply_validation_result(result)` updates:
- `metadata.versioning.validation = { provider, status, match_score? }`
- `metadata.history.verified.dt` (epoch ms)
- Lat/long and normalized fields if provided

### Address Display Metadata

On each save, `Address` computes a compact single-line label and persists it to `metadata.display.full_location`. It also stores a detected formatting `standard` (e.g., `us` or `eu`) and a `country_code` where possible.

```json
{
  "full_location": "123 Main St, Apt 5, Springfield, IL 62704",
  "standard": "us",
  "country_code": "US"
}
```

Note: Bulk `.update()` calls will not trigger recompute; prefer model `save()` or schedule a refresh.

### Next Steps

- Integrate Nominatim/Google Maps provider calls with proper mapping.
- Add acceptance admin actions (similar to email) if required.

---

## Domain Verification

### Connection

- type: `domain_verification`
- config example: `{ "provider": "stub", "mode": "stub" }`

### Flow

1. `domain.queue_verification()` enqueues `validate_domain_basic`.
2. Task calls `apps.sync.services.domain_verification.verify_domain_via_connection(path)`.
3. Bundle contains masked `config`, normalized `result` (status/reachable/reason).

### Apply

Accept/reject via Bundles admin. On acceptance, a decision service could update metadata or set status.

### Next Steps

- Add real reachability checks and social API verifications.
- Provide admin accept/reject actions specific to Domain when needed.

---

## Review Workflow

All verification types follow the same review pattern:

1. A Celery task performs verification and creates a `Bundle` with `response.review.status: pending` and provider results populated.
2. A reviewer accepts or rejects the bundle via admin actions. On acceptance, the decision service updates the target record and marks the `Bundle` as `accepted` (or `rejected`).

Admin: Use the Bundles admin to bulk accept/reject. Actions call the appropriate `accept_*` or `reject_exchange` decision service function.

No migrations required; decision state is stored in JSON fields. Extend the decision services for other resource types by adding targeted `accept_*` functions.

---

## Safety Alert Connection

The `reseed --full` command auto-seeds a `sync.Connection` with `name="alert"`, `type="safety_alert"`, `purpose="webclerk.com"`, and `status="safe"`. This is reserved for incident signaling; if the local system detects an assault, it can trigger a Bundle via this connection to notify webclerk.com for verification and coordinated communication.

---

## Verification Stubs Summary

All verification tasks are currently stubbed (no external calls):

| Task | Model | Provider | Status |
|------|-------|----------|--------|
| `validate_email_format(email_id)` | Email | local | stubbed |
| `validate_phone_basic(phone_id)` | Phone | local | stubbed |
| `validate_address_osm(address_id)` | Address | osm | stubbed |
| `validate_domain_basic(domain_id)` | Domain | local | stubbed |

This flow does not make external requests by default. It is safe to enable in local/dev and can be toggled to live providers later. Bundles are lightweight audit logs; they do not store raw provider payloads unless added explicitly.

---

## Future Work

- Implement real OSM/Nominatim lookups with rate limiting and retries.
- Add nightly re-verification for stale records via Celery beat.
- Add post_save signals to auto-queue verification when relevant fields change.
- For advanced international address formatting, consider integrating libpostal or Babel.
